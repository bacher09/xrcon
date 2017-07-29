from .base_command_test import BaseCommandTest, ExitException
from xrcon.commands import XPingProgram
from .base import mock
import argparse
import socket
import math


class XPingCommandTest(BaseCommandTest):

    def setUp(self):
        super(XPingCommandTest, self).setUp()
        self.patch_getaddrinfo()

    def patch_getaddrinfo(self):
        getaddrinfo_patch = mock.patch('socket.getaddrinfo')
        self.getaddrinfo_mock = getaddrinfo_patch.start()
        self.addCleanup(getaddrinfo_patch.stop)

    def test_statistics(self):
        xping = XPingProgram()
        rtt_vals = [0.15, 0.12, 0.13, 0.14]
        for rtt in rtt_vals:
            xping.update_statics(rtt)

        xping.packets_sent = len(rtt_vals)
        xping.packets_received = len(rtt_vals)
        rtt_min, rtt_avg, rtt_max, mdev = xping.get_statistics()
        self.assertAlmostEqual(rtt_min, min(rtt_vals))
        self.assertAlmostEqual(rtt_max, max(rtt_vals))
        calc_avg = sum(rtt_vals) / len(rtt_vals)
        self.assertAlmostEqual(rtt_avg, calc_avg)
        dev_sq = sum((rtt - rtt_avg) ** 2 for rtt in rtt_vals) / len(rtt_vals)
        stddev = math.sqrt(dev_sq)
        self.assertAlmostEqual(mdev, stddev)

    def test_find_server(self):

        def find_server(text):
            xping = XPingProgram()
            namespace = xping.parser.parse_args(text.split())
            return xping.find_server(namespace)

        self.getaddrinfo_mock.return_value = [(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
            '',
            ('127.0.0.1', 26001)
        )]
        server_info = find_server("-p 26001 xonotic.server")
        self.getaddrinfo_mock.assert_called_once_with(
            "xonotic.server", 26001, socket.AF_UNSPEC, socket.SOCK_DGRAM,
            socket.IPPROTO_UDP
        )
        self.assertEqual(server_info[4][0], '127.0.0.1')

        self.getaddrinfo_mock.reset_mock()
        self.getaddrinfo_mock.side_effect = socket.gaierror("Test error")
        with self.assertRaises(ExitException):
            find_server("bad.server")

        self.getaddrinfo_mock.reset_mock()
        self.getaddrinfo_mock.side_effect = None
        self.getaddrinfo_mock.return_value = [(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
            '',
            ('127.0.0.1', 26000)
        )]
        find_server("-4 xonotic.server")
        self.getaddrinfo_mock.assert_called_once_with(
            "xonotic.server", 26000, socket.AF_INET, socket.SOCK_DGRAM,
            socket.IPPROTO_UDP
        )

        self.getaddrinfo_mock.reset_mock()
        self.getaddrinfo_mock.return_value = []
        with self.assertRaises(ExitException):
            find_server("xonotic.server")

    def cli_parser_test(self):

        def parse_arguments(text):
            xping = XPingProgram()
            return xping.parser.parse_args(text.split())

        namespace = parse_arguments("xonotic.server")
        self.assertEqual(namespace.server, "xonotic.server")

        namespace = parse_arguments("-p 3030 -i 4 -c 8 xonotic.server")
        self.assertEqual(namespace.port, 3030)
        self.assertAlmostEqual(namespace.interval, 4.0)
        self.assertEqual(namespace.count, 8)

        namespace = parse_arguments("-6 -c 15 xonotic.server")
        self.assertEqual(namespace.proto, socket.AF_INET6)

        with self.assertRaises(ExitException):
            parse_arguments("-c -5 xonotic")

        with self.assertRaises(argparse.ArgumentTypeError):
            XPingProgram.count_validator("-2")

        with self.assertRaises(ExitException):
            parse_arguments("-c b xonotic")

        with self.assertRaises(ExitException):
            parse_arguments("-p 0 xonotic")

        with self.assertRaises(ExitException):
            parse_arguments("-p 65536 xonotic")

        with self.assertRaises(ExitException):
            parse_arguments("-p bad_port xonotic")

        with self.assertRaises(ExitException):
            parse_arguments("-i 0.0001 xonotic")

        with self.assertRaises(ExitException):
            parse_arguments("-i bad xonotic")
