from ..base import TestCase, mock


class ExitException(Exception):
    pass


class BaseCommandTest(TestCase):

    def setUp(self):
        self.patch_argparse()

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
