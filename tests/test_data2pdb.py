import json
import unittest
import os
from md_utils import data2pdb
from md_utils.data2pdb import main
from md_utils.md_common import diff_lines, silent_remove, capture_stdout, capture_stderr
import logging

# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DISABLE_REMOVE = logger.isEnabledFor(logging.DEBUG)

__author__ = 'hmayes'

TEST_DIR = os.path.dirname(__file__)
MAIN_DIR = os.path.dirname(TEST_DIR)
DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
SUB_DATA_DIR = os.path.join(DATA_DIR, 'data2pdb')
DEF_INI = os.path.join(SUB_DATA_DIR, 'data2pdb.ini')
TYPO_INI = os.path.join(SUB_DATA_DIR, 'data2pdb_typo.ini')
MISS_INI = os.path.join(SUB_DATA_DIR, 'data2pdb_miss.ini')
NO_FILES_INI = os.path.join(SUB_DATA_DIR, 'data2pdb_no_files.ini')
DIFF_ATOM_NUM_INI = os.path.join(SUB_DATA_DIR, 'data2pdb_diff_atom_num.ini')
DIFF_ATOM_NUM_DICT_INI = os.path.join(SUB_DATA_DIR, 'data2pdb_dict_diff_atom_num.ini')
CUTOFF_DATA_INI = os.path.join(SUB_DATA_DIR, 'data2pdb_cutoff.ini')
GHOST_LIST_INI = os.path.join(SUB_DATA_DIR, 'data2pdb_ghost_list.ini')
NO_DICT_INI = os.path.join(SUB_DATA_DIR, 'data2pdb_no_dict.ini')
GLU_INI = os.path.join(SUB_DATA_DIR, 'data2pdb_glu.ini')
GLU_DICT_INI = os.path.join(SUB_DATA_DIR, 'data2pdb_glu_dict.ini')

NOT_INI = os.path.join(SUB_DATA_DIR, 'glue_hm_cutoff.data')

PDB_TPL = os.path.join(SUB_DATA_DIR, 'glue_hm_tpl.pdb')
# noinspection PyUnresolvedReferences
PDB_TPL_OUT = os.path.join(SUB_DATA_DIR, 'reproduced_tpl.pdb')

# noinspection PyUnresolvedReferences
PDB_OUT = os.path.join(SUB_DATA_DIR, 'glue_hm.pdb')
GOOD_PDB_OUT = os.path.join(SUB_DATA_DIR, 'glue_hm_good.pdb')

# noinspection PyUnresolvedReferences
GLU_OUT = os.path.join(SUB_DATA_DIR, '0.625_20c_reorder_retype_548990.pdb')
GOOD_GLU_OUT = os.path.join(SUB_DATA_DIR, '0.625_20c_reorder_retype_548990_good.pdb')

DEF_DICT_OUT = os.path.join(MAIN_DIR, 'atom_dict.json')
GOOD_DICT = os.path.join(SUB_DATA_DIR, 'atom_dict_good.json')


class TestData2PDBNoOut(unittest.TestCase):
    # These all test failure cases
    def testNoArgs(self):
        with capture_stderr(main, []) as output:
            self.assertTrue("WARNING:  Problems reading file: Could not read file" in output)
        with capture_stdout(main, []) as output:
            self.assertTrue("optional arguments" in output)

    def testTypoIni(self):
        with capture_stderr(main, ["-c", TYPO_INI]) as output:
            self.assertTrue("Unexpected key" in output)

    def testMissReqKeyIni(self):
        with capture_stderr(main, ["-c", MISS_INI]) as output:
            self.assertTrue("Missing config val for key 'pdb_tpl_file'" in output)

    def testNoFiles(self):
        with capture_stderr(main, ["-c", NO_FILES_INI]) as output:
            self.assertTrue("No files to process" in output)

    def testNoFilesInList(self):
        with capture_stderr(main, ["-c", GHOST_LIST_INI]) as output:
            self.assertTrue("Problems reading file" in output)

    def testDiffAtomNum(self):
        with capture_stderr(main, ["-c", DIFF_ATOM_NUM_INI]) as output:
            self.assertTrue("Mismatched numbers of atoms" in output)

    def testDiffAtomNumDict(self):
        with capture_stderr(main, ["-c", DIFF_ATOM_NUM_DICT_INI]) as output:
            self.assertTrue("Mismatched numbers of atoms" in output)

    def testCutoffData(self):
        # An incomplete data file (as if stopped during copying)
        with capture_stderr(main, ["-c", CUTOFF_DATA_INI]) as output:
            self.assertTrue("atoms, but found" in output)

    def testNotIni(self):
        # gracefully fail if give the wrong file to the -c option
        test_input = ["-c", NOT_INI]
        if logger.isEnabledFor(logging.DEBUG):
            main(test_input)
        with capture_stderr(main, test_input) as output:
            self.assertTrue("WARNING:  File contains no section headers" in output)

    def testNoDictFound(self):
        with capture_stderr(main, ["-c", NO_DICT_INI]) as output:
            self.assertTrue("The program will continue without checking atom types" in output)

    def testHelp(self):
        test_input = ['-h']
        if logger.isEnabledFor(logging.DEBUG):
            main(test_input)
        with capture_stderr(main, test_input) as output:
            self.assertFalse(output)
        with capture_stdout(main, test_input) as output:
            self.assertTrue("optional arguments" in output)


class TestData2PDB(unittest.TestCase):
    # These test/demonstrate different options
    def testDefIni(self):
        test_input = ["-c", DEF_INI]
        if logger.isEnabledFor(logging.DEBUG):
            main(test_input)
        try:
            main(test_input)
            self.assertFalse(diff_lines(PDB_OUT, GOOD_PDB_OUT))
        finally:
            silent_remove(PDB_TPL_OUT)
            silent_remove(PDB_OUT)

    def testGlu(self):
        try:
            data2pdb.main(["-c", GLU_INI])
            self.assertFalse(diff_lines(GLU_OUT, GOOD_GLU_OUT))
        finally:
            silent_remove(PDB_TPL_OUT)
            silent_remove(GLU_OUT)

    def testGluDict(self):
        try:
            data2pdb.main(["-c", GLU_DICT_INI])
            self.assertFalse(diff_lines(GLU_OUT, GOOD_GLU_OUT))
            with open(DEF_DICT_OUT, 'r') as d_file:
                dict_test = json.load(d_file)
            with open(GOOD_DICT, 'r') as d_file:
                dict_good = json.load(d_file)
            self.assertEqual(dict_test, dict_good)
        finally:
            silent_remove(PDB_TPL_OUT)
            silent_remove(GLU_OUT)
            silent_remove(DEF_DICT_OUT)
