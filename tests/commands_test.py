from .base import TestCase, mock, unittest
from xrcon.commands import xrcon, XRcon, ConfigParser
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
        self.xrcon_mock.create_by_server_str.return_value = \
            self.xrcon_mock.return_value

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

    @mock.patch('getpass.getpass')
    @mock.patch('argparse.FileType')
    def test_config(self, ftype_mock, getpass_mock):
        getpass_mock.return_value = six.u('getpass')
        self.xrcon_mock.return_value.execute.return_value = six.b('Result')
        ftype_mock.return_value.return_value = six.StringIO(CONFIG_EXAMPLE2)
        xrcon("--config myconfig.ini -s server -t 2 status"
              .split())

    def test_invalid(self):
        with self.assertRaises(ExitException):
            xrcon("-s server -p passw -t 3 status".split())

        with self.assertRaises(ExitException):
            xrcon("-n bad_section status".split())
