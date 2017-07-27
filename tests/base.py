import six
import unittest


try:
    from unittest import mock
except ImportError:
    import mock  # NOQA


class TestCase(unittest.TestCase):

    if six.PY2:
        def assertCountEqual(self, first, second, msg=None):
            return self.assertItemsEqual(first, second, msg=msg)
