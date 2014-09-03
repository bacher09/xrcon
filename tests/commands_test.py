from .base import TestCase, mock, unittest
from xrcon.commands import xrcon, XRcon, ConfigParser
from xrcon.utils import parse_server_addr
import socket
import six


CONFIG_EXAMPLE = """\
[DEFAULT]
server = 127.0.0.1
password = secret
type = 0
timeout = 1.2

[minsta]
server = 127.0.0.1:26001

[other]
server = ::1
password = other
type = 2
"""


CONFIG_EXAMPLE2 = """\
[one]
server = 7.7.7.7
password = password

[two]
server = 5.5.5.5
password = qwerty
type = 2
"""


INVALID_CONFIG = """\
[corupted]
server = bad
password = here
type = 15

[corupted2]
server = ::1
password = 1234
timeout = bad
"""


class ExitException(Exception):
    pass


class XRconCommandTest(TestCase):

    def setUp(self):
        self.patch_xrcon()
        self.patch_configparser()
        self.patch_argparse()

    def patch_configparser(self):
        def read_fun(self, names):
            self.readfp(six.StringIO(CONFIG_EXAMPLE))

        read_patcher = mock.patch.object(ConfigParser, 'read', autospec=True,
                                         side_effect=read_fun)
        self.read_mock = read_patcher.start()
        self.addCleanup(read_patcher.stop)

    def patch_xrcon(self):
        xrcon_patcher = mock.patch('xrcon.commands.XRcon', autospec=True,
                                   RCON_TYPES=XRcon.RCON_TYPES)

        self.xrcon_mock = xrcon_patcher.start()
        self.addCleanup(xrcon_patcher.stop)

        def create_by_server_str(server_addr, *args, **kwargs):
            host, port = parse_server_addr(server_addr)
            return mock.DEFAULT

        self.xrcon_mock.create_by_server_str.return_value = \
            self.xrcon_mock.return_value
        self.xrcon_mock.create_by_server_str.side_effect = create_by_server_str

    def patch_argparse(self):
        self.arg_exit_mock = mock.Mock(spec=[])
        self.arg_error_mock = mock.Mock(spec=[])
        self.arg_exit_mock.side_effect = ExitException
        self.arg_error_mock.side_effect = ExitException
        argparse_patch = mock.patch.multiple(
            'argparse.ArgumentParser',
            exit=self.arg_exit_mock,
            error=self.arg_error_mock
        )
        argparse_patch.start()
        self.addCleanup(argparse_patch.stop)

        filetype_patch = mock.patch('argparse.FileType')
        self.filetype_mock = filetype_patch.start()
        self.addCleanup(filetype_patch.stop)

    def stop_mocks(self):
        self.read_patcher.stop()
        self.xrcon_patcher.stop()

    def test_simple(self):
        xrcon_mock = self.xrcon_mock
        xrcon_mock.return_value.execute.return_value = six.b('Result')
        xrcon("-s server -p password -t 2 status".split())
        self.assertTrue(self.read_mock.called)
        xrcon_mock.return_value.execute.assert_called_once_with('status', 1.2)

        xrcon_mock.create_by_server_str \
            .assert_called_once_with('server', 'password', 2, 1.2)

        xrcon_mock.reset_mock()
        xrcon_mock.create_by_server_str.return_value = xrcon_mock.return_value
        xrcon("-n minsta status".split())
        xrcon_mock.return_value.execute.assert_called_once_with('status', 1.2)
        xrcon_mock.create_by_server_str \
            .assert_called_once_with('127.0.0.1:26001', 'secret', 0, 1.2)

        # test empty
        xrcon_mock.return_value.execute.return_value = None
        xrcon("-s server -p password -t 2 empty".split())

    @mock.patch('getpass.getpass')
    def test_config(self, getpass_mock):
        getpass_mock.return_value = six.u('getpass')
        self.xrcon_mock.return_value.execute.return_value = six.b('Result')
        self.filetype_mock.return_value.return_value = \
            six.StringIO(CONFIG_EXAMPLE2)
        xrcon("--config myconfig.ini -s server -t 2 status"
              .split())

    def test_invalid(self):
        with self.assertRaises(ExitException):
            xrcon("-s server -p passw -t 3 status".split())

        with self.assertRaises(ExitException):
            xrcon("-n bad_section status".split())

        self.filetype_mock.return_value.return_value = \
            six.StringIO(INVALID_CONFIG)

        with self.assertRaises(ExitException):
            xrcon("--config invalid.ini -n corupted status".split())

        with self.assertRaises(ExitException):
            xrcon("--config invalid.ini -n corupted2 status".split())

        with self.assertRaises(ExitException):
            xrcon("-s server:0 -p 1234 status".split())

        self.xrcon_mock.return_value.connect.side_effect = socket.gaierror
        with self.assertRaises(ExitException):
            xrcon("-s badhost -p password status".split())
