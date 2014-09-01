import socket
import time
from functools import wraps
from .utils import (
    rcon_nosecure_packet,
    rcon_secure_time_packet,
    rcon_secure_challenge_packet,
    parse_challenge_response,
    CHALLENGE_PACKET,
    CHALLENGE_RESPONSE_HEADER
)


class NotConnected(Exception):
    pass


def connection_required(fun):
    @wraps(fun)
    def wrapper(self, *args, **kwargs):
        if self.sock is None:
            raise NotConnected("You should call connect first")

        return fun(self, *args, **kwargs)

    return wrapper


class XRcon(object):

    RCON_NOSECURE = 0
    RCON_SECURE_TIME = 1
    RCON_SECURE_CHALLENGE = 2

    SECURE_TYPES = frozenset([
        RCON_NOSECURE, RCON_SECURE_TIME, RCON_SECURE_CHALLENGE
    ])

    MAX_PACKET_SIZE = 1399
    CHALLENGE_TIMEOUT = 3

    _secure_rcon = RCON_SECURE_TIME

    def __init__(self, host, port, password, secure_rcon=RCON_SECURE_TIME):
        self.host = host
        self.port = port
        self.password = password
        self.secure_rcon = secure_rcon
        self.sock = None

    @property
    def secure_rcon(self):
        return self._secure_rcon

    @secure_rcon.setter
    def secure_rcon(self, value):
        if value not in self.SECURE_TYPES:
            raise ValueError("Bad value of secure_rcon")

        self._secure_rcon = value

    def connect(self):
        family, stype, proto, cname, sockaddr = self.best_connection_params(
            self.host, self.port)
        self.sock = socket.socket(family, stype)
        self.sock.connect(sockaddr)

    @connection_required
    def close(self):
        self.sock.close()
        self.sock = None

    @connection_required
    def send(self, command):
        if self.secure_rcon == self.RCON_NOSECURE:
            self.sock.send(rcon_nosecure_packet(self.password, command))
        elif self.secure_rcon == self.RCON_SECURE_TIME:
            self.sock.send(rcon_secure_time_packet(self.password, command))
        elif self.secure_rcon == self.RCON_SECURE_CHALLENGE:
            challenge = self.getchallenge()
            self.sock.send(rcon_secure_challenge_packet(self.password,
                                                        challenge, command))
        else:
            raise ValueError("Bad value of secure_rcon")

    @connection_required
    def getchallenge(self):
        self.sock.send(CHALLENGE_PACKET)
        # wait challenge response
        timeout = time.time() + self.CHALLENGE_TIMEOUT
        while time.time() < timeout:
            packet = self.sock.recv(self.MAX_PACKET_SIZE)
            if packet.startswith(CHALLENGE_RESPONSE_HEADER):
                return parse_challenge_response(packet)

        raise socket.timeout("Challenge timeout")

    @staticmethod
    def best_connection_params(host, port):
        params = socket.getaddrinfo(host, port, 0, socket.SOCK_DGRAM)
        for data in params:
            if data[0] == socket.AF_INET:
                return data

        if len(params) > 0:
            return params[0]
