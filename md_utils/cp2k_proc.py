#!/usr/bin/env python
"""
Get information from cp2k output files, such as coordinates and final QMMM energy.
Given a template data or pdb file, it will make new files with the xyz coordinates from the cp2k output file
"""

from __future__ import print_function
from __init__ import __version__
import argparse
import os
import re
import sys
from datetime import datetime
from md_utils.data2data import process_data_tpl
from md_utils.data2pdb import process_pdb_tpl

try:
    # noinspection PyCompatibility
    from ConfigParser import ConfigParser
except ImportError:
    # noinspection PyCompatibility
    from configparser import ConfigParser
from md_utils.md_common import (InvalidDataError, create_out_fname, warning, process_cfg,
                                list_to_file, file_rows_to_list, create_element_dict)

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
PDB_TPL_FILE = 'pdb_tpl_file'
CP2K_LIST_FILE = 'cp2k_list_file'
CP2K_FILE = 'cp2k_file'
XYZ_FILE_SUF = 'xyz_file_suffix'
PRINT_XYZ_FLAG = 'print_xyz_files'

# data file info

COORD_PAT = re.compile(r".*MODULE FIST:  ATOMIC COORDINATES IN.*")
ENERGY_PAT = re.compile(r".*ENERGY\| Total FORCE_EVAL \( QMMM \).*")
NUM_ATOMS_PAT = re.compile(r"(\d+).*atoms$")
BOX_PAT = re.compile(r".*xhi")

# Defaults
DEF_CFG_FILE = 'cp2k_proc.ini'
ELEMENT_DICT_FILE = os.path.join(os.path.dirname(__file__), 'cfg', 'charmm36_atoms_elements.txt')
# Set notation
DEF_CFG_VALS = {CP2K_LIST_FILE: 'cp2k_files.txt', CP2K_FILE: None,
                DATA_TPL_FILE: None, PDB_TPL_FILE: None,
                PRINT_XYZ_FLAG: False, XYZ_FILE_SUF: '.xyz',
                }
REQ_KEYS = {}

# From data template file
NUM_ATOMS = 'num_atoms'
BOX_SIZE = 'box_size'
HEAD_CONTENT = 'head_content'
ATOMS_CONTENT = 'atoms_content'
TAIL_CONTENT = 'tail_content'

# For cp2k file processing
CP2K_FILES = 'cp2k_file_list'


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
        raise IOError("Could not read file '{}'".format(floc))
    main_proc = cfg_proc(dict(config.items(MAIN_SEC)), DEF_CFG_VALS, REQ_KEYS, int_list=False)

    main_proc[CP2K_FILES] = []

    if os.path.isfile(main_proc[CP2K_LIST_FILE]):
        main_proc[CP2K_FILES] += file_rows_to_list(main_proc[CP2K_LIST_FILE])
    if main_proc[CP2K_FILE] is not None:
        main_proc[CP2K_FILES].append(main_proc[CP2K_FILE])

    if len(main_proc[CP2K_FILES]) == 0:
        raise InvalidDataError("Found no file names to process. Use the configuration ('ini') file to specify the name "
                               "of a single file with the keyword '{}' or a file with listing files to process "
                               "(one per line) with the keyword '{}'.".format(CP2K_FILE, CP2K_LIST_FILE))

    return main_proc


def parse_cmdline(argv):
    """
    Returns the parsed argument list and return code.
    `argv` is a list of arguments, or `None` for ``sys.argv[1:]``.
    """
    if argv is None:
        argv = sys.argv[1:]

    # initialize the parser object:
    parser = argparse.ArgumentParser(description='Gathers data from cp2k output files, such as final system energy and '
                                                 'xyz coordinates. Options in the configuration file can lead to '
                                                 'creating data, pdb, or xyz files with the coordinates from the '
                                                 'cp2k output file.')
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


def process_coords(cp2k_file, data_tpl_content, print_xyz_flag, element_dict):
    """
    Creates the new atoms section based on coordinates from the cp2k file
    @param print_xyz_flag: boolean to make xyz files
    @param element_dict: a dictionary of MM types to atomic elements
    @param cp2k_file: file being read
    @param data_tpl_content: data from the template file
    @return: new atoms section, with replaced coordinates
    """
    if data_tpl_content is None:
        make_data_file = False
        new_atoms = []
    else:
        make_data_file = True
        new_atoms = list(data_tpl_content[ATOMS_CONTENT])

    atoms_xyz = []
    atom_count = 0
    atom_num = 0
    for line in cp2k_file:
        split_line = line.split()
        if len(split_line) == 0:
            if make_data_file:
                # If there was a data file, should separately catch the end of the section (see below). Otherwise,
                # all is fine and return data
                raise InvalidDataError("Encountered an empty line after reading {} atoms. Expected to read "
                                       "coordinates for {} atoms before encountering a blank line."
                                       "".format(atom_num, data_tpl_content[NUM_ATOMS]))
            else:
                return new_atoms, atoms_xyz
        atom_num = int(split_line[0])
        xyz_coords = map(float, split_line[3:6])
        if make_data_file:
            new_atoms[atom_count][4:7] = xyz_coords
        if print_xyz_flag:
            if make_data_file:
                charmm_type = new_atoms[atom_count][8].strip(',')
                element_type = element_dict[charmm_type]
                atoms_xyz.append([element_type] + xyz_coords)
            else:
                atoms_xyz.append([split_line[3]] + xyz_coords)
        atom_count += 1

        if make_data_file:
            if atom_num == data_tpl_content[NUM_ATOMS]:
                # If that is the end of the atoms, the next line should be blank
                line = next(cp2k_file).strip()
                if len(line) == 0:
                    return new_atoms, atoms_xyz
                else:
                    raise InvalidDataError("After reading the number of atoms found in the template data file "
                                           "({}), did not encounter a blank line, but: {}"
                                           "".format(data_tpl_content[NUM_ATOMS], line))

    # if went through even line and didn't get all the atoms, catch the error
    raise InvalidDataError("Did not read coordinates from {} atoms in file: {}".format(data_tpl_content[NUM_ATOMS],
                                                                                       cp2k_file.name))


def process_cp2k_file(cfg, cp2k_file, data_tpl_content, pdb_tpl_content, element_dict):
    """
    Gather info from CP2K output file and update xyz data if needed
    @param cfg: confirmation for the run
    @param cp2k_file: the file to open
    @param data_tpl_content: list of lists
    @param pdb_tpl_content: list of lists
    @param element_dict: element dictionary for making xyz files
    @return: xyz coordinates info in data, pdb, and xyz formats (as needed)
    """
    new_atoms_section = None
    if data_tpl_content is None:
        make_data_file = False
    else:
        make_data_file = True
    qmmm_energy = None
    atoms_xyz = None
    with open(cp2k_file) as f:
        if make_data_file:
            data_tpl_content[HEAD_CONTENT][0] = "Created on {} by {} version {} from template file {} and " \
                                                "cp2k output file {}".format(datetime.now(), __name__, __version__,
                                                                             cfg[DATA_TPL_FILE], cp2k_file)
        for line in f:
            line = line.strip()
            if ENERGY_PAT.match(line):
                qmmm_energy = line.split()[-1]
            if COORD_PAT.match(line):
                # Now advance to first line of coordinates
                for _ in range(3):
                    next(f)
                new_atoms_section, atoms_xyz = process_coords(f, data_tpl_content, cfg[PRINT_XYZ_FLAG], element_dict)

    # If we successfully returned the new_atoms_section, make new file
    if new_atoms_section is None:
        raise InvalidDataError("Did not file atoms coordinates in file: {}".format(cp2k_file))
    print("{} energy: {}".format(cp2k_file, qmmm_energy))
    if make_data_file:
        f_name = create_out_fname(cp2k_file, ext='.data')
        list_to_file(data_tpl_content[HEAD_CONTENT] + new_atoms_section + data_tpl_content[TAIL_CONTENT],
                     f_name, print_message=False)
    if cfg[PRINT_XYZ_FLAG]:
        f_name = create_out_fname(cp2k_file, ext=cfg[XYZ_FILE_SUF])
        list_to_file(atoms_xyz, f_name, print_message=False)


def main(argv=None):
    # Read input
    args, ret = parse_cmdline(argv)
    if ret != GOOD_RET or args is None:
        return ret

    # Read template and data files
    cfg = args.config

    try:
        if cfg[PDB_TPL_FILE] is None:
            pdb_tpl_content = None
        else:
            pdb_tpl_content = process_pdb_tpl(cfg)
        if cfg[DATA_TPL_FILE] is None:
            data_tpl_content = None
        else:
            data_tpl_content = process_data_tpl(cfg)

        element_dict = create_element_dict(ELEMENT_DICT_FILE, pdb_dict=False)

        for cp2k_file in cfg[CP2K_FILES]:
            process_cp2k_file(cfg, cp2k_file, data_tpl_content, pdb_tpl_content, element_dict)

    except IOError as e:
        warning("Problems reading file:", e)
        return IO_ERROR

    except (InvalidDataError, KeyError, ValueError) as e:
        warning("Problems reading data:", e)
        return INVALID_DATA

    return GOOD_RET  # success


if __name__ == '__main__':
    status = main()
    sys.exit(status)
