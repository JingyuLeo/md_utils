import unittest
import os

from md_utils import pdb_edit
import md_utils.md_common


__author__ = 'hmayes'

DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
SUB_DATA_DIR = os.path.join(DATA_DIR, 'pdb_edit')
ATOM_DICT_FILE = os.path.join(SUB_DATA_DIR, 'atom_reorder.csv')
DEF_INI = os.path.join(SUB_DATA_DIR, 'pdb_edit.ini')
ATOM_DICT_BAD_INI = os.path.join(SUB_DATA_DIR, 'pdb_edit_bad_reorder.ini')
ATOM_DICT_REPEAT_INI = os.path.join(SUB_DATA_DIR, 'pdb_edit_repeat_key.ini')
MOL_CHANGE_INI = os.path.join(SUB_DATA_DIR, 'pdb_edit_mol_change.ini')
MOL_CHANGE_RENUM_INI = os.path.join(SUB_DATA_DIR, 'pdb_edit_mol_renum.ini')
# noinspection PyUnresolvedReferences
DEF_OUT = os.path.join(SUB_DATA_DIR, 'new.pdb')
GOOD_OUT = os.path.join(SUB_DATA_DIR, 'glue_autopsf_short_good.pdb')
GOOD_MOL_CHANGE_OUT = os.path.join(SUB_DATA_DIR, 'glue_autopsf_short_mol_change_good.pdb')
GOOD_MOL_CHANGE_RENUM_OUT = os.path.join(SUB_DATA_DIR, 'glue_autopsf_short_mol_change_renum_good.pdb')

GOOD_ATOM_DICT = {1: 20, 2: 21, 3: 22, 4: 23, 5: 24, 6: 25, 7: 26, 8: 27, 9: 2, 10: 1, 11: 3, 12: 4, 13: 5, 14: 6,
                  15: 7, 16: 8, 17: 9, 18: 10, 19: 11, 20: 12, 21: 13, 22: 14, 23: 15, 24: 16, 25: 17, 26: 18, 27: 19}


class TestPDBEdit(unittest.TestCase):
    def testReadAtomNumDict(self):
        test_dict = pdb_edit.read_int_dict(ATOM_DICT_FILE)
        self.assertEqual(test_dict, GOOD_ATOM_DICT)

    def testReadBadAtomNumDict(self):
        with md_utils.md_common.capture_stderr(pdb_edit.main, ["-c", ATOM_DICT_BAD_INI]) as output:
            self.assertTrue("xx" in output)
            self.assertTrue("26" in output)
            self.assertTrue("Problems with input information" in output)

    def testRepeatKeyNumDict(self):
        with md_utils.md_common.capture_stderr(pdb_edit.main, ["-c", ATOM_DICT_REPEAT_INI]) as output:
            self.assertTrue("Problems with input information" in output)

    def testReorderAtoms(self):
        try:
            pdb_edit.main(["-c", DEF_INI])
            # for debugging:
            with open(DEF_OUT) as f:
                with open(GOOD_OUT) as g:
                    for d_line, g_line in zip(f, g):
                        if d_line != g_line:
                            print(d_line, g_line)
            self.assertFalse(md_utils.md_common.diff_lines(DEF_OUT, GOOD_OUT))
        finally:
            md_utils.md_common.silent_remove(DEF_OUT)

    def testChangeMol(self):
        try:
            pdb_edit.main(["-c", MOL_CHANGE_INI])
            self.assertFalse(md_utils.md_common.diff_lines(DEF_OUT, GOOD_MOL_CHANGE_OUT))
        finally:
            md_utils.md_common.silent_remove(DEF_OUT)

    def testChangeRenumMol(self):
        try:
            pdb_edit.main(["-c", MOL_CHANGE_RENUM_INI])
            self.assertFalse(md_utils.md_common.diff_lines(DEF_OUT, GOOD_MOL_CHANGE_RENUM_OUT))
        finally:
            md_utils.md_common.silent_remove(DEF_OUT)
