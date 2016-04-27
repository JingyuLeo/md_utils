# coding=utf-8

"""
Tests for wham_rad.
"""

import unittest
import math

import os

from md_utils.md_common import BOLTZ_CONST, capture_stderr, capture_stdout, silent_remove, diff_lines
from md_utils.wham_rad import calc_corr, calc_rad, to_zero_point, main, OUT_PFX
from md_utils.wham import CORR_KEY, COORD_KEY, FREE_KEY


__author__ = 'mayes'

# Directories #

DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
SUB_DATA_DIR = os.path.join(DATA_DIR, 'wham_test_data')


ORIG_WHAM_FNAME = "PMF_last2ns3_1.txt"
ORIG_WHAM_PATH = os.path.join(DATA_DIR, ORIG_WHAM_FNAME)

SHORT_WHAM_FNAME = "PMF_test.txt"
SHORT_WHAM_PATH = os.path.join(DATA_DIR, ORIG_WHAM_FNAME)

# noinspection PyUnresolvedReferences
ORIG_WHAM_OUT = os.path.join(DATA_DIR, OUT_PFX + ORIG_WHAM_FNAME)
GOOD_ORIG_WHAM_OUT = os.path.join(SUB_DATA_DIR, 'good_' + OUT_PFX + ORIG_WHAM_FNAME)
# noinspection PyUnresolvedReferences
SHORT_WHAM_OUT = os.path.join(DATA_DIR, OUT_PFX + SHORT_WHAM_FNAME)
GOOD_SHORT_WHAM_OUT = os.path.join(SUB_DATA_DIR, 'good_' + OUT_PFX + SHORT_WHAM_FNAME)


# Experimental temperature was 310 Kelvin
INF = "inf"
EXP_TEMP = 310
EXP_KBT = BOLTZ_CONST * EXP_TEMP


# Shared Methods #

def zpe_check(test_inst, zpe):
    """Tests that the zero-point energy value has been properly applied.
    :param test_inst: The test class instance.
    :param zpe: The zpe-calibrated data to test.
    """
    for z_row in zpe:
        corr, coord = float(z_row[CORR_KEY]), float(z_row[COORD_KEY])
        if corr == 0:
            test_inst.assertAlmostEqual(6.0, coord)
        else:
            test_inst.assertTrue(corr < 0.0 or math.isinf(corr))

# Tests #


class TestCalcCorr(unittest.TestCase):
    def testCalcCorr(self):
        """
        Good sample data.
        """
        self.assertAlmostEqual(11.9757045375, calc_corr(2.050000, 9.532083, EXP_KBT))

    def testCalcCorrNaN(self):
        """
        Unparsed free energy value.
        """
        self.assertEqual(INF, calc_corr(2.050000, INF, EXP_KBT))


class TestCalcRad(unittest.TestCase):
    def testCalcRad(self):
        for row in calc_rad(SHORT_WHAM_PATH, EXP_KBT):
            self.assertEqual(3, len(row))
            self.assertIsInstance(row[COORD_KEY], float)
            self.assertIsInstance(row[CORR_KEY], float)
            self.assertIsInstance(row[FREE_KEY], float)


class TestZeroPoint(unittest.TestCase):

    def testZeroPoint(self):
        zpe = to_zero_point(calc_rad(SHORT_WHAM_PATH, EXP_KBT))
        zpe_check(self, zpe)


class TestMain(unittest.TestCase):

    def testNoArgs(self):
        with capture_stderr(main, []) as output:
            self.assertTrue("too few arguments" in output)
        with capture_stdout(main, []) as output:
            self.assertTrue("Creates a radial correction value" in output)

    def testSomeArgs(self):
        try:
            main([str(EXP_TEMP), "-o"])
            self.assertFalse(diff_lines(ORIG_WHAM_OUT, GOOD_ORIG_WHAM_OUT))
            self.assertFalse(diff_lines(SHORT_WHAM_OUT, GOOD_SHORT_WHAM_OUT))
        finally:
            silent_remove(ORIG_WHAM_OUT)
            silent_remove(SHORT_WHAM_OUT)
