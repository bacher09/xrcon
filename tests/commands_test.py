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


class XRconCommandTest(TestCase):

    def setUp(self):
        def read_fun(self, names):
            self.readfp(six.StringIO(CONFIG_EXAMPLE))

        self.read_patcher = mock.patch \
            .object(ConfigParser, 'read', autospec=True, side_effect=read_fun)

        self.xrcon_patcher = mock.patch('xrcon.commands.XRcon', autospec=True,
                                        RCON_TYPES=XRcon.RCON_TYPES)

        self.read_mock = self.read_patcher.start()
        self.xrcon_mock = self.xrcon_patcher.start()
        self.addCleanup(self.stop_mocks)
        self.xrcon_mock.create_by_server_str.return_value = \
            self.xrcon_mock.return_value

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
