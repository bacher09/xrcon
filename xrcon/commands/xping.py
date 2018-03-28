import argparse
import socket
import select
import errno
import math
import time
import six
from collections import namedtuple
from .base import BaseProgram
from ..utils import (
    PING_Q2_PACKET, PONG_Q2_PACKET, PING_QFUSION_PACKET, PONG_QFUSION_PACKET,
    PING_Q3_PACKET, PONG_Q3_PACKET, MAX_PACKET_SIZE
)


if six.PY3:  # pragma: no cover
    monotonic_time = time.monotonic
else:   # pragma: no cover
    monotonic_time = time.time


PingProtocol = namedtuple('PingProtocol', ['ping', 'pong'])


Q2_PROTOCOL = PingProtocol(PING_Q2_PACKET, PONG_Q2_PACKET)
QFUSION_PROTOCOL = PingProtocol(PING_QFUSION_PACKET, PONG_QFUSION_PACKET)
Q3_PROTOCOL = PingProtocol(PING_Q3_PACKET, PONG_Q3_PACKET)


class XPingProgram(BaseProgram):

    description = 'Ping remote Xonotic server'
    minimal_interval = 0.5
    default_interval = 1.0
    default_port = 26000
    ping_protocols = {
        'q2': Q2_PROTOCOL,
        'q3': Q3_PROTOCOL,
        'qfusion': QFUSION_PROTOCOL
    }
    default_ping_protocol = 'q2'

    def __init__(self):
        super(XPingProgram, self).__init__()
        self.server = None
        self.sock = None
        self.ping_proto = None
        self.server_name = None
        self.packets_sent = 0
        self.packets_received = 0
        self.packets_duplicated = 0
        # packets that are lost for sure
        self.packets_lost = 0
        # packets_sent - packets_received can be wrong for one packet
        # because program can be terminated before we received response
        # from remote server (for example when user press Ctrl+C we stop
        # waiting for response, so at the end we can't know for sure
        # that this last packet was lost)
        self.rtt_min = None
        self.rtt_max = None
        self.rtt_sum = 0
        self.rtt_sum2 = 0

    def run(self, args=None):
        namespace = self.parser.parse_args(args)
        self.ping_proto = self.ping_protocols[namespace.ping_proto]
        self.execute(namespace)

    def find_server(self, namespace):
        try:
            servers = socket.getaddrinfo(
                namespace.server,
                namespace.port,
                namespace.proto,
                socket.SOCK_DGRAM,
                socket.IPPROTO_UDP
            )
        except socket.gaierror as exc:
            error_msg = "Can't find server: {err}\n".format(err=exc.strerror)
            self.parser.exit(255, error_msg)
        else:
            # return first picked server
            if len(servers) > 0:
                return servers[0]
            else:
                self.parser.exit(255, "getaddrinfo returned empty list")

    def make_socket(self, namespace):
        inet_proto, sock_type, sock_proto, _, addr = \
                self.find_server(namespace)
        self.addr = addr
        self.sock = socket.socket(inet_proto, sock_type, sock_proto)
        self.sock.setblocking(False)

    def print_header(self, namespace):
        print("XPING {server} ({ip_addr}) port: {port}".format(
            server=namespace.server,
            ip_addr=self.addr[0],
            port=namespace.port
        ))

    def print_footer(self):
        print('\n--- {server} ping statistics ---'.format(
            server=self.server_name
        ))

        loss = self.packets_sent - self.packets_received
        loss_percent = (loss / self.packets_sent) * 100
        part = "{sent:d} packets transmitted, {received:d} received,".format(
            sent=self.packets_sent,
            received=self.packets_received,
        )

        if self.packets_duplicated > 0:
            part += " {dup:d} duplicated,".format(dup=self.packets_duplicated)

        part += " {loss:0.1f}% packet loss".format(loss=loss_percent)
        print(part)

        if self.packets_duplicated > 0:
            print("WARNING: Results might be incorrect because"
                  " of duplicated packets")

        self.pring_stats()

    def pring_stats(self):
        if self.packets_received < 1:
            # there is no any stats
            # print empty line so output format will be same
            print("")
            return

        rtt_min, rtt_avg, rtt_max, mdev = self.get_statistics()
        print(
            "rtt min/avg/max/mdev = "
            "{min:0.3f}/{avg:0.3f}/{max:0.3f}/{mdev:0.3f} ms".format(
                min=rtt_min * 1000,
                avg=rtt_avg * 1000,
                max=rtt_max * 1000,
                mdev=mdev * 1000
            ))

    def update_statics(self, rtt):
        if self.rtt_min is None or self.rtt_min > rtt:
            self.rtt_min = rtt

        if self.rtt_max is None or self.rtt_max < rtt:
            self.rtt_max = rtt

        self.rtt_sum += rtt
        self.rtt_sum2 += rtt ** 2

    def get_statistics(self):
        rtt_min = 0.0 if self.rtt_min is None else self.rtt_min
        rtt_max = 0.0 if self.rtt_max is None else self.rtt_max
        rtt_avg = self.rtt_sum / self.packets_received
        # calc stddev
        a = self.rtt_sum2 / self.packets_received
        b = rtt_avg ** 2
        if a > b:
            std_dev = math.sqrt(a - b)
        else:
            # seems we have float point rounding error
            # most likely for this case stddev is near zero
            std_dev = 0
        return rtt_min, rtt_avg, rtt_max, std_dev

    def do_ping(self, count=0, interval=1.0):
        self.ping_start = monotonic_time()
        while True:
            self.sock.sendto(self.ping_proto.ping, self.addr)
            received, time_left = self.wait_response(interval)
            self.packets_sent += 1
            if received:
                self.packets_received += 1
                rtt = interval - time_left
                self.response_received(rtt)
                self.update_statics(rtt)
            else:
                self.packets_lost += 1

            if count != 0 and self.packets_sent >= count:
                break

            while time_left > 0:
                # handle duplicated packets
                received, time_left = self.wait_response(time_left)
                if received:
                    self.packets_duplicated += 1
                    self.duplicate_received()

    def execute(self, namespace):
        self.server_name = namespace.server
        self.make_socket(namespace)
        self.print_header(namespace)
        try:
            self.do_ping(count=namespace.count, interval=namespace.interval)
        except KeyboardInterrupt:
            self.print_footer()
        else:
            self.print_footer()
        finally:
            self.sock.close()

    def response_received(self, time_spent):
        print("{ip_addr} port={port} time={time_ms:0.2f} ms".format(
            ip_addr=self.addr[0],
            port=self.addr[1],
            time_ms=time_spent * 1000
        ))

    def duplicate_received(self):
        print("{ip_addr} port={port} DUPLICATE".format(
            ip_addr=self.addr[0], port=self.addr[1]
        ))

    def wait_response(self, timeout):
        time_left = timeout
        while time_left > 0:
            received, time_left = self.check_response(time_left)
            if received:
                return True, time_left

        return False, 0

    def check_response(self, timeout):
        start_time = monotonic_time()
        rlst, _, _ = select.select([self.sock.fileno()], [], [], timeout)
        if rlst:
            try:
                data, addr = self.sock.recvfrom(MAX_PACKET_SIZE)
                if data == self.ping_proto.pong and addr == self.addr:
                    end_time = monotonic_time()
                    timeout -= end_time - start_time
                    return True, timeout
                else:
                    end_time = monotonic_time()
                    timeout -= end_time - start_time
                    return False, timeout
            except socket.error as e:  # use BlockingIOError in python 3
                if e.errno != errno.EAGAIN:
                    raise
                # select returned that socket is ready for reading but during
                # recvfrom we get error that there is no data in socket buffer.
                # this might happen in some rare cases
                # https://stackoverflow.com/questions/5351994/will-read-ever-block-after-select
                # https://stackoverflow.com/questions/23577888/can-i-guarantee-that-recv-will-not-block-after-select-reports-that-the-socke
                return False, 0
        else:
            return False, 0

    @staticmethod
    def port_validator(port_str):
        try:
            port_val = int(port_str)
        except ValueError:
            raise argparse.ArgumentTypeError("port should be integer")
        else:
            if 0 < port_val <= 65535:
                return port_val
            else:
                msg = 'Port should be in range (0, 65535]'
                raise argparse.ArgumentTypeError(msg)

    @classmethod
    def interval_validator(cls, interval_str):
        try:
            interval_val = float(interval_str)
        except ValueError:
            raise argparse.ArgumentTypeError("interval should be float or int")
        else:
            if interval_val >= cls.minimal_interval:
                return interval_val
            else:
                msg = "interval should be more or equal to {0}" \
                            .format(cls.minimal_interval)
                raise argparse.ArgumentTypeError(msg)

    @staticmethod
    def count_validator(count_str):
        try:
            count_val = int(count_str)
        except ValueError:
            raise argparse.ArgumentTypeError("count should be interger")
        else:
            if count_val >= 0:
                return count_val
            else:
                msg = "count should be zero or more"
                raise argparse.ArgumentTypeError(msg)

    @classmethod
    def build_parser(cls):
        parser = super(XPingProgram, cls).build_parser()
        parser.add_argument('-t', '--protocol', dest='ping_proto',
                            default=cls.default_ping_protocol,
                            choices=cls.ping_protocols.keys())
        parser.add_argument('-p', '--port', default=cls.default_port,
                            type=cls.port_validator,
                            help='udp port where to send packets')
        interval_help = 'interval in seconds between packets,' \
                        ' default {:0.1f}'.format(cls.default_interval)
        parser.add_argument('-i', '--interval', default=cls.default_interval,
                            type=cls.interval_validator, help=interval_help)
        parser.add_argument('-4', action='store_const', const=socket.AF_INET,
                            dest="proto", default=socket.AF_UNSPEC,
                            help='Use only IPv4 protocol')
        parser.add_argument('-6', action='store_const', const=socket.AF_INET6,
                            dest="proto", help='Use only IPv6 protocol')
        parser.add_argument('-c', '--count', default=0,
                            type=cls.count_validator)
        parser.add_argument('server', type=str)
        return parser
