#!/usr/bin/env python
"""
Given a file with an xyz vector (space separated, no other data), return the maximum x, y, and z coordinates, plus the
values after a buffer distance is added
"""

from __future__ import print_function
import ConfigParser
import os

import numpy as np
from md_utils.md_common import InvalidDataError, warning, process_cfg
import sys
import argparse


__author__ = 'hmayes'


# Error Codes
# The good status code
GOOD_RET = 0
INPUT_ERROR = 1
IO_ERROR = 2
INVALID_DATA = 3

# Constants #
TOL = 0.0000001

# Config File Sections
SECTIONS = 'sections'
MAIN_SEC = 'main'
DA_GAUSS_SEC = 'DA_Gaussian'
VII_SEC = 'VII'
REP1_SEC = 'REP1'
PARAM_SECS = [DA_GAUSS_SEC, VII_SEC, REP1_SEC]

# Config keys
GROUP_NAMES = 'group_names'
FIT_PARAMS = {DA_GAUSS_SEC: ['c1', 'c2', 'c3'],
              VII_SEC: ['vii'],
              REP1_SEC: ['cap_b', 'b', 'b_prime', 'd_oo', 'cap_c', 'c', 'd_oh', 'cutoff_oo_low', 'cutoff_oo_high',
                         'cutoff_ho_low', 'cutoff_ho_high']
              }
SEC_PARAMS = 'parameters'
INP_FILE = 'new_input_file_name'

LOW = 'low'
HIGH = 'high'
DESCRIP = 'descrip'
PROP_LIST = [LOW, HIGH, DESCRIP]

# Defaults
MAIN_SEC_DEF_CFG_VALS = {INP_FILE: 'fit.inp',
                }
PARAM_SEC_DEF_CFG_VALS = {GROUP_NAMES: 'NOT_SPECIFIED',
                }
DEF_FIT_VII = False
DEF_CFG_FILE = 'fit_evb_setup.ini'
DEF_BEST_FILE = 'fit.best'
DEF_GROUP_NAME = ''
DEF_DESCRIP = ''
PRINT_FORMAT = '%12.6f  %12.6f  : %s\n'


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
    proc = {}
    for section in config.sections():
        raw_configs = config.items(section)
        proc[section] = raw_configs
    return proc


def parse_cmdline(argv):
    """
    Returns the parsed argument list and return code.
    `argv` is a list of arguments, or `None` for ``sys.argv[1:]``.
    """
    if argv is None:
        argv = sys.argv[1:]

    # initialize the parser object:
    parser = argparse.ArgumentParser(description='Reads in best output file and generates new input files.')
    parser.add_argument("-f", "--file", help="The fitevb output file to read. The default is {}".format(DEF_BEST_FILE),
                        default=DEF_BEST_FILE)
    parser.add_argument("-c", "--config", help="The location of the configuration file in ini format. "
                                               "The default file name is {}, located in the "
                                               "base directory where the program as run.".format(DEF_CFG_FILE),
                        default=DEF_CFG_FILE, type=read_cfg)
    parser.add_argument("-v", "--vii_fit", help="Flag to specify fitting the VII term. The default value "
                                                "is {}.".format(DEF_FIT_VII),
                        default=DEF_FIT_VII)
    parser.add_argument("-s", "--summary_file", help="If a summary file name is specified, the program will append "
                                                     "results to a summary file and specify parameter value changes.",
                        default=False)
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

    if not os.path.isfile(args.file):
        if args.file == DEF_BEST_FILE:
            warning("Problems reading specified default fitevb output file ({}) in current directory. "
                    "A different name or directory can be specified with the optional "
                    "-f or --file arguments".format(args.file))
        else:
            warning("Problems reading specified fitevb output file: {}".format(args.file))
        parser.print_help()
        return args, IO_ERROR

    return args, GOOD_RET


def process_output_file(data_file):
    """
    Reads in an initial set of parameters values from a space-separated list, as provided by 'fit.best' output from
    fitEVB. The order is important; thus read through the sections and parameters from the (ordered) lists (specified
    in the constants
    @param data_file: contains a space-separated list of parameters values in the order that corresponds to the lists
    of sections and parameters in constants.
    @return: initial values to use in fitting, with both the high and low values set to that initial value
    """
    raw_vals = np.loadtxt(data_file,dtype=np.float64)
    vals = {}
    index = 0
    for section in PARAM_SECS:
        for param in FIT_PARAMS[section]:
            vals[param] = {}
            vals[param][LOW] = raw_vals[index]
            vals[param][HIGH] = raw_vals[index]
            index += 1
    return vals


def make_inp(initial_vals, cfg, fit_vii_flag):
    """
    cfg has the sections, default ranges for each parameter, and parameter descriptions
    Use that to seed the inp_vals (used for printing) and overwrite with initial values if a parameter
    is not to be fit in the current step.
    @param initial_vals: parameter values from last fitting iteration
    @param cfg: configuration values, wheter the Vii parameter is to be fit
    @return:
    """
    # dict to collect data to print
    inp_vals = {}

    for section in PARAM_SECS:
        for param in cfg[section][SEC_PARAMS]:
            inp_vals[param] = cfg[section][param]
            if section == VII_SEC:
                if not fit_vii_flag:
                    for prop in initial_vals[param]:
                        inp_vals[param][prop] = initial_vals[param][prop]
            else:
                # all other parameters set to initial values
                if fit_vii_flag:
                    for prop in initial_vals[param]:
                        inp_vals[param][prop] = initial_vals[param][prop]

    with open(cfg[MAIN_SEC][INP_FILE], 'w') as inpfile:
        for section in PARAM_SECS:
            inpfile.write('FIT  {} {}\n'.format(section, cfg[section][GROUP_NAMES]))
            for param in FIT_PARAMS[section]:
                inpfile.write(PRINT_FORMAT % (inp_vals[param][LOW], inp_vals[param][HIGH], inp_vals[param][DESCRIP]))


def process_raw_cfg(raw_cfg):
    cfgs = {}
    param_sections = []
    # Process raw values
    for section in raw_cfg:
        section_dict = {}
        if section == MAIN_SEC:
            for entry in raw_cfg[section]:
                section_dict[entry[0]] = entry[1]
        else:
            param_sections.append(section)
            section_dict[SEC_PARAMS] = []
            for entry in raw_cfg[section]:
                if entry[0] == GROUP_NAMES:
                    section_dict[entry[0]] = entry[1]
                else:
                    section_dict[SEC_PARAMS].append(entry[0])
                    vals = [x.strip() for x in entry[1].split(',')]
                    if len(vals) == 2:
                        vals.append(DEF_DESCRIP)
                    try:
                        section_dict[entry[0]] = {LOW: float(vals[0]), HIGH: float(vals[1]), DESCRIP: vals[2]}
                    except ValueError as e:
                        warning("In configuration file section {}, expected comma-separated numerical lower range "
                                "value, upper-range value, and (optional) description (i.e. '-10,10,d_OO') for key {}. "
                                "Found {}. Please check input.".format(section, entry[0], entry[1]))
        cfgs[section] = section_dict

    # Check for defaults
    for section in cfgs:
        if section == MAIN_SEC:
            for cfg in MAIN_SEC_DEF_CFG_VALS:
                if cfg not in cfgs[section]:
                    cfgs[section][cfg] = MAIN_SEC_DEF_CFG_VALS[cfg]
        else:
            if section in PARAM_SECS:
                for cfg in PARAM_SEC_DEF_CFG_VALS:
                    if cfg not in cfgs[section]:
                        cfgs[section][cfg] = PARAM_SEC_DEF_CFG_VALS[cfg]
            else:
                warning("This program currently expects only the sections {} and an optional section {}. Read section "
                        "{}, which will be ignored.".format(PARAM_SECS, MAIN_SEC, section))

    # Add main section with defaults if this optional section is missing; make sure required sections and parameters
    # have been read.
    if MAIN_SEC not in cfgs:
        cfgs[MAIN_SEC] = MAIN_SEC_DEF_CFG_VALS
    for section in PARAM_SECS:
        if section in cfgs:
            for param in FIT_PARAMS[section]:
                if param not in cfgs[section]:
                    raise InvalidDataError('The configuration file is missing parameter {} in section {}. '
                                           'Check input.'.format(param, section))
        else:
            raise InvalidDataError('The configuration file is missing section {}. Check input.'.format(section))

    return cfgs


def get_param_info(cfg):
    headers = []
    for section in PARAM_SECS:
        for param in FIT_PARAMS[section]:
            # print(cfg[section][param])
            headers.append(cfg[section][param])
    return headers


def make_summary(output_file, summary_file, cfg):
    param_info = get_param_info(cfg)
    latest_output = np.loadtxt(output_file,dtype=np.float64)
    headers = []
    percent_diffs = {}
    max_percent_diff = 0.0
    if os.path.isfile(summary_file):
        previous_output = np.loadtxt(summary_file,dtype=np.float64)
        all_output = np.vstack((previous_output, latest_output))
        for index, col in enumerate(all_output.T):
            last_val = None
            col_name = param_info[index][DESCRIP]
            print("analyzing {}:".format(col_name))
            headers.append(col_name)
            for val in col:
                if last_val is not None:
                    if abs(val) < TOL:
                        warning("Small value ({}) encountered for parameter {} (col {}).".format(val, col_name, index))
                        percent_diffs[col_name] = np.nan
                    elif abs(val - last_val) > TOL:
                        percent_diffs[col_name] = (val - last_val) / last_val * 100
                        print("    value = {:8.2f}   percent diff = {:8.2f}".format(val, percent_diffs[col_name]))
                        upper_bound = param_info[index][HIGH]
                        lower_bound = param_info[index][LOW]
                        if abs(val-upper_bound) < TOL:
                            warning("Value ({}) near upper bound ({}) encountered for parameter {} (col {}).".format(val, upper_bound, col_name, index))
                        if abs(val-lower_bound) < TOL:
                            warning("Value ({}) near lower bound ({}) encountered for parameter {} (col {}).".format(val, lower_bound, col_name, index))
                last_val = val
        np.savetxt(summary_file, all_output)
        print("Latest round::")
        for index, header in enumerate(headers):
            if header in percent_diffs:
                print("    {}: {:8.2f}   percent diff: {:8.2f}".format(header.rjust(5), latest_output[index], percent_diffs[header]))
    else:
        np.savetxt(summary_file, latest_output, newline=' ')
        print("Wrote results from {} to new summary file {}".format(output_file, summary_file))


def main(argv=None):
    # Read input
    args, ret = parse_cmdline(argv)
    if ret != GOOD_RET:
        return ret
    raw_cfg = args.config

    try:
        cfg = process_raw_cfg(raw_cfg)
        initial_vals = process_output_file(args.file)
        if args.summary_file is not False:
            make_summary(args.file, args.summary_file, cfg)
        make_inp(initial_vals, cfg, args.vii_fit)
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
