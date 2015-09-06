from __future__ import print_function
# Util Methods #
import fnmatch
from itertools import chain, islice

import os
import sys


def swarn(tgt=sys.stderr, *objs):
    """Writes a warning message to a target (stderr by default)."""
    print("WARNING: ", *objs, file=tgt)


def find_files_by_dir(tgt_dir, pat):
    """Recursively searches the target directory tree for files matching the given pattern.
    The results are returned as a dict with a list of found files keyed by the absolute
    directory name.
    :param tgt_dir: The target base directory.
    :param pat: The file pattern to search for.
    :return: A dict where absolute directory names are keys for lists of found file names
        that match the given pattern.
    """
    matchdirs = {}
    for root, dirs, files in os.walk(tgt_dir):
        matches = [match for match in files if fnmatch.fnmatch(match, pat)]
        if matches:
            matchdirs[os.path.abspath(root)] = matches
    return matchdirs

def chunk(seq, chunksize, process=iter):
    """ Yields items from an iterator in iterable chunks.
    From https://gist.github.com/ksamuel/1275417
    """
    it = iter(seq)
    while True:
        yield process(chain([it.next()], islice(it, chunksize - 1)))
