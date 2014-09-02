import time
import hashlib
import hmac
import six
import re


md4 = lambda *args, **kw: hashlib.new('MD4', *args, **kw)


RCON_PACKET_HEADER = six.b('\xFF' * 4)
RCON_RESPONSE_HEADER = RCON_PACKET_HEADER + six.b('n')
CHALLENGE_PACKET = RCON_PACKET_HEADER + six.b('getchallenge')
CHALLENGE_RESPONSE_HEADER = RCON_PACKET_HEADER + six.b('challenge ')
ADDR_STR_RE = re.compile(r"""
    ^(?:
        (?P<host>[^:]+)               # ipv4 address or host name
        |\[(?P<host6>[a-zA-Z0-9:]+)\] # ipv6 address in square brackets
    )                                 # end of host part
    (?::(?P<port>\d+))?$              # optional port part
    """, re.VERBOSE)


def rcon_nosecure_packet(password, command):
    return RCON_PACKET_HEADER + six.b('rcon {password} {command}'
        .format(password=password, command=command))


if six.PY2: # pragma: no cover
    def to_bytes(text):
        return str(text)

    def hmac_md4(key, msg):
        return hmac.new(key, msg, md4)
else: # pragma: no cover
    def to_bytes(text):
        if not isinstance(text, bytes):
            text = six.b(text)

        return text

    def hmac_md4(key, msg):
        key, msg = to_bytes(key), to_bytes(msg)
        return hmac.new(key, msg, md4)


def rcon_secure_time_packet(password, command):
    cur_time = time.time()
    key = hmac_md4(password, "{time:6f} {command}"
            .format(time=cur_time, command=command)).digest()
    return six.b('').join([
        RCON_PACKET_HEADER,
        six.b('srcon HMAC-MD4 TIME '),
        key,
        six.b(' {time:6f} {command}'.format(time=cur_time, command=command))
    ])


def parse_challenge_response(response):
    l = len(CHALLENGE_RESPONSE_HEADER)
    return response[l:l+11]


def rcon_secure_challenge_packet(password, challenge, command):
    password = to_bytes(password)
    challenge = to_bytes(challenge)
    command = to_bytes(command)
    hmac_key = six.b(' ').join([challenge, command])
    key = hmac_md4(password, hmac_key).digest()
    return six.b('').join([
        RCON_PACKET_HEADER,
        six.b('srcon HMAC-MD4 CHALLENGE '),
        key,
        six.b(' '),
        challenge,
        six.b(' '),
        command
    ])


def parse_rcon_response(packet):
    l = len(RCON_RESPONSE_HEADER)
    return packet[l:]


def parse_server_addr(str_addr, default_port=26000):
    """Parse address and returns host and port

    Args:
        str_addr --- string that contains server ip or hostname and optionaly
        port

    Returns: tuple (host, port)

    Examples:

    >>> parse_server_addr('127.0.0.1:26006')
    ('127.0.0.1', 26006)
    >>> parse_server_addr('[2001:db8:85a3:8d3:1319:8a2e:370:7348]:26006')
    ('2001:db8:85a3:8d3:1319:8a2e:370:7348', 26006)
    >>> parse_server_addr('[2001:db8:85a3:8d3:1319:8a2e:370:7348]')
    ('2001:db8:85a3:8d3:1319:8a2e:370:7348', 26000)
    >>> parse_server_addr('localhost:123')
    ('localhost', 123)
    >>> parse_server_addr('localhost:1d23')
    Traceback (most recent call last):
        ...
    ValueError: Bad address string "localhost:1d23"
    """
    m = ADDR_STR_RE.match(str_addr)
    if m is None:
        raise ValueError('Bad address string "{0}"'.format(str_addr))

    dct = m.groupdict()
    port = dct.get('port')
    if port is None:
        port = default_port
    else:
        port = int(port) # Caution: could raise ValueEror or TypeError

    if port == 0:
        raise ValueError("Port can't be zero")

    host = dct['host'] if dct['host'] else dct['host6']
    return host, port
