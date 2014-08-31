import sys
import six


try:
    from unittest import mock
except ImportError:
    import mock


def py26_gt():
    return sys.version_info[:2] > (2, 6)


if py26_gt():
    import unittest
else:
    import unittest2 as unittest


class TestCase(unittest.TestCase):

    if six.PY2:
        def assertCountEqual(self, first, second, msg=None):
            return self.assertItemsEqual(first, second, msg=msg)
