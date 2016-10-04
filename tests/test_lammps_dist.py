# coding=utf-8

"""
Tests for wham_rad.
"""

import logging
import unittest
import os

from md_utils.lammps import find_atom_data
from md_utils.lammps_dist import atom_distances, main
from md_utils.md_common import InvalidDataError, diff_lines, capture_stderr, capture_stdout, silent_remove

__author__ = 'mayes'

# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DISABLE_REMOVE = logger.isEnabledFor(logging.DEBUG)

# File Locations #

DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
LAM_DATA_DIR = os.path.join(DATA_DIR, 'lammps_dist')
DUMP_PATH = os.path.join(LAM_DATA_DIR, '1.50_small.dump')
STD_DIST_PATH = os.path.join(LAM_DATA_DIR, 'std_pairs_1.50_small.csv')
DIST_PATH = os.path.join(LAM_DATA_DIR, 'pairs_1.50_small.csv')
PAIRS_PATH = os.path.join(LAM_DATA_DIR, 'atom_pairs.txt')
PAIRS_PATH2 = os.path.join(LAM_DATA_DIR, 'atom_pairs2.txt')
DUMP_LIST = os.path.join(LAM_DATA_DIR, 'dump_list.txt')
DUMP_OUT = os.path.join(LAM_DATA_DIR, 'pairs_dump_list.csv')
GOOD_DUMP_OUT = os.path.join(LAM_DATA_DIR, 'pairs_dump_list_good.csv')
DUMP_CUTOFF_PATH = os.path.join(LAM_DATA_DIR, '1.50_small_cutoff.dump')
DUMP_CUTOFF_OUT = os.path.join(LAM_DATA_DIR, 'pairs_1.50_small_cutoff.csv')
GOOD_DUMP_CUTOFF_OUT = os.path.join(LAM_DATA_DIR, 'std_pairs_1.50_small_cutoff.csv')
GHOST_DUMP_LIST = os.path.join(LAM_DATA_DIR, 'ghost_dump_list.txt')

# Data #

LAM_ATOMS = {7500000: {17467: [1116, 38, -0.82, -13.3474, -9.77472, 0.566407],
                       4167: [272, 9, -0.51, -2.90332, 4.1959, -0.319479]},
             7500010: {17467: [1116, 38, -0.82, -13.2865, -9.72761, 0.578118],
                       4167: [272, 9, -0.51, -2.92659, 4.13608, -0.270837]},
             7500020: {17467: [1116, 38, -0.82, -13.2259, -9.67559, 0.587055],
                       4167: [272, 9, -0.51, -2.95968, 4.10041, -0.239808]},
             7500030: {17467: [1116, 38, -0.82, -13.1778, -9.6271, 0.595548],
                       4167: [272, 9, -0.51, -3.00944, 4.05809, -0.207916]},
             7500040: {17467: [1116, 38, -0.82, -13.1348, -9.58866, 0.605338],
                       4167: [272, 9, -0.51, -3.05803, 4.06638, -0.176754]},
             7500050: {17467: [1116, 38, -0.82, -13.1059, -9.56761, 0.624937],
                       4167: [272, 9, -0.51, -3.08408, 4.11423, -0.1371]},
             7500060: {17467: [1116, 38, -0.82, -13.0893, -9.54197, 0.645511],
                       4167: [272, 9, -0.51, -3.15378, 4.16002, -0.134485]},
             7500070: {17467: [1116, 38, -0.82, -13.0658, -9.51954, 0.683413],
                       4167: [272, 9, -0.51, -3.19654, 4.23121, -0.120521]},
             7500080: {17467: [1116, 38, -0.82, -13.0411, -9.49329, 0.73031],
                       4167: [272, 9, -0.51, -3.20867, 4.30202, -0.0954135]},
             7500090: {17467: [1116, 38, -0.82, -13.0308, -9.46276, 0.771404],
                       4167: [272, 9, -0.51, -3.27254, 4.37238, -0.111996]},
             7500100: {17467: [1116, 38, -0.82, -13.028, -9.43718, 0.8038],
                       4167: [272, 9, -0.51, -3.39168, 4.40742, -0.184281]}}

ATOM_DIST = {7500000: {(4167, 17467): 17.465446579913035, (4168, 4197): 5.572394809599909},
             7500010: {(4167, 17467): 17.32773384537704, (4168, 4197): 5.592634621806166},
             7500020: {(4167, 17467): 17.200498583156506, (4168, 4197): 5.659566262054097},
             7500030: {(4167, 17467): 17.06826074399486, (4168, 4197): 5.534633534862449},
             7500040: {(4167, 17467): 16.98861615703186, (4168, 4197): 5.3843480598621225},
             7500050: {(4167, 17467): 16.97675829737141, (4168, 4197): 5.418799109249207},
             7500060: {(4167, 17467): 16.943065879306378, (4168, 4197): 5.266585720056211},
             7500070: {(4167, 17467): 16.944961740483688, (4168, 4197): 4.966874907434251},
             7500080: {(4167, 17467): 16.96081003370571, (4168, 4197): 4.771782319654156},
             7500090: {(4167, 17467): 16.953322170217845, (4168, 4197): 4.67085250454015},
             7500100: {(4167, 17467): 16.896979504188344, (4168, 4197): 4.540623282628058}}


# Tests #

class TestFindAtomData(unittest.TestCase):
    def testGood(self):
        self.assertEqual(LAM_ATOMS, find_atom_data(DUMP_PATH, {4167, 17467}))

    def testMissingAtoms(self):
        with self.assertRaises(InvalidDataError):
            find_atom_data(DUMP_PATH, {-97})


class TestAtomDistances(unittest.TestCase):
    def testTwoPair(self):
        pairs = [(4167, 17467), (4168, 4197)]
        dists = atom_distances(DUMP_PATH, pairs)
        for tstep, t_dist in ATOM_DIST.items():
            for pair in pairs:
                self.assertAlmostEqual(t_dist[pair], dists[tstep][pair])


class TestMainFailWell(unittest.TestCase):
    def testHelp(self):
        test_input = ['-h']
        if logger.isEnabledFor(logging.DEBUG):
            main(test_input)
        with capture_stderr(main, test_input) as output:
            self.assertFalse(output)
        with capture_stdout(main, test_input) as output:
            self.assertTrue("optional arguments" in output)

    def testNoSuchAtomNum(self):
        # this dump list has 1429 atoms; the pairs asks for atoms 4179,54892 and 4180,54892
        # make sure do not create an empty file; start by removing it and then test if there after
        #   running test
        silent_remove(DUMP_OUT)
        test_input = ["-l", DUMP_LIST, "-p", PAIRS_PATH]
        with capture_stderr(main, test_input) as output:
            self.assertTrue("Could not find" in output)
        self.assertFalse(os.path.isfile(DUMP_OUT))

    def testNoSuchFile(self):
        test_input = ["-f", "ghost", "-p", PAIRS_PATH]
        if logger.isEnabledFor(logging.DEBUG):
            main(test_input)
        with capture_stderr(main, test_input) as output:
            self.assertTrue("No such file or directory" in output)

    def testNoSpecifiedFile(self):
        test_input = ["-p", PAIRS_PATH]
        if logger.isEnabledFor(logging.DEBUG):
            main(test_input)
        with capture_stderr(main, test_input) as output:
            self.assertTrue("Specify either" in output)

    def testNoSpecifiedPairFile(self):
        test_input = ["-f", DUMP_PATH]
        if logger.isEnabledFor(logging.DEBUG):
            main(test_input)
        with capture_stderr(main, test_input) as output:
            self.assertTrue("No pair file specified and did not find" in output)

    def testNoSuchFileInList(self):
        test_input = ["-l", GHOST_DUMP_LIST, "-p", PAIRS_PATH]
        if logger.isEnabledFor(logging.DEBUG):
            main(test_input)
        with capture_stderr(main, test_input) as output:
            self.assertTrue("No such file or directory" in output)

    # def testBadDumpFile(self):
    #     test_input = ["-f", GHOST_DUMP_LIST, "-p", PAIRS_PATH]
    #     # if logger.isEnabledFor(logging.DEBUG):
    #     main(test_input)
        # with capture_stderr(main, test_input) as output:
        #     self.assertTrue("No such file or directory" in output)


class TestMain(unittest.TestCase):
    def testDefault(self):
        try:
            main(["-f", DUMP_PATH, "-p", PAIRS_PATH])
            self.assertFalse(diff_lines(STD_DIST_PATH, DIST_PATH))
        finally:
            silent_remove(DIST_PATH)

    def testDumpList(self):
        try:
            main(["-l", DUMP_LIST, "-p", PAIRS_PATH2])
            self.assertFalse(diff_lines(DUMP_OUT, GOOD_DUMP_OUT))
        finally:
            silent_remove(DUMP_OUT)

    def testFileCutoff(self):
        test_input = ["-f", DUMP_CUTOFF_PATH, "-p", PAIRS_PATH]
        try:
            main(test_input)
            self.assertFalse(diff_lines(DUMP_CUTOFF_OUT, GOOD_DUMP_CUTOFF_OUT))
        finally:
            silent_remove(DUMP_CUTOFF_OUT)
