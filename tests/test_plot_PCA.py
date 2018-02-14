# coding=utf-8

"""
"""

import unittest
import logging
import os
from md_utils.md_common import silent_remove, capture_stderr, capture_stdout, diff_lines
from md_utils.plot_PCA import main

__author__ = 'adams'

# logging.basicConfig(level=logging.DEBUG)
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DISABLE_REMOVE = logger.isEnabledFor(logging.DEBUG)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
PCA_DIR = os.path.join(DATA_DIR, 'plot_PCA')
TRAJ_FILE = os.path.join(PCA_DIR, 'short.dcd')
TOP_FILE = os.path.join(PCA_DIR, 'step5_assembly.xplor_ext.psf')
IG_FILE = os.path.join(PCA_DIR, 'IG_indices.txt')
EG_FILE = os.path.join(PCA_DIR, 'EG_indices.txt')
NAME = 'test'
PNG_FILE = os.path.join(PCA_DIR, 'test.png')
TRAJ_GLOB = os.path.join(PCA_DIR, '*dcd')
DIST_FILE = os.path.join(PCA_DIR, 'test.csv')
GOOD_DIST_FILE = os.path.join(PCA_DIR, 'dist_good.csv')
GOOD_APPEND_FILE = os.path.join(PCA_DIR, 'dist_append_good.csv')

class TestMainFailWell(unittest.TestCase):
    def testHelp(self):
        test_input = ['-h']
        if logger.isEnabledFor(logging.DEBUG):
            main(test_input)
        with capture_stderr(main, test_input) as output:
            self.assertFalse(output)
        with capture_stdout(main, test_input) as output:
            self.assertTrue("optional arguments" in output)

    def testNoSuchFile(self):
        test_input = ['-p', 'ghost']
        if logger.isEnabledFor(logging.DEBUG):
            main(test_input)
        with capture_stderr(main, test_input) as output:
            self.assertTrue("not find specified file" in output)


class TestMain(unittest.TestCase):
    def testWithInwardData(self):
        silent_remove(PNG_FILE)
        test_input = ["--traj", TRAJ_FILE, "--top", TOP_FILE, "-i", IG_FILE, "-e", EG_FILE, "-n", NAME, "-o", PCA_DIR]
        try:
            main(test_input)
            os.path.isfile(PNG_FILE)
        finally:
            silent_remove(PNG_FILE, disable=DISABLE_REMOVE)

    def testGlob(self):
        silent_remove(PNG_FILE)
        test_input = ["-t", TRAJ_GLOB, "-p", TOP_FILE, "-i", IG_FILE, "-e", EG_FILE, "-n", NAME, "-o", PCA_DIR]
        try:
            main(test_input)
            os.path.isfile(PNG_FILE)
        finally:
            silent_remove(PNG_FILE, disable=DISABLE_REMOVE)

    def testWriteDistances(self):
        silent_remove(DIST_FILE)
        test_input = ["-t", TRAJ_FILE, "-p", TOP_FILE, "-i", IG_FILE, "-e", EG_FILE, "-n", NAME, "-o", PCA_DIR, "-w"]
        try:
            main(test_input)
            self.assertFalse(diff_lines(DIST_FILE, GOOD_DIST_FILE))
        finally:
            silent_remove(DIST_FILE, disable=DISABLE_REMOVE)

    def testAppendDistances(self):
        silent_remove(DIST_FILE)
        test_input = ["-t", TRAJ_FILE, "-p", TOP_FILE, "-i", IG_FILE, "-e", EG_FILE, "-n", NAME, "-o", PCA_DIR, "-w"]
        try:
            # The append happens in place, so the base file must first be generated
            main(test_input)
            main(test_input)
            self.assertFalse(diff_lines(DIST_FILE, GOOD_APPEND_FILE))
        finally:
            silent_remove(DIST_FILE, disable=DISABLE_REMOVE)

    def testReadDistances(self):
        silent_remove(PNG_FILE)
        test_input = ["-n", NAME, "-o", PCA_DIR, "-l", GOOD_DIST_FILE]
        try:
            main(test_input)
            os.path.isfile(PNG_FILE)
        finally:
            silent_remove(PNG_FILE, disable=DISABLE_REMOVE)

    def testReadAppend(self):
        silent_remove(PNG_FILE)
        test_input = ["-n", NAME, "-o", PCA_DIR, "-l", GOOD_APPEND_FILE]
        try:
            main(test_input)
            os.path.isfile(PNG_FILE)
        finally:
            silent_remove(PNG_FILE, disable=DISABLE_REMOVE)

    #This unit test is for designed exclusively for use on maitake to examine the actual plot
    # def testPlotContents(self):
    #     test_input = ["-t", "/Users/xadams/XylE/InwardOpen_deprotonated/namd/7.2.dcd", "-p", TOP_FILE, "-i", IG_FILE, "-e", EG_FILE, "-n", NAME, "-o", PCA_DIR, ]
    #     main(test_input)
    #     os.path.isfile(PNG_FILE)
