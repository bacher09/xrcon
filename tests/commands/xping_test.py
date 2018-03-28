from .base import BaseCommandTest, ExitException
from xrcon.commands.xping import XPingProgram
from ..base import mock
import collections
import itertools
import argparse
import socket
import errno
import math
import six
from xrcon.utils import (
    PONG_Q2_PACKET, PING_Q2_PACKET, PING_Q3_PACKET, PONG_Q3_PACKET
)


def make_blocking_error():
    if six.PY3:
        raise BlockingIOError(errno.EAGAIN, "Blocking error")
    else:
        raise socket.error(errno.EAGAIN, "Blocking error")


class XPingCommandTest(BaseCommandTest):

    def setUp(self):
        super(XPingCommandTest, self).setUp()
        self.patch_getaddrinfo()
        self.patch_socket()
        self.patch_select()
        self.patch_monotonic_time()
        self.patch_sleep()

    def patch_getaddrinfo(self):
        getaddrinfo_patch = mock.patch('socket.getaddrinfo')
        self.getaddrinfo_mock = getaddrinfo_patch.start()
        self.addCleanup(getaddrinfo_patch.stop)

    def patch_socket(self):
        socket_patch = mock.patch('socket.socket')
        self.socket_mock = socket_patch.start()
        self.addCleanup(socket_patch.stop)
        self.socket_mock.return_value.fileno.return_value = mock.sentinel.fd

    def patch_select(self):
        select_patch = mock.patch('select.select')
        self.select_mock = select_patch.start()
        self.addCleanup(select_patch.stop)

        # default select mock
        def select_side_effect(rlist, wlist, xlist, timeout=None):
            return rlist, wlist, xlist

        self.select_mock.side_effect = select_side_effect

    def patch_monotonic_time(self):
        time_patch = mock.patch('xrcon.commands.xping.monotonic_time')
        self.monotonic_time_mock = time_patch.start()
        self.addCleanup(time_patch.stop)

    def patch_sleep(self):
        sleep_patch = mock.patch('time.sleep')
        self.sleep_mock = sleep_patch.start()
        self.addCleanup(sleep_patch.stop)

    def start_xping(self, args):
        obj = XPingProgram()
        obj.run(args)
        return obj

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

    def test_command_counted(self):
        packets_queue = collections.deque()

        self.getaddrinfo_mock.return_value = [(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
            '',
            ('127.0.0.1', 26001)
        )]

        def sendto_mock(data, addr):
            if data == PING_Q2_PACKET:
                packets_queue.append((PONG_Q2_PACKET, addr))

            return len(data)

        def recvfrom_mock(size):
            try:
                data, addr = packets_queue.popleft()
            except IndexError:
                raise make_blocking_error()
            else:
                return data[:size], addr

        def select_side_effect(rfds, wfds, efds, timeout=None):
            if len(packets_queue) > 0:
                return rfds, wfds, efds
            else:
                return [], [], []

        self.select_mock.side_effect = select_side_effect
        self.socket_mock.return_value.sendto.side_effect = sendto_mock
        self.socket_mock.return_value.recvfrom.side_effect = recvfrom_mock
        self.monotonic_time_mock.side_effect = itertools.count(0.1, 0.02)

        obj = self.start_xping("-p 26001 -c 5 someserver.example".split())

        self.assertEqual(self.socket_mock.return_value.recvfrom.call_count, 5)
        self.assertEqual(obj.packets_lost, 0)
        self.assertEqual(obj.packets_received, 5)
        self.assertEqual(obj.packets_sent, 5)

    def test_command_send_interrupted(self):
        self.getaddrinfo_mock.return_value = [(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
            '',
            ('127.0.0.1', 26000)
        )]

        packets_queue = collections.deque()
        self.send_count = 0

        def sendto_mock(data, addr):
            self.send_count += 1
            if self.send_count > 20:
                raise KeyboardInterrupt

            if data == PING_Q2_PACKET:
                packets_queue.append((PONG_Q2_PACKET, addr))

            return len(data)

        def recvfrom_mock(size):
            try:
                data, addr = packets_queue.popleft()
            except IndexError:
                raise make_blocking_error()
            else:
                return data[:size], addr

        def select_side_effect(rfds, wfds, efds, timeout=None):
            if len(packets_queue) > 0:
                return rfds, wfds, efds
            else:
                return [], [], []

        self.select_mock.side_effect = select_side_effect
        self.socket_mock.return_value.sendto.side_effect = sendto_mock
        self.socket_mock.return_value.recvfrom.side_effect = recvfrom_mock
        self.monotonic_time_mock.side_effect = itertools.count(0.1, 0.02)

        # start test
        obj = self.start_xping("someserver.example".split())
        # evalute result
        self.assertEqual(self.socket_mock.return_value.recvfrom.call_count, 20)
        self.assertEqual(obj.packets_lost, 0)
        self.assertEqual(obj.packets_received, 20)
        self.assertEqual(obj.packets_sent, 20)

    def test_command_recv_interrupted(self):
        self.getaddrinfo_mock.return_value = [(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
            '',
            ('127.0.0.1', 26000)
        )]

        packets_queue = collections.deque()
        self.recv_count = 0

        def sendto_mock(data, addr):

            if data == PING_Q2_PACKET:
                packets_queue.append((PONG_Q2_PACKET, addr))

            return len(data)

        def recvfrom_mock(size):
            if self.recv_count > 19:
                raise KeyboardInterrupt

            try:
                data, addr = packets_queue.popleft()
            except IndexError:
                raise make_blocking_error()
            else:
                self.recv_count += 1
                return data[:size], addr

        def select_side_effect(rfds, wfds, efds, timeout=None):
            if len(packets_queue) > 0:
                return rfds, wfds, efds
            else:
                return [], [], []

        self.select_mock.side_effect = select_side_effect
        self.socket_mock.return_value.sendto.side_effect = sendto_mock
        self.socket_mock.return_value.recvfrom.side_effect = recvfrom_mock
        self.monotonic_time_mock.side_effect = itertools.count(0.1, 0.02)
        # start test
        obj = self.start_xping("someserver.example".split())
        # evalute result
        self.assertEqual(self.socket_mock.return_value.recvfrom.call_count, 21)
        self.assertEqual(obj.packets_lost, 0)
        self.assertEqual(obj.packets_received, 20)
        self.assertEqual(obj.packets_sent, 20)

    def test_command_lost_packets(self):
        self.getaddrinfo_mock.return_value = [(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
            '',
            ('127.0.0.1', 26000)
        )]

        packets_queue = collections.deque()
        self.send_count = 0

        def sendto_mock(data, addr):
            if data == PING_Q2_PACKET and self.send_count % 2 == 0:
                packets_queue.append((PONG_Q2_PACKET, addr))

            self.send_count += 1
            return len(data)

        def recvfrom_mock(size):
            data, addr = packets_queue.popleft()
            return data[:size], addr

        self.socket_mock.return_value.sendto.side_effect = sendto_mock
        self.socket_mock.return_value.recvfrom.side_effect = recvfrom_mock
        self.monotonic_time_mock.side_effect = itertools.count(0.1, 0.02)

        def select_side_effect(rlist, wlist, xlist, timeout=None):
            if len(packets_queue) > 0:
                return rlist, wlist, xlist
            else:
                return [], [], []

        self.select_mock.side_effect = select_side_effect
        # start test
        obj = self.start_xping("-c 10 someserver.example".split())
        # evalute result
        self.assertEqual(obj.packets_lost, 5)
        self.assertEqual(obj.packets_received, 5)
        self.assertEqual(obj.packets_sent, 10)

    def test_command_duplicated_packets(self):
        self.getaddrinfo_mock.return_value = [(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
            '',
            ('127.0.0.1', 26000)
        )]

        packets_queue = collections.deque()
        self.send_count = 0

        def sendto_mock(data, addr):
            if data == PING_Q2_PACKET:
                packets_queue.append((PONG_Q2_PACKET, addr))
                packets_queue.append((PONG_Q2_PACKET, addr))

            self.send_count += 1
            return len(data)

        def recvfrom_mock(size):
            data, addr = packets_queue.popleft()
            return data[:size], addr

        self.socket_mock.return_value.sendto.side_effect = sendto_mock
        self.socket_mock.return_value.recvfrom.side_effect = recvfrom_mock
        self.monotonic_time_mock.side_effect = itertools.count(0.1, 0.02)

        def select_side_effect(rlist, wlist, xlist, timeout=None):
            if len(packets_queue) > 0:
                return rlist, wlist, xlist
            else:
                return [], [], []

        self.select_mock.side_effect = select_side_effect
        # start test
        obj = self.start_xping("-c 10 someserver.example".split())
        # evalute result
        self.assertEqual(obj.packets_duplicated, 10 - 1)  # we don't wait last
        self.assertEqual(obj.packets_sent, 10)
        self.assertEqual(obj.packets_received, 10)

    def test_command_ping_q3(self):
        packets_queue = collections.deque()
        self.getaddrinfo_mock.return_value = [(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
            '',
            ('127.0.0.1', 27000)
        )]

        def sendto_mock(data, addr):
            if data == PING_Q3_PACKET:
                packets_queue.append((PONG_Q3_PACKET, addr))

            return len(data)

        def recvfrom_mock(size):
            try:
                data, addr = packets_queue.popleft()
            except IndexError:
                raise make_blocking_error()
            else:
                return data[:size], addr

        self.socket_mock.return_value.sendto.side_effect = sendto_mock
        self.socket_mock.return_value.recvfrom.side_effect = recvfrom_mock
        self.monotonic_time_mock.side_effect = itertools.count(0.1, 0.02)

        # start test
        obj = self.start_xping(
            "-t q3 -c 10 -p 27000 someserver.example".split()
        )
        # evalute result
        self.assertEqual(obj.packets_lost, 0)
        self.assertEqual(obj.packets_received, 10)
        self.assertEqual(obj.packets_sent, 10)

    def test_command_not_responding(self):
        self.getaddrinfo_mock.return_value = [(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
            '',
            ('127.0.0.1', 26000)
        )]

        def sendto_mock(data, addr):
            return len(data)

        self.monotonic_time_mock.side_effect = itertools.count(0.1, 0.02)
        self.socket_mock.return_value.sendto.side_effect = sendto_mock
        self.socket_mock.return_value.recvfrom.side_effect = socket.error
        self.select_mock.side_effect = None
        self.select_mock.return_value = [], [], []
        # start test
        obj = self.start_xping("-c 10 someserver.example".split())
        # evalute result
        self.assertEqual(obj.packets_lost, 10)
        self.assertEqual(obj.packets_received, 0)
        self.assertEqual(obj.packets_sent, 10)

    def test_command_lost_blocking_error(self):
        self.getaddrinfo_mock.return_value = [(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
            '',
            ('127.0.0.1', 26000)
        )]

        packets_queue = collections.deque()
        self.send_count = 0

        def sendto_mock(data, addr):
            if data == PING_Q2_PACKET and self.send_count % 2 == 0:
                packets_queue.append((PONG_Q2_PACKET, addr))

            self.send_count += 1
            return len(data)

        def recvfrom_mock(size):
            try:
                data, addr = packets_queue.popleft()
            except IndexError:
                raise make_blocking_error()
            else:
                return data[:size], addr

        self.socket_mock.return_value.sendto.side_effect = sendto_mock
        self.socket_mock.return_value.recvfrom.side_effect = recvfrom_mock
        self.monotonic_time_mock.side_effect = itertools.count(0.1, 0.02)
        # start test
        obj = self.start_xping("-c 20 someserver.example".split())
        # evalute result
        self.assertEqual(obj.packets_lost, 10)
        self.assertEqual(obj.packets_received, 10)
        self.assertEqual(obj.packets_sent, 20)

    def test_command_recv_error(self):
        self.getaddrinfo_mock.return_value = [(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
            '',
            ('127.0.0.1', 26000)
        )]

        def sendto_mock(data, addr):
            return len(data)

        def recvfrom_mock(size):
            raise socket.error(errno.ENOTSOCK)

        self.socket_mock.return_value.sendto.side_effect = sendto_mock
        self.socket_mock.return_value.recvfrom.side_effect = recvfrom_mock
        self.monotonic_time_mock.side_effect = itertools.count(0.1, 0.02)
        # start test
        with self.assertRaises(socket.error):
            self.start_xping("someserver.example".split())

    def test_command_receive_bad_packets(self):
        self.getaddrinfo_mock.return_value = [(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP,
            '',
            ('127.0.0.1', 26000)
        )]
        self.monotonic_time_mock.return_value = 0.1

        packets_queue = collections.deque()
        packets_queue.extend([
            (PONG_Q2_PACKET, ('8.8.8.8', 26001)),
            (PONG_Q2_PACKET, ('127.0.0.1', 26000)),
        ])

        def sendto_mock(data, addr):
            if data == PING_Q2_PACKET:
                packets_queue.append((six.b('packet with bad data 1'), addr))
                packets_queue.append((PONG_Q2_PACKET, addr))
                packets_queue.append((six.b('packet with bad data 2'), addr))
                # update time
                self.monotonic_time_mock.return_value += 0.2

            return len(data)

        def recvfrom_mock(size):
            try:
                data, addr = packets_queue.popleft()
            except IndexError:
                raise make_blocking_error()
            else:
                return data[:size], addr

        self.socket_mock.return_value.sendto.side_effect = sendto_mock
        self.socket_mock.return_value.recvfrom.side_effect = recvfrom_mock
        # start test
        obj = self.start_xping("-c 10 someserver.example".split())
        # evalute result
        self.assertEqual(obj.packets_lost, 0)
        self.assertEqual(obj.packets_received, 10)
        self.assertEqual(obj.packets_sent, 10)
