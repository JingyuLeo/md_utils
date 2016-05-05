import unittest
import os

from md_utils.md_common import capture_stdout, capture_stderr, diff_lines, silent_remove
from md_utils.per_col_stats import DEF_ARRAY_FILE, main

__author__ = 'hmayes'

# Directories #

DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
SUB_DATA_DIR = os.path.join(DATA_DIR, 'small_tests')

# Input files #

DEF_INPUT = os.path.join(SUB_DATA_DIR, DEF_ARRAY_FILE)
HEADER_INPUT = os.path.join(SUB_DATA_DIR, "qm_box_sizes_header.txt")
CSV_INPUT = os.path.join(SUB_DATA_DIR, "qm_box_sizes.csv")
CSV_HEADER_INPUT = os.path.join(SUB_DATA_DIR, "qm_box_sizes_header.csv")
# CSV_HEADER_INPUT2 = os.path.join(SUB_DATA_DIR, "all_sum_dru_san_tight_small_fit.csv")
VEC_INPUT = os.path.join(SUB_DATA_DIR, "vector_input.txt")
BAD_INPUT = os.path.join(SUB_DATA_DIR, 'bad_per_col_stats_input.txt')
BAD_INPUT2 = os.path.join(SUB_DATA_DIR, 'bad_per_col_stats_input2.txt')

# Output files #

# noinspection PyUnresolvedReferences
CSV_OUT = os.path.join(SUB_DATA_DIR, "stats_qm_box_sizes.csv")
GOOD_CSV_OUT = os.path.join(SUB_DATA_DIR, "stats_qm_box_sizes_good.csv")
GOOD_CSV_BUFFER_OUT = os.path.join(SUB_DATA_DIR, "stats_qm_box_sizes_buffer_good.csv")
# noinspection PyUnresolvedReferences
CSV_HEADER_OUT = os.path.join(SUB_DATA_DIR, "stats_qm_box_sizes_header.csv")
GOOD_CSV_HEADER_OUT = os.path.join(SUB_DATA_DIR, "stats_qm_box_sizes_header_good.csv")
# noinspection PyUnresolvedReferences
BAD_INPUT_OUT = os.path.join(SUB_DATA_DIR, "stats_bad_per_col_stats_input.csv")
GOOD_BAD_INPUT_OUT = os.path.join(SUB_DATA_DIR, "stats_bad_per_col_stats_input_good.csv")


# Test data #

GOOD_OUT = "     Min value per column:    10.000000    14.995000    10.988000\n" \
           "     Max value per column:    11.891000    15.605000    18.314000\n" \
           "     Avg value per column:    11.092250    15.241000    16.348750\n" \
           "     Std. dev. per column:     0.798138     0.299536     3.576376"


class TestPerCol(unittest.TestCase):
    def testNoArgs(self):
        with capture_stderr(main, []) as output:
            self.assertTrue("Problems reading file" in output)

    def testDefInp(self):
        # main(["-f", DEF_INPUT])
        try:
            with capture_stdout(main, ["-f", DEF_INPUT]) as output:
                self.assertTrue(GOOD_OUT in output)
                self.assertFalse(diff_lines(CSV_OUT, GOOD_CSV_OUT))
        finally:
            silent_remove(CSV_OUT)

    def testArrayInp(self):
        # main(["-f", VEC_INPUT])
        with capture_stderr(main, ["-f", VEC_INPUT]) as output:
            self.assertTrue("File contains a vector" in output)

    def testBadInput(self):
        # Test what happens when cannot convert a value to float
        try:
            with capture_stderr(main, ["-f", BAD_INPUT]) as output:
                self.assertTrue("could not be converted to a float" in output)
                self.assertFalse(diff_lines(BAD_INPUT_OUT, GOOD_BAD_INPUT_OUT))
        finally:
            silent_remove(BAD_INPUT_OUT)

    def testIncDimen(self):
        # Test what happens when the lines do not all have the same number of dimensions
        with capture_stderr(main, ["-f", BAD_INPUT2]) as output:
            self.assertTrue("Problems reading data" in output)
            self.assertTrue("found 3 values " in output)
            self.assertTrue("and 2 values" in output)

    def testDefInpWithBuffer(self):
        # main(["-f", DEF_INPUT, "-b", "6"])
        try:
            with capture_stdout(main, ["-f", DEF_INPUT, "-b", "6"]) as output:
                self.assertTrue('Max value plus 6.0 buffer:    17.891000    21.605000    24.314000' in output)
                self.assertFalse(diff_lines(CSV_OUT, GOOD_CSV_BUFFER_OUT))
        finally:
            silent_remove(CSV_OUT)

    def testDefInpWithBadBuffer(self):
        bad_buffer = 'xyz'
        with capture_stderr(main, ["-f", DEF_INPUT, "-b", bad_buffer]) as output:
            self.assertTrue('WARNING:  Problems reading data: Input for buffer ({}) could not be converted to '
                            'a float.'.format(bad_buffer) in output)

    def testNoSuchOption(self):
        # main(["-@", DEF_INPUT])
        with capture_stderr(main, ["-@", DEF_INPUT]) as output:
            self.assertTrue("unrecognized argument" in output)
            self.assertTrue(DEF_INPUT in output)

    def testHeader(self):
        """
        This input file has a header that starts with a '#' so is ignored by np
        """
        try:
            with capture_stdout(main, ["-f", HEADER_INPUT]) as output:
                self.assertTrue(GOOD_OUT in output)
                self.assertFalse(diff_lines(CSV_HEADER_OUT, GOOD_CSV_OUT))
        finally:
            silent_remove(CSV_HEADER_OUT)

    def testCsv(self):
        """
        This input file has a header that starts with a '#' so is ignored by np.loadtxt
        """
        # main(["-f", CSV_INPUT, "-d", ","])
        try:
            with capture_stdout(main, ["-f", CSV_INPUT, "-d", ","]) as output:
                self.assertTrue(GOOD_OUT in output)
                self.assertFalse(diff_lines(CSV_OUT, GOOD_CSV_OUT))
        finally:
            silent_remove(CSV_OUT)

    def testCsvHeader(self):
        """
        This input file has a header that starts with a '#' so is ignored by np.loadtxt
        """
        # main(["-f", CSV_HEADER_INPUT, "-n", "-d", ","])
        try:
            with capture_stdout(main, ["-f", CSV_HEADER_INPUT, "-n", "-d", ","]) as output:
                self.assertTrue(GOOD_OUT in output)
                self.assertFalse(diff_lines(CSV_HEADER_OUT, GOOD_CSV_HEADER_OUT))
        finally:
            silent_remove(CSV_HEADER_OUT)

    # def testCsvHeader2(self):
    #     """
    #     This input file has a header that starts with a '#' so is ignored by np.loadtxt
    #     """
    #     main(["-f", CSV_HEADER_INPUT2, "-n", "-d", ","])
        # try:
        #     with capture_stdout(main, ["-f", CSV_HEADER_INPUT2, "-n", "-d", ","]) as output:
        #         self.assertTrue(GOOD_OUT in output)
        #         self.assertFalse(diff_lines(CSV_HEADER_OUT, GOOD_CSV_HEADER_OUT))
        # finally:
        #     silent_remove(CSV_HEADER_OUT)