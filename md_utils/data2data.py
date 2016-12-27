#!/usr/bin/env python
"""
Creates pdb data files from lammps data files, given a template pdb file.
"""

from __future__ import print_function
import copy
import re
import sys
import argparse
import numpy as np
try:
    # noinspection PyCompatibility
    from ConfigParser import ConfigParser
except ImportError:
    # noinspection PyCompatibility
    from configparser import ConfigParser
from md_utils.md_common import (InvalidDataError, create_out_fname, warning, process_cfg,
                                list_to_file, read_csv_dict, LAMMPS_SECTION_NAMES, pbc_calc_vector)

__author__ = 'hmayes'

# Error Codes
# The good status code
GOOD_RET = 0
INPUT_ERROR = 1
IO_ERROR = 2
INVALID_DATA = 3

# Constants #

# Config File Sections
MAIN_SEC = 'main'

# Config keys
DATA_TPL_FILE = 'data_tpl_file'
DATA_FILES = 'data_list_file'
ATOM_TYPE_DICT_FILE = 'atom_type_dict_filename'
MAKE_ATOM_TYPE_DICT = 'make_atom_type_dict_flag'
ATOM_NUM_DICT_FILE = 'atom_num_dict_filename'
MAKE_ATOM_NUM_DICT = 'make_atom_num_dict_flag'
ADJUST_ATOM = 'adjust_atom'
XYZ1 = 'xyz1'
XYZ2 = 'xyz2'
XYZ_STEPS = 'xyz_steps'
XYZ_STEPS_EXTEND = 'xyz_steps_extend'
ATOMS_DIST = 'atoms_dist'
DIST_RANGE = 'dist_min_max_step'

# data file info
ATOMS_PAT = re.compile(r"^Atoms.*")
NUM_ATOMS_PAT = re.compile(r"(\d+).*atoms$")
BOX_PAT = re.compile(r".*xhi")

# Defaults
DEF_CFG_FILE = 'data2data.ini'
# Set notation
DEF_CFG_VALS = {DATA_FILES: 'data_list.txt',
                ATOM_TYPE_DICT_FILE: None,
                MAKE_ATOM_NUM_DICT: False,
                ATOM_NUM_DICT_FILE: None,
                MAKE_ATOM_TYPE_DICT: False,
                ADJUST_ATOM: None,
                XYZ1: [],
                XYZ2: [],
                XYZ_STEPS: 0,
                XYZ_STEPS_EXTEND: 0,
                ATOMS_DIST: [],
                DIST_RANGE: [],
                }
REQ_KEYS = {DATA_TPL_FILE: str,
            }

# From data template file
NUM_ATOMS = 'num_atoms'
BOX_SIZE = 'box_size'
HEAD_CONTENT = 'head_content'
ATOMS_CONTENT = 'atoms_content'
TAIL_CONTENT = 'tail_content'
ATOM_TYPE_DICT = 'atom_type_dict'
ATOM_ID_DICT = 'atom_id_dict'

# For data file processing
SEC_HEAD = 'head_section'
SEC_ATOMS = 'atoms_section'
SEC_TAIL = 'tail_section'
NEW_DIST_LIST = 'new_dist_list'


def read_cfg(floc, cfg_proc=process_cfg):
    """
    Reads the given configuration file, returning a dict with the converted values supplemented by default values.

    :param floc: The location of the file to read.
    :param cfg_proc: The processor to use for the raw configuration values.  Uses default values when the raw
        value is missing.
    :return: A dict of the processed configuration file's data.
    """
    config = ConfigParser()
    good_files = config.read(floc)
    if not good_files:
        raise IOError('Could not read file {}'.format(floc))
    main_proc = cfg_proc(dict(config.items(MAIN_SEC)), DEF_CFG_VALS, REQ_KEYS, int_list=False)

    if main_proc[ADJUST_ATOM] is not None:
        try:
            main_proc[ADJUST_ATOM] = int(main_proc[ADJUST_ATOM])
            if main_proc[ADJUST_ATOM] < 1:
                raise ValueError
        except ValueError:
            raise InvalidDataError("The value for the '{}' keyword must be a positive integer (read '{}') "
                                   "as it specifies the 1-based atom index number that will have its xyz "
                                   "coordinates adjusted.".format(ADJUST_ATOM, main_proc[ADJUST_ATOM]))
        if main_proc[XYZ_STEPS] <= 0:
            raise InvalidDataError("When using the '{}' keyword, use the '{}' keyword to specify a positive number of "
                                   "steps to be taken between coordinates provided for '{}' and '{}'."
                                   "".format(ADJUST_ATOM, XYZ_STEPS, XYZ1, XYZ2))
        for key in [XYZ1, XYZ2]:
            key_len = len(main_proc[key])
            try:
                if key_len == 3:
                    main_proc[key] = np.asarray([float(x) for x in main_proc[key]])
                else:
                    raise InvalidDataError
            except (ValueError, InvalidDataError):
                raise InvalidDataError("Use the '{}' keyword to provide a comma-separated list of three floats "
                                       "(read '{}').".format(key, main_proc[key]))

    num_atoms_dist = len(main_proc[ATOMS_DIST])
    if num_atoms_dist > 0:
        try:
            if num_atoms_dist == 2:
                main_proc[ATOMS_DIST] = [int(x) for x in main_proc[ATOMS_DIST]]
            else:
                raise InvalidDataError
        except (ValueError, InvalidDataError):
            raise InvalidDataError("Use the '{}' keyword to provide a comma-separated list of two integers (atom "
                                   "ids, with the second one to be moved as specified; "
                                   "read {}).".format(ATOMS_DIST, main_proc[ATOMS_DIST]))
        try:
            if len(main_proc[DIST_RANGE]) == 3:
                dist_range = [float(x) for x in main_proc[DIST_RANGE]]
                if dist_range[0] == dist_range[1]:
                    main_proc[NEW_DIST_LIST] = [dist_range[0]]
                else:
                    main_proc[NEW_DIST_LIST] = []
                    if dist_range[0] < dist_range[1] and dist_range[2] > 0:
                        min_val = dist_range[0]
                        max_val = dist_range[1]
                        step = dist_range[2]
                    elif dist_range[0] > dist_range[1] and dist_range[2] < 0:
                        min_val = dist_range[0]
                        max_val = dist_range[1]
                        step = dist_range[2]
                    else:
                        raise InvalidDataError
                    new_val = min_val
                    while new_val <= max_val:
                        main_proc[NEW_DIST_LIST].append(new_val)
                        new_val += step
            else:
                raise InvalidDataError
        except (ValueError, InvalidDataError):
            raise InvalidDataError("Use the '{}' keyword to provide a comma-separated list of three floats (min dist,"
                                   "max dist, step-size) (read '{}').".format(DIST_RANGE, main_proc[DIST_RANGE]))

    return main_proc


def parse_cmdline(argv):
    """
    Returns the parsed argument list and return code.
    `argv` is a list of arguments, or `None` for ``sys.argv[1:]``.
    """
    if argv is None:
        argv = sys.argv[1:]

    # initialize the parser object:
    parser = argparse.ArgumentParser(description='Creates data files from lammps data in the format of a template data '
                                                 'file. The required input file provides the location of the '
                                                 'template file, a file with a list of data files to convert, and '
                                                 '(optionally) dictionaries mapping old data number or types to new, '
                                                 'to reorder and/or check that the atom type order '
                                                 'is the same in the files to convert and the template file. \n'
                                                 'Note: Dictionaries of data types can be made, **assuming the atom '
                                                 'numbers correspond**. The check on whether they do can be used to '
                                                 'make a list of which atom numbers require remapping.')
    parser.add_argument("-c", "--config", help="The location of the configuration file in ini format. "
                                               "The default file name is {}, located in the "
                                               "base directory where the program as run.".format(DEF_CFG_FILE),
                        default=DEF_CFG_FILE, type=read_cfg)
    args = None
    try:
        args = parser.parse_args(argv)
    except IOError as e:
        warning("Problems reading file:", e)
        parser.print_help()
        return args, IO_ERROR
    except (InvalidDataError, KeyError, SystemExit) as e:
        if e.message == 0:
            return args, GOOD_RET
        warning(e)
        parser.print_help()
        return args, INPUT_ERROR

    return args, GOOD_RET


def process_data_tpl(cfg):
    tpl_loc = cfg[DATA_TPL_FILE]
    tpl_data = {HEAD_CONTENT: [], ATOMS_CONTENT: [], TAIL_CONTENT: [], ATOM_TYPE_DICT: {}, ATOM_ID_DICT: {}}
    section = SEC_HEAD

    with open(tpl_loc) as f:
        for line in f:
            line = line.strip()
            # head_content to contain Everything before 'Atoms' section
            # also capture the number of atoms
            if section == SEC_HEAD:
                tpl_data[HEAD_CONTENT].append(line)
                if NUM_ATOMS not in tpl_data:
                    atoms_match = NUM_ATOMS_PAT.match(line)
                    if atoms_match:
                        # regex is 1-based
                        tpl_data[NUM_ATOMS] = int(atoms_match.group(1))
                if BOX_SIZE not in tpl_data:
                    box_match = BOX_PAT.match(line)
                    if box_match:
                        split_line = line.split()
                        i = 0
                        tpl_data[BOX_SIZE] = np.zeros(3)
                        while i < 3:
                            box_dist = float(split_line[1]) - float(split_line[0])
                            tpl_data[BOX_SIZE][i] = box_dist
                            i += 1
                            line = next(f).strip()
                            tpl_data[HEAD_CONTENT].append(line)
                if ATOMS_PAT.match(line):
                    section = SEC_ATOMS
                    tpl_data[HEAD_CONTENT].append('')

            # atoms_content to contain everything but the xyz: atom_num, mol_num, atom_type, charge'
            elif section == SEC_ATOMS:
                if len(line) == 0:
                    continue
                split_line = line.split()
                atom_num = int(split_line[0])
                mol_num = int(split_line[1])
                atom_type = int(split_line[2])
                charge = float(split_line[3])
                xyz_coords = map(float, split_line[4:7])
                # Read in CHARMM type info,
                end = split_line[7:]
                # end = ' '.join(split_line[7:])
                # atom_struct = [atom_num, mol_num, atom_type, charge,end]
                # tpl_data[ATOMS_CONTENT].append(atom_struct)
                tpl_data[ATOMS_CONTENT].append([atom_num, mol_num, atom_type, charge] + xyz_coords + end)
                if len(tpl_data[ATOMS_CONTENT]) == tpl_data[NUM_ATOMS]:
                    section = SEC_TAIL
            # tail_content to contain everything after the 'Atoms' section
            elif section == SEC_TAIL:
                tpl_data[TAIL_CONTENT].append(line)

    return tpl_data


def read_data_for_dict(cfg, data_file, data_tpl_content, old_new_atom_num_dict, old_new_atom_type_dict):
    with open(data_file) as d:
        section = SEC_HEAD
        atom_id = 0
        num_atoms = None

        for line in d.readlines():
            line = line.strip()

            # Get number of atoms in header, so know when to exit reading loop
            if section == SEC_HEAD:
                if ATOMS_PAT.match(line):
                    section = SEC_ATOMS
                elif num_atoms is None:
                    atoms_match = NUM_ATOMS_PAT.match(line)
                    if atoms_match:
                        # regex is 1-based
                        num_atoms = int(atoms_match.group(1))
                        if num_atoms != data_tpl_content[NUM_ATOMS]:
                            raise InvalidDataError("Number of atoms ({}) in the file: {} \n  does not match the "
                                                   "number of atoms ({}) in the template file: {}"
                                                   "".format(num_atoms, data_file,
                                                             data_tpl_content[NUM_ATOMS], cfg[DATA_TPL_FILE]))

            elif section == SEC_ATOMS:
                if len(line) == 0:
                    continue
                split_line = line.split()

                try:
                    old_atom_num = int(split_line[0])
                    new_atom_num = data_tpl_content[ATOMS_CONTENT][atom_id][0]

                    old_atom_type = int(split_line[2])
                    new_atom_type = data_tpl_content[ATOMS_CONTENT][atom_id][2]

                except ValueError as e:
                    if line in LAMMPS_SECTION_NAMES:
                        raise InvalidDataError("Encountered next section ('{}') before reading the number of "
                                               "atoms ({}) in the data template. "
                                               "Check input.".format(line, data_tpl_content[NUM_ATOMS]))
                    else:
                        raise InvalidDataError("Encountered error: '{}' on line: {}.".format(line, e))

                # Making the dictionaries
                if cfg[MAKE_ATOM_NUM_DICT]:
                    # skip if the values are equal
                    if old_atom_num != new_atom_num:
                        old_new_atom_num_dict[old_atom_num] = new_atom_num
                if cfg[MAKE_ATOM_TYPE_DICT]:
                    if old_atom_type in old_new_atom_type_dict:
                        # Check that we don't have conflicting matching
                        if new_atom_type != old_new_atom_type_dict[old_atom_type]:
                            warning('Previously matched old atom type {} to new atom type {}. On the following '
                                    'line, also found old atom type matched to a different new atom type ({}):'
                                    ' \n{}.'.format(old_atom_type, old_new_atom_type_dict[old_atom_type],
                                                    new_atom_type, line))
                    else:
                        # skip if the values are equal
                        if old_atom_type != new_atom_type:
                            old_new_atom_type_dict[old_atom_type] = new_atom_type

                atom_id += 1
                # Check after addition because the counter started at 0
                if atom_id == num_atoms:
                    # Since the dictionary is only based on the atom section, nothing more is needed.
                    return


def make_atom_dict(cfg, data_tpl_content, old_new_atom_num_dict, old_new_atom_type_dict):
    """
    By matching lines in the template and data file, make a dictionary of atom types (old,new)
    @param cfg: configuration for run
    @param data_tpl_content: info from the data template
    @param old_new_atom_num_dict: dict for changing atom number
    @param old_new_atom_type_dict: dict for changing atom type
    @return: dictionary of atom types (old,new) (also saved if file name given)
    """
    with open(cfg[DATA_FILES]) as f:
        for data_file in f.readlines():
            data_file = data_file.strip()
            # check for empty line; skip to next
            if len(data_file) > 0:
                read_data_for_dict(cfg, data_file, data_tpl_content, old_new_atom_num_dict, old_new_atom_type_dict)
                print("Created dictionary based on 'old' info from: {}\n"
                      "                        and 'new' info from: {}".format(data_file, cfg[DATA_TPL_FILE]))

                # Now that finished reading the file, Write dictionary if a name is given, and a dictionary was created
                if (len(old_new_atom_num_dict) > 0) and (cfg[ATOM_NUM_DICT_FILE] is not None):
                    with open(cfg[ATOM_NUM_DICT_FILE], 'w') as d_file:
                        for line in old_new_atom_num_dict.items():
                            d_file.write('%d,%d' % line + '\n')
                    print('Wrote atom number dictionary to {}.'.format(cfg[ATOM_NUM_DICT_FILE]))
                if len(old_new_atom_type_dict) > 0 and (cfg[ATOM_TYPE_DICT_FILE] is not None):
                    with open(cfg[ATOM_TYPE_DICT_FILE], 'w') as d_file:
                        for line in old_new_atom_type_dict.items():
                            d_file.write('%d,%d' % line + '\n')
                    print('Wrote atom type dictionary to {}.'.format(cfg[ATOM_TYPE_DICT_FILE]))

                # Only need to read one file to make the dictionary.
                return


def process_data_file(atom_type_dict, data_file, data_tpl_content, new_data_section):
    with open(data_file) as d:
        section = SEC_HEAD
        atom_id = 0
        num_atoms = None
        for line in d.readlines():
            line = line.strip()
            # not keeping anything from the header
            if section == SEC_HEAD:
                if ATOMS_PAT.match(line):
                    section = SEC_ATOMS
                elif num_atoms is None:
                    atoms_match = NUM_ATOMS_PAT.match(line)
                    if atoms_match:
                        # regex is 1-based
                        num_atoms = int(atoms_match.group(1))
                        if num_atoms != len(data_tpl_content[ATOMS_CONTENT]):
                            raise InvalidDataError('The number of atoms in the template file ({}) does '
                                                   'not equal the number of atoms ({}) in the data file file: {}.'
                                                   ''.format(data_tpl_content[NUM_ATOMS], num_atoms, data_file))
            # atoms_content to grab xyz and pbc rep; also perform some checking
            elif section == SEC_ATOMS:
                if len(line) == 0:
                    continue
                split_line = line.split()

                # Not currently checking molecule number; the number may be wrong and the data still correct,
                # because of the reordering I did to match the template ordering.
                # Thus, I don't need:
                # mol_num = int(split_line[1])

                # Perform checking that the atom type in the corresponding line of the template file matches
                # the current file
                try:
                    old_atom_type = int(split_line[2])
                    # Add in the xyz coordinates
                    new_data_section[atom_id][4:7] = map(float, split_line[4:7])
                except (IndexError, ValueError):
                    raise InvalidDataError("In attempting to read {} atoms from file: {}\n  "
                                           "expected, but did not find, three ints followed by four floats on"
                                           "line: {}\n  "
                                           "Check input".format(data_tpl_content[NUM_ATOMS], data_file, line))

                # If there is an atom_type_dict, and the read atom type is in it....
                if old_atom_type in atom_type_dict:
                    new_atom_type = data_tpl_content[ATOMS_CONTENT][atom_id][2]
                    matching_new_atom_type = atom_type_dict[old_atom_type]

                    if new_atom_type != matching_new_atom_type:
                        print('Data mismatch on atom_id {:3d}, line: {}\n  Expected type {} but found type {}'
                              ''.format(atom_id + 1, line, matching_new_atom_type, new_atom_type))

                # and pbc ids, if they are there, before comments
                try:
                    new_data_section[atom_id][7] = ' '.join(map(int, split_line[8:10] + [new_data_section[atom_id][7]]))
                except (ValueError, IndexError):
                    # if there is no pdb id info and/or comment info, no problem. Keep on.
                    pass
                atom_id += 1
                # Check after increment because the counter started at 0
                if atom_id == num_atoms:
                    # Since the tail will come only from the template, nothing more is needed.
                    break

    # Now that finished reading the file...
    # Check total length
    # (will be wrong if got to tail before reaching num_atoms)
    if atom_id != num_atoms:
        raise InvalidDataError('The number of atoms read from the file {} ({}) does not equal '
                               'the listed number of atoms ({}).'.format(data_file, atom_id, num_atoms))
        # Now make new file
    f_name = create_out_fname(data_file, suffix='_new', ext='.data')
    list_to_file(data_tpl_content[HEAD_CONTENT] + new_data_section + data_tpl_content[TAIL_CONTENT],
                 f_name)


def process_data_files(cfg, data_tpl_content, atom_type_dict):
    # Don't want to change the original template data when preparing to print the new file:
    new_data_section = copy.deepcopy(data_tpl_content[ATOMS_CONTENT])

    with open(cfg[DATA_FILES]) as f:
        for data_file in f.readlines():
            data_file = data_file.strip()
            if len(data_file) > 0:
                process_data_file(atom_type_dict, data_file, data_tpl_content, new_data_section)


def adjust_atom_xyz(cfg, data_tpl_content):
    """
    If this options is selected, adjust the xyz coordinates as specified
    @param cfg: configuration for the run
    @param data_tpl_content: processed data from the template
    @return: will print new data files or raise InvalidDataError
    """
    if cfg[ADJUST_ATOM] > data_tpl_content[NUM_ATOMS]:
        raise InvalidDataError("Keyword '{}' specified atom index {} to have its XYZ coordinates adjusted, "
                               "but found only "
                               "{} atoms in the data template file: {}".format(ADJUST_ATOM, cfg[ADJUST_ATOM],
                                                                               data_tpl_content[NUM_ATOMS],
                                                                               cfg[DATA_TPL_FILE]))
    diff_vector = np.asarray((np.subtract(cfg[XYZ2], cfg[XYZ1])))
    inc_vector = np.divide(diff_vector, cfg[XYZ_STEPS])
    head_content = data_tpl_content[HEAD_CONTENT]
    atoms_content = data_tpl_content[ATOMS_CONTENT]
    tail_content = data_tpl_content[TAIL_CONTENT]
    # since python is zero-based, must subtract 1
    adjust_atom_num = cfg[ADJUST_ATOM] - 1
    for multiplier in range(-cfg[XYZ_STEPS_EXTEND], cfg[XYZ_STEPS] + cfg[XYZ_STEPS_EXTEND]):
        f_name = create_out_fname(cfg[DATA_TPL_FILE], suffix='_' + str(multiplier), ext='.data')
        atoms_content[adjust_atom_num][4:7] = np.round(multiplier * inc_vector + cfg[XYZ1], 6)
        list_to_file(head_content + atoms_content + tail_content, f_name)


def adjust_atom_dist(cfg, data_tpl_content):
    """
    If this options is selected, adjust the xyz coordinates to specified distances
    @param cfg: configuration for the run
    @param data_tpl_content: processed data from the template
    @return: will print new data files or raise InvalidDataError
    """
    for atom_num in cfg[ATOMS_DIST]:
        if atom_num > data_tpl_content[NUM_ATOMS]:
            raise InvalidDataError("Keyword '{}' specified atom indexes {} but found only "
                                   "{} atoms in the data template file: {}".format(ATOMS_DIST, cfg[ATOMS_DIST],
                                                                                   data_tpl_content[NUM_ATOMS],
                                                                                   cfg[DATA_TPL_FILE]))
    # since python is zero-based, must subtract 1
    pivot_atom_num = cfg[ATOMS_DIST][0] - 1
    pivot_atom = data_tpl_content[ATOMS_CONTENT][pivot_atom_num]
    pivot_xyz = np.array(pivot_atom[4:7])

    moving_atom_num = cfg[ATOMS_DIST][1] - 1
    moving_atom = data_tpl_content[ATOMS_CONTENT][moving_atom_num]
    moving_xyz = np.array(moving_atom[4:7])

    diff_vector = pbc_calc_vector(moving_xyz, pivot_xyz, data_tpl_content[BOX_SIZE])
    base_dist = np.linalg.norm(diff_vector)

    head_content = data_tpl_content[HEAD_CONTENT]
    atoms_content = data_tpl_content[ATOMS_CONTENT]
    tail_content = data_tpl_content[TAIL_CONTENT]

    for new_dist in cfg[NEW_DIST_LIST]:
        multiplier = new_dist / base_dist
        f_name = create_out_fname(cfg[DATA_TPL_FILE], suffix='_' + str(new_dist), ext='.data')
        atoms_content[moving_atom_num][4:7] = np.round(multiplier * diff_vector + pivot_xyz, 6)
        list_to_file(head_content + atoms_content + tail_content, f_name)


def main(argv=None):
    # Read input
    args, ret = parse_cmdline(argv)
    if ret != GOOD_RET or args is None:
        return ret

    # Read template and data files
    cfg = args.config

    try:
        data_tpl_content = process_data_tpl(cfg)

        old_new_atom_num_dict = {}
        old_new_atom_type_dict = {}

        # Will return an empty dictionary for one of them if that one is not true
        if cfg[MAKE_ATOM_NUM_DICT] or cfg[MAKE_ATOM_TYPE_DICT]:
            make_atom_dict(cfg, data_tpl_content, old_new_atom_num_dict, old_new_atom_type_dict)

        # Will return empty dicts if no file
        if not cfg[MAKE_ATOM_TYPE_DICT]:
            old_new_atom_type_dict = read_csv_dict(cfg[ATOM_TYPE_DICT_FILE])
        if cfg[ADJUST_ATOM] is None and len(cfg[ATOMS_DIST]) == 0:
            process_data_files(cfg, data_tpl_content, old_new_atom_type_dict)
        elif len(cfg[ATOMS_DIST]) == 0:
            adjust_atom_xyz(cfg, data_tpl_content)
        else:
            adjust_atom_dist(cfg, data_tpl_content)

    except IOError as e:
        warning("Problems reading file:", e)
        return IO_ERROR

    except InvalidDataError as e:
        warning("Problems reading data:", e)
        return INVALID_DATA

    return GOOD_RET  # success


if __name__ == '__main__':
    status = main()
    sys.exit(status)
