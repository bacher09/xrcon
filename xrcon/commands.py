import argparse
import getpass
import os.path
import socket
import select
import errno
import math
import time
import sys
import six
from .client import XRcon
from .utils import PING_Q2_PACKET, PONG_Q2_PACKET, MAX_PACKET_SIZE


try:  # pragma: no cover
    from configparser import NoSectionError, NoOptionError, ConfigParser
except ImportError:  # pragma: no cover
    from ConfigParser import NoSectionError, NoOptionError, \
        SafeConfigParser as ConfigParser


if six.PY3:  # pragma: no cover
    monotonic_time = time.monotonic
else:   # pragma: no cover
    monotonic_time = time.time


class XRconProgram(object):

    CONFIG_DEFAULTS = {
        'timeout': '0.7',
        'type': '1'
    }

    CONFIG_NAME = "~/.xrcon.ini"

    def __init__(self):
        self.parser = self.build_parser()

    def run(self, args=None):
        namespace = self.parser.parse_args(args)
        self.execute(namespace)

    def execute(self, namespace):
        config = self.parse_config(namespace.config)
        try:
            cargs = self.rcon_args(config, namespace, namespace.name)
        except (NoOptionError, NoSectionError, ValueError) as e:
            message = "Bad configuratin file: {msg}".format(msg=str(e))
            self.parser.error(message)

        try:
            rcon = XRcon \
                .create_by_server_str(cargs['server'], cargs['password'],
                                      cargs['type'], cargs['timeout'])
        except ValueError as e:
            self.parser.error(str(e))

        try:
            rcon.connect()
            try:
                data = rcon.execute(self.command(namespace), cargs['timeout'])
                if data:
                    self.write(data.decode('utf8'))
            finally:
                rcon.close()
        except socket.error as e:
            self.parser.error(str(e))

    def write(self, message):
        assert isinstance(message, six.text_type), "Bad text type"
        sys.stdout.write(message)

    @staticmethod
    def command(namespace):
        return six.u(' ').join(namespace.command)

    @staticmethod
    def build_parser():
        parser = argparse.ArgumentParser(description='Executes rcon command')
        parser.add_argument('--config', type=argparse.FileType('r'))
        parser.add_argument('--timeout', type=float)
        parser.add_argument('-n', '--name')
        parser.add_argument('-s', '--server')
        parser.add_argument('-p', '--password')
        parser.add_argument('-t', '--type', type=int, choices=XRcon.RCON_TYPES)
        parser.add_argument('command', nargs='+')
        return parser

    @classmethod
    def parse_config(cls, file=None):
        config = ConfigParser(defaults=cls.CONFIG_DEFAULTS)

        if file is not None:
            config.readfp(file)
        else:
            config.read([os.path.expanduser(cls.CONFIG_NAME)])

        return config

    @staticmethod
    def rcon_args(config, namespace, name=None):
        if name is None:
            name = 'DEFAULT'

        dct = {}
        cval = getattr(namespace, 'server')
        dct['server'] = cval if cval else config.get(name, 'server')

        cval = getattr(namespace, 'password')
        try:
            dct['password'] = cval if cval else config.get(name, 'password')
        except NoOptionError:
            dct['password'] = getpass.getpass()

        cval = getattr(namespace, 'type')
        dct['type'] = cval if cval else config.getint(name, 'type')
        if dct['type'] not in XRcon.RCON_TYPES:
            raise ValueError("Invalid rcon type")

        cval = getattr(namespace, 'timeout')
        dct['timeout'] = cval if cval else config.getfloat(name, 'timeout')

        return dct

    @classmethod
    def start(cls, args=None):
        obj = cls()
        obj.run(args=args)
        return obj


class XPingProgram(object):

    description = 'Ping remote Xonotic server'
    minimal_interval = 0.5
    default_interval = 1.0
    default_port = 26000

    def __init__(self):
        self.parser = self.build_parser()
        self.server = None
        self.sock = None
        self.server_name = None
        self.packets_sent = 0
        self.packets_received = 0
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

        # TODO: packets_received can be bigger then packets_sent
        loss = self.packets_sent - self.packets_received
        loss_percent = (loss / self.packets_sent) * 100
        fmt_string = "{sent:d} packets transmitted, {received:d} received, " \
                     "{loss:0.1f}% packet loss"

        print(fmt_string.format(
            sent=self.packets_sent,
            received=self.packets_received,
            loss=loss_percent
        ))

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
            self.sock.sendto(PING_Q2_PACKET, self.addr)
            self.packets_sent += 1
            received, time_left = self.wait_response(interval)
            if received:
                self.packets_received += 1
                rtt = interval - time_left
                self.response_received(rtt)
                self.update_statics(rtt)
            else:
                self.packets_lost += 1

            if count != 0 and self.packets_sent >= count:
                break

            # TODO: process duplicated packets
            time.sleep(time_left)

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
                if data == PONG_Q2_PACKET and addr == self.addr:
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
        parser = argparse.ArgumentParser(description=cls.description)
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

    @classmethod
    def start(cls, args=None):
        obj = cls()
        obj.run(args=args)
        return obj
