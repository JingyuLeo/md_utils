# coding=utf-8

"""
Tests for evb_get_info.py.
"""
import os
import unittest

from md_utils import evb_get_info
from md_utils.md_common import capture_stdout, capture_stderr, diff_lines, silent_remove


__author__ = 'hmayes'


DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
SUB_DATA_DIR = os.path.join(DATA_DIR, 'evb_info')

INCOMP_INI_PATH = os.path.join(SUB_DATA_DIR, 'evb_get_info_missing_data.ini')

CI_INI_PATH = os.path.join(SUB_DATA_DIR, 'evb_get_info.ini')
DEF_CI_OUT_PATH1 = os.path.join(SUB_DATA_DIR, '1.500_20c_short_ci_sq.csv')
GOOD_CI_OUT_PATH1 = os.path.join(SUB_DATA_DIR, '1.500_20c_short_ci_sq_good.csv')
DEF_CI_OUT_PATH2 = os.path.join(SUB_DATA_DIR, '2.000_20c_short_ci_sq.csv')
GOOD_CI_OUT_PATH2 = os.path.join(SUB_DATA_DIR, '2.000_20c_short_ci_sq_good.csv')

CI_SUBSET_INI_PATH = os.path.join(SUB_DATA_DIR, 'evb_get_info_subset.ini')
DEF_CI_SUBSET_OUT_PATH = os.path.join(SUB_DATA_DIR, '1.500_20c_short_ci_sq_ts.csv')
GOOD_CI_SUBSET_OUT_PATH = os.path.join(SUB_DATA_DIR, '1.500_20c_short_ci_sq_ts_good.csv')

CI_ONE_STATE_INI_PATH = os.path.join(SUB_DATA_DIR, 'serca_evb_get_info.ini')
DEF_ONE_STATE_OUT_PATH = os.path.join(SUB_DATA_DIR, '0_3_ci_sq.csv')
GOOD_ONE_STATE_OUT_PATH = os.path.join(SUB_DATA_DIR, '0_3_ci_sq_good.csv')


class TestEVBGetInfo(unittest.TestCase):
    def testNoIni(self):
        with capture_stdout(evb_get_info.main,[]) as output:
            self.assertTrue("usage:" in output)
        with capture_stderr(evb_get_info.main,[]) as output:
            self.assertTrue("Problems reading file: Could not read file" in output)
    def testMissingInfo(self):
        with capture_stderr(evb_get_info.main,["-c", INCOMP_INI_PATH]) as output:
            self.assertTrue("Input data missing" in output)
        with capture_stdout(evb_get_info.main,["-c", INCOMP_INI_PATH]) as output:
            self.assertTrue("optional arguments" in output)
    def testCiInfo(self):
        try:
            evb_get_info.main(["-c", CI_INI_PATH])
            self.assertFalse(diff_lines(DEF_CI_OUT_PATH1, GOOD_CI_OUT_PATH1))
            self.assertFalse(diff_lines(DEF_CI_OUT_PATH2, GOOD_CI_OUT_PATH2))
        finally:
            silent_remove(DEF_CI_OUT_PATH1)
            silent_remove(DEF_CI_OUT_PATH2)
    def testSubsetCiInfo(self):
        try:
            evb_get_info.main(["-c", CI_SUBSET_INI_PATH])
            self.assertFalse(diff_lines(DEF_CI_SUBSET_OUT_PATH, GOOD_CI_SUBSET_OUT_PATH))
            self.assertFalse(diff_lines(DEF_CI_OUT_PATH1, GOOD_CI_OUT_PATH1))
            self.assertFalse(diff_lines(DEF_CI_OUT_PATH2, GOOD_CI_OUT_PATH2))
        finally:
            silent_remove(DEF_CI_SUBSET_OUT_PATH)
            silent_remove(DEF_CI_OUT_PATH1)
            silent_remove(DEF_CI_OUT_PATH2)
    def testOneStateCiInfo(self):
        try:
            evb_get_info.main(["-c", CI_ONE_STATE_INI_PATH])
            self.assertFalse(diff_lines(DEF_ONE_STATE_OUT_PATH, GOOD_ONE_STATE_OUT_PATH))
        finally:
            silent_remove(DEF_ONE_STATE_OUT_PATH)

    # def testNegGofR(self):
    #     with capture_stderr(evb_get_info.main,["-c", INCOMP_GOFR_INI_PATH]) as output:
    #         self.assertTrue("a positive value" in output)
    # def testHOGofR(self):
    #     try:
    #         evb_get_info.main(["-c", HO_GOFR_INI_PATH])
    #         self.assertFalse(diff_lines(DEF_GOFR_OUT_PATH, GOOD_HO_GOFR_OUT_PATH))
    #     finally:
    #         silent_remove(DEF_GOFR_OUT_PATH)
    # def testOOGofR(self):
    #     try:
    #         evb_get_info.main(["-c", OO_GOFR_INI_PATH])
    #         self.assertFalse(diff_lines(DEF_GOFR_OUT_PATH, GOOD_OO_GOFR_OUT_PATH))
    #     finally:
    #         silent_remove(DEF_GOFR_OUT_PATH)
    # def testHHGofR(self):
    #     try:
    #         evb_get_info.main(["-c", HH_GOFR_INI_PATH])
    #         self.assertFalse(diff_lines(DEF_GOFR_OUT_PATH, GOOD_HH_GOFR_OUT_PATH))
    #     finally:
    #         silent_remove(DEF_GOFR_OUT_PATH)
    # def testOHGofR(self):
    #     try:
    #         evb_get_info.main(["-c", OH_GOFR_INI_PATH])
    #         self.assertFalse(diff_lines(DEF_GOFR_OUT_PATH, GOOD_OH_GOFR_OUT_PATH))
    #     finally:
    #         silent_remove(DEF_GOFR_OUT_PATH)
    # def testHO_OO_HH_OHGofR(self):
    #     try:
    #         evb_get_info.main(["-c", HO_OO_HH_OH_GOFR_INI_PATH])
    #         self.assertFalse(diff_lines(DEF_GOFR_OUT_PATH, GOOD_HO_OO_HH_OH_GOFR_OUT_PATH))
    #     finally:
    #         silent_remove(DEF_GOFR_OUT_PATH)