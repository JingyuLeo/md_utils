#!/usr/bin/env python
"""
Creates lammps data files from lammps dump files, given a template lammps data file.
"""

from __future__ import print_function

import ConfigParser
from collections import defaultdict
import copy
import logging
import re
import numpy as np
from md_utils.md_common import list_to_file, InvalidDataError, seq_list_to_file, create_out_suf_fname

import sys
import argparse

__author__ = 'mayes'


# Logging
logger = logging.getLogger('evbd2d')
logging.basicConfig(filename='evbd2d.log', filemode='w', level=logging.DEBUG)
# logging.basicConfig(level=logging.INFO)



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
DUMPS_FILE = 'dump_list_file'
WAT_O_TYPE = 'water_o_type'
WAT_H_TYPE = 'water_h_type'
H3O_O_TYPE = 'h3o_o_type'
H3O_H_TYPE = 'h3o_h_type'
PROT_RES_MOL_ID = 'prot_res_mol_id'
PROT_H_TYPE = 'prot_h_type'
PROT_IGNORE = 'prot_ignore_atom_nums'

# Defaults
DEF_CFG_FILE = 'evbd2d.ini'
# Set notation
DEF_CFG_VALS = {DUMPS_FILE: 'dump_list.txt', PROT_IGNORE: [], }
REQ_KEYS = {DATA_TPL_FILE: str, WAT_O_TYPE: int, WAT_H_TYPE: int, H3O_O_TYPE: int, H3O_H_TYPE: int,
            PROT_RES_MOL_ID: int, PROT_H_TYPE: int, }

# From data template file
NUM_ATOMS = 'num_atoms'
TAIL_CONTENT = 'tail_content'
ATOMS_CONTENT = 'atoms_content'
HEAD_CONTENT = 'head_content'
H3O_MOL = 'hydronium_molecule'
H3O_O_CHARGE = 'hydronium_o_charge'
H3O_H_CHARGE = 'hydronium_h_charge'
FIRST_H3O_H_INDEX = 'first h3o hydrogen index'
PROT_RES_MOL = 'protonatable_residue_molecule'
WATER_MOLS = 'template_water_molecules'


# For data template file processing
SEC_HEAD = 'head_section'
SEC_ATOMS = 'atoms_section'
SEC_TAIL = 'tail_section'


# For dump file processing
SEC_TIMESTEP = 'timestep'
SEC_NUM_ATOMS = 'dump_num_atoms'
SEC_BOX_SIZE = 'dump_box_size'


def warning(*objs):
    """Writes a message to stderr."""
    print("WARNING: ", *objs, file=sys.stderr)


def to_int_list(raw_val):
    return_vals = []
    for val in raw_val.split(','):
        return_vals.append(int(val.strip()))
    return return_vals


def conv_raw_val(param, def_val):
    """
    Converts the given parameter into the given type (default returns the raw value).  Returns the default value
    if the param is None.
    :param param: The value to convert.
    :param def_val: The value that determines the type to target.
    :return: The converted parameter value.
    """
    if param is None:
        return def_val
    if isinstance(def_val, bool):
        return bool(param)
    if isinstance(def_val, int):
        return int(param)
    if isinstance(def_val, long):
        return long(param)
    if isinstance(def_val, float):
        return float(param)
    if isinstance(def_val, list):
        return to_int_list(param)
    return param


def process_cfg(raw_cfg):
    """
    Converts the given raw configuration, filling in defaults and converting the specified value (if any) to the
    default value's type.
    :param raw_cfg: The configuration map.
    :return: The processed configuration.
    """
    proc_cfg = {}
    try:
        for key, def_val in DEF_CFG_VALS.items():
            proc_cfg[key] = conv_raw_val(raw_cfg.get(key), def_val)
    except Exception as e:
        logger.error('Problem with default config vals on key %s: %s', key, e)
    try:
        for key, type_func in REQ_KEYS.items():
            proc_cfg[key] = type_func(raw_cfg[key])
    except Exception as e:
        logger.error('Problem with required config vals on key %s: %s', key, e)


    # If I needed to make calculations based on values, get the values as below, and then
    # assign to calculated config values
    return proc_cfg


def read_cfg(floc, cfg_proc=process_cfg):
    """
    Reads the given configuration file, returning a dict with the converted values supplemented by default values.

    :param floc: The location of the file to read.
    :param cfg_proc: The processor to use for the raw configuration values.  Uses default values when the raw
        value is missing.
    :return: A dict of the processed configuration file's data.
    """
    config = ConfigParser.ConfigParser()
    good_files = config.read(floc)
    if not good_files:
        raise IOError('Could not read file {}'.format(floc))
    main_proc = cfg_proc(dict(config.items(MAIN_SEC)))
    return main_proc


def parse_cmdline(argv):
    """
    Returns the parsed argument list and return code.
    `argv` is a list of arguments, or `None` for ``sys.argv[1:]``.
    """
    if argv is None:
        argv = sys.argv[1:]

    # initialize the parser object:
    parser = argparse.ArgumentParser(description='Creates lammps data files from lammps dump files, given a template '
                                                 'lammps data file. The required input file provides the location of '
                                                 'the data template file, a file with a list of dump files to convert, '
                                                 'and information about the configuration of the data file, needed to '
                                                 'process the dump file to produce data files matching the template '
                                                 '(consistent ID for the hydronium ion, protonatable residue always'
                                                 'deprotonated, etc.). Currently, this script expects only one '
                                                 'protonatable residue.')
    parser.add_argument("-c", "--config", help="The location of the configuration file in ini "
                                               "format. See the example file /test/test_data/evbd2d/evbd2d.ini. "
                                               "The default file name is evbd2d.ini, located in the "
                                               "base directory where the program as run.",
                        default=DEF_CFG_FILE, type=read_cfg)
    args = None
    try:
        args = parser.parse_args(argv)
    except IOError as e:
        warning("Problems reading file:", e)
        parser.print_help()
        return args, IO_ERROR
    except KeyError as e:
        warning("Input data missing:", e)
        parser.print_help()
        return args, INPUT_ERROR

    return args, GOOD_RET


def print_data(head, atoms, tail, f_name):
    list_to_file(head, f_name)
    seq_list_to_file(atoms, f_name, mode='a')
    list_to_file(tail, f_name, mode='a')
    return


def process_data_tpl(cfg):
    tpl_loc = cfg[DATA_TPL_FILE]
    tpl_data = {HEAD_CONTENT: [], ATOMS_CONTENT: [], TAIL_CONTENT: [], PROT_RES_MOL: [], H3O_MOL: [],
                WATER_MOLS: defaultdict(list), FIRST_H3O_H_INDEX: None}
    section = SEC_HEAD
    num_atoms_pat = re.compile(r"(\d+).*atoms$")
    atoms_pat = re.compile(r"^Atoms.*")
    # put in dummy x y z
    x = 0.0
    y = 0.0
    z = 0.0
    with open(tpl_loc) as f:
        for line in f.readlines():
            line = line.strip()
            # head_content to contain Everything before 'Atoms' section
            # also capture the number of atoms
            if section == SEC_HEAD:
                tpl_data[HEAD_CONTENT].append(line)
                if NUM_ATOMS not in tpl_data:
                    atoms_match = num_atoms_pat.match(line)
                    if atoms_match:
                        # regex is 1-based
                        tpl_data[NUM_ATOMS] = int(atoms_match.group(1))
                if atoms_pat.match(line):
                    section = SEC_ATOMS
                    tpl_data[HEAD_CONTENT].append('')
            # atoms_content to contain everything but the xyz: atom_num, mol_num, atom_type, charge, type'
            elif section == SEC_ATOMS:
                if len(line) == 0:
                    continue
                split_line = line.split()
                atom_num = int(split_line[0])
                mol_num = int(split_line[1])
                atom_type = int(split_line[2])
                charge = float(split_line[3])
                descrip = ' '.join(split_line[7:])
                atom_struct = [atom_num, mol_num, atom_type, charge, x, y, z, descrip]
                tpl_data[ATOMS_CONTENT].append(atom_struct)
                if atom_type == cfg[H3O_O_TYPE]:
                    tpl_data[H3O_MOL].append(atom_struct)
                    tpl_data[H3O_O_CHARGE] = charge
                elif atom_type == cfg[H3O_H_TYPE]:
                    if tpl_data[FIRST_H3O_H_INDEX] is None:
                        tpl_data[FIRST_H3O_H_INDEX] = len(tpl_data[H3O_MOL])
                    tpl_data[H3O_MOL].append(atom_struct)
                    tpl_data[H3O_H_CHARGE] = charge
                elif mol_num == cfg[PROT_RES_MOL_ID]:
                    tpl_data[PROT_RES_MOL].append(atom_struct)
                elif atom_type == cfg[WAT_O_TYPE] or atom_type == cfg[WAT_H_TYPE]:
                    tpl_data[WATER_MOLS][mol_num].append(atom_struct)
                if atom_num == tpl_data[NUM_ATOMS]:
                    section = SEC_TAIL
            # tail_content to contain everything after the 'Atoms' section
            elif section == SEC_TAIL:
                tpl_data[TAIL_CONTENT].append(line)

    # Validate data section
    if len(tpl_data[ATOMS_CONTENT]) != tpl_data[NUM_ATOMS]:
        raise InvalidDataError('The length of the "Atoms" section ({}) does not equal '
                               'the number of atoms ({}).'.format(len(tpl_data[ATOMS_CONTENT]), tpl_data[NUM_ATOMS]))

    if logger.isEnabledFor(logging.DEBUG):
        f_out = 'reproduced.data'
        print_data(tpl_data[HEAD_CONTENT], tpl_data[ATOMS_CONTENT], tpl_data[TAIL_CONTENT], f_out)

    return tpl_data


def find_section_state(line):
    atoms_pat = re.compile(r"^ITEM: ATOMS id mol type q x y z.*")
    if line == 'ITEM: TIMESTEP':
        return SEC_TIMESTEP
    elif line == 'ITEM: NUMBER OF ATOMS':
        return SEC_NUM_ATOMS
    elif line == 'ITEM: BOX BOUNDS pp pp pp':
        return SEC_BOX_SIZE
    elif atoms_pat.match(line):
        return SEC_ATOMS


def pbc_dist(a, b, box):
    dist = a - b
    dist = dist - box * np.asarray(map(round, dist / box))
    return np.linalg.norm(dist)


def deprotonate(cfg, protonatable_res, excess_proton, dump_h3o_mol, water_mol_dict, box, tpl_data):
    """
    Deprotonate a the residue and assign the proton to the closest water
    so that the output data matches with the template.
    """
    # Convert excess proton to a hydronium proton
    excess_proton[1] = tpl_data[H3O_MOL][0][1]   # molecule number
    excess_proton[2] = cfg[H3O_H_TYPE]           # type
    excess_proton[3] = tpl_data[H3O_H_CHARGE]    # charge
    dump_h3o_mol.append(excess_proton)
    min_dist = np.linalg.norm(box)
    for mol_id, molecule in water_mol_dict.items():
        for atom in molecule:
            if atom[2] == cfg[WAT_O_TYPE]:
                dist = pbc_dist(np.asarray(excess_proton[4:7]), np.asarray(atom[4:7]), box)
        if dist < min_dist:
            min_dist_id = mol_id
            min_dist = dist
    logger.debug("Deprotonated residue: the molecule ID of the closest water "
                 "(to become a hydronium) is %s.", min_dist_id)
    # Now that have the closest water, add its atoms to the hydronium list
    for atom in water_mol_dict[min_dist_id]:
        dump_h3o_mol.append(atom)
        # Remove the closest water from the dictionary of water molecules, and convert it to a hydronium
    del water_mol_dict[min_dist_id]
    for atom in dump_h3o_mol:
        if atom[2] == cfg[WAT_O_TYPE]:
            atom[2] = cfg[H3O_O_TYPE]
            atom[3] = tpl_data[H3O_O_CHARGE]
        elif atom[2] == cfg[WAT_H_TYPE]:
            atom[2] = cfg[H3O_H_TYPE]
            atom[3] = tpl_data[H3O_H_CHARGE]
    # Make the atom type and charge of the protonatable residue the same as for the template file (switching
    # from protonated to deprotonated residue)
    if len(tpl_data[PROT_RES_MOL]) != len(protonatable_res):
        raise InvalidDataError('In the current timestep of the current dump file, the number of atoms in the '
                               'protonatable residue does not equal the number of atoms in the template data file.')
    for atom in range(0, len(protonatable_res)):
        if protonatable_res[atom][0:2] == tpl_data[PROT_RES_MOL][atom][0:2]:
            protonatable_res[atom][2:4] = tpl_data[PROT_RES_MOL][atom][2:4]
        else:
            raise InvalidDataError('In the current timestep of the current dump file, the atoms in the '
                                   'protonatable residue are not ordered as in the template data file.')

    return


def check_h3o_mol_id(cfg, dump_h3o_mol, water_mol_dict, tpl_h3o_mol, tpl_water_mols):
    # if the h3o molecule id does not match the template, make it so
    # saved as new name for readability
    #   Note: if the procedure for deprotonating a residue has been run, (at least currently) the first hydrogen may
    #   have the correct molecule ID, while the rest does not! Thus, check from the last atom of the molecule
    #   (guaranteed not to be the first hydrogen!)
    target_h3o_mol_id = tpl_h3o_mol[-1][1]
    target_wat_mol_id = copy.copy(dump_h3o_mol[-1][1])
    # Start by copying properties from the template; copy whole line so easier to align columns later
    #   FYI on why I used copy: I was assigning parts of the original water and h3o to the same new molecules,
    #   and it was referencing only, so I did not get my required combination results.
    for atom in tpl_h3o_mol:
        if atom[2] == cfg[H3O_O_TYPE]:
            h3o_o_props = copy.copy(atom)
        else:
            # okay if overwrite; all H props should be the same
            h3o_h_props = copy.copy(atom)
    for atom in next(tpl_water_mols.itervalues()):
        if atom[2] == cfg[WAT_O_TYPE]:
            wat_o_props = copy.copy(atom)
        else:
            # okay if overwrite; all H props should be the same
            wat_h_props = copy.copy(atom)

    print('pre switching (old h3o, old water)')
    print(dump_h3o_mol)
    print(water_mol_dict[target_h3o_mol_id])

    for atom_id, atom in enumerate(dump_h3o_mol):
        atom[1] = target_h3o_mol_id
        # Make sure line up atom types!
        if atom[2] == cfg[H3O_O_TYPE]:
            atom[2:3] = h3o_o_props[2:3]
            atom[7:] = h3o_o_props[7:]
        else:
            atom[2:3] = h3o_h_props[2:3]
            atom[7:] = h3o_h_props[7:]

    for atom_id, atom in enumerate(water_mol_dict[target_h3o_mol_id]):
        atom[1] = target_wat_mol_id
        # Make sure line up atom types!
        if atom[2] == cfg[WAT_O_TYPE]:
            atom[2:3] = wat_o_props[2:3]
            atom[7:] = wat_o_props[7:]
        else:
            atom[2:3] = wat_h_props[2:3]
            atom[7:] = wat_h_props[7:]
    print('post switching (new h3o, new water)')
    print(dump_h3o_mol)
    print(water_mol_dict[target_h3o_mol_id])

    # copy before I delete it
    new_wat_mol = copy.copy(water_mol_dict[target_h3o_mol_id])
    del water_mol_dict[target_h3o_mol_id]
    water_mol_dict[target_wat_mol_id] = new_wat_mol
    return


def check_atom_order(cfg, dump_h3o_mol, water_mol_dict, tpl_data):
    print('template h30:', tpl_data[H3O_MOL])

    target_h3o_h_atom_ids = []
    for atom in tpl_data[H3O_MOL]:
        if atom[2] == cfg[H3O_O_TYPE]:
            target_h3o_o_atom_id = copy.copy(atom[0])
        else:
            target_h3o_h_atom_ids.append(copy.copy(atom[0]))

    # Check if any are wrong
    h_atom_counter = 0
    target_wat_h_atom_ids = []
    for atom in dump_h3o_mol:
        if atom[2] == cfg[H3O_O_TYPE]:
            if atom[0] == target_h3o_o_atom_id:
                target_wat_o_atom_id = None
            else:
                reorder = True
                target_wat_o_atom_id = copy.copy(atom[0])
                atom[0] = target_h3o_o_atom_id
        else:
            if atom[0] in target_h3o_h_atom_ids:
                continue
            target_wat_h_atom_ids.append(copy.copy(atom[0]))
            h_atom_counter += 1

    if target_wat_o_atom_id is not None:
        pass

    for atom in target_wat_h_atom_ids:
        print(atom)

    # TODO: Return here: Reorder water molecules if needed
    # if the order of the water atoms does not match the template, make it so!
    if len(tpl_data[WATER_MOLS]) != len(water_mol_dict):
        raise InvalidDataError('In the current timestep of the current dump file, the number water atoms '
                               'does not equal the number of atoms in the template data file.')
    for mol_id, molecule in water_mol_dict.items():
        for atom_id, atom in enumerate(molecule):
            # print(tpl_data[WATER_MOLS])
            if not ( (atom[0] != tpl_data[WATER_MOLS][mol_id][atom_id][0]) or (
                    atom[2] != tpl_data[WATER_MOLS][mol_id][atom_id][2])):
                break
            print('Fix me!', atom, tpl_data[WATER_MOLS][mol_id][atom_id])
    return


def process_dump_files(cfg, data_tpl_content):
    section = None
    box = np.zeros((3,))
    with open(cfg[DUMPS_FILE]) as f:
        for dump_file in f.readlines():
            dump_file = dump_file.strip()
            data_file_num = 0
            with open(dump_file) as d:
                counter = 1
                for line in d.readlines():
                    line = line.strip()
                    if section is None:
                        section = find_section_state(line)
                        #logger.debug("In process_dump_files, set section to %s.", section)
                        if section is None:
                            raise InvalidDataError('Unexpected line in file {}: {}'.format(d, line))
                    elif section == SEC_TIMESTEP:
                        timestep = line
                        # Reset variables
                        water_dict = defaultdict(list)
                        dump_atom_data = []
                        excess_proton = None
                        h3o_mol = []
                        prot_res = []
                        data_file_num += 1
                        section = None
                    elif section == SEC_NUM_ATOMS:
                        if data_tpl_content[NUM_ATOMS] != int(line):
                            raise InvalidDataError('At timestep {} in file {}, the listed number of atoms ({}) does '
                                                   'not equal the number of atoms in the template data file '
                                                   '({}).'.format(timestep, d, line, data_tpl_content[NUM_ATOMS]))
                        section = None
                    elif section == SEC_BOX_SIZE:
                        split_line = line.split()
                        diff = float(split_line[1]) - float(split_line[0])
                        box[counter - 1] = diff
                        if counter == 3:
                            counter = 0
                            section = None
                        counter += 1
                    elif section == SEC_ATOMS:
                        split_line = line.split()
                        atom_num = int(split_line[0])
                        mol_num = int(split_line[1])
                        atom_type = int(split_line[2])
                        charge = float(split_line[3])
                        x, y, z = map(float, split_line[4:7])
                        # Here, the atoms counting starts at 1. However, the template counted from zero
                        descrip = ' '.join(data_tpl_content[ATOMS_CONTENT][counter - 1][7:])
                        atom_struct = [atom_num, mol_num, atom_type, charge, x, y, z, descrip]
                        dump_atom_data.append(atom_struct)
                        # See if protonatable residue is protonated. If so, keep track of excess proton.
                        # Else, keep track of hydronium molecule.
                        if not (not (mol_num == cfg[PROT_RES_MOL_ID]) or not (atom_type == cfg[PROT_H_TYPE]) or not (
                                atom_num not in cfg[PROT_IGNORE])):
                            # subtract 1 from counter because counter starts at 1, index starts at zero
                            excess_proton = atom_struct
                        elif mol_num == cfg[PROT_RES_MOL_ID]:
                            prot_res.append(atom_struct)
                        elif atom_type == cfg[H3O_O_TYPE] or atom_type == cfg[H3O_H_TYPE]:
                            h3o_mol.append(atom_struct)
                        elif atom_type == cfg[WAT_O_TYPE] or atom_type == cfg[WAT_H_TYPE]:
                            water_dict[mol_num].append(atom_struct)
                        if counter == data_tpl_content[NUM_ATOMS]:
                            counter = 0
                            section = None
                        counter += 1
                # Now that finished reading all lines...
                # Deprotonated if necessary
                if len(h3o_mol) == 0:
                    deprotonate(cfg, prot_res, excess_proton, h3o_mol, water_dict, box, data_tpl_content)
                # Change H3O mol_id if necessary
                target_h3o_mol_id = data_tpl_content[H3O_MOL][-1][1]
                if h3o_mol[-1][1] != target_h3o_mol_id:
                    check_h3o_mol_id(cfg, h3o_mol, water_dict, data_tpl_content[H3O_MOL], data_tpl_content[WATER_MOLS])
                check_atom_order(cfg, h3o_mol, water_dict, data_tpl_content)
                d_out = create_out_suf_fname(dump_file, '_' + str(timestep), ext='.data')
                print_data(data_tpl_content[HEAD_CONTENT], dump_atom_data, data_tpl_content[TAIL_CONTENT], d_out)
                print('Wrote file: {}'.format(d_out))
    return


def main(argv=None):
    # Read input
    args, ret = parse_cmdline(argv)
    # TODO: did not show the expected behavior when I didn't have a required cfg in the ini file
    if ret != GOOD_RET:
        return ret

    # TODO: in generated data files, print atom types and provide new header based on where this came from

    # Read template and dump files
    cfg = args.config
    try:
        data_tpl_content = process_data_tpl(cfg)
        process_dump_files(cfg, data_tpl_content)
    except IOError as e:
        warning("Problems reading file:", e)
        return IO_ERROR
    except InvalidDataError as e:
        warning("Problems reading data template:", e)
        return INVALID_DATA

    return GOOD_RET  # success


if __name__ == '__main__':
    status = main()
    sys.exit(status)
