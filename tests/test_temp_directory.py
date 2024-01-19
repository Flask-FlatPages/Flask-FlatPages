"""
=========================
tests.test_temp_directory
=========================

Provide temp directory context manager and tests for it.

"""

import os
import shutil
import tempfile
import unittest

from contextlib import contextmanager


@contextmanager
def temp_directory():
    """
    This context manager gives the path to a new temporary directory that is
    deleted (with all it's content) at the end of the with block.
    """
    directory = tempfile.mkdtemp()
    try:
        yield directory
    finally:
        shutil.rmtree(directory)


class TestTempDirectory(unittest.TestCase):
    def test_exception(self):
        try:
            with temp_directory() as temp:
                assert os.path.isdir(temp)
                1 / 0
        except ZeroDivisionError:
            pass
        else:
            assert False, "Exception did not propagate"
        assert not os.path.exists(temp)

    def test_removed(self):
        with temp_directory() as temp:
            assert os.path.isdir(temp)
        # should be removed now
        assert not os.path.exists(temp)

    def test_writing(self):
        with temp_directory() as temp:
            filename = os.path.join(temp, "foo")
            with open(filename, "w") as fd:
                fd.write("foo")
            assert os.path.isfile(filename)
        assert not os.path.exists(temp)
        assert not os.path.exists(filename)
