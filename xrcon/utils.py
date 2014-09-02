import time
import hashlib
import hmac
import six


md4 = lambda *args, **kw: hashlib.new('MD4', *args, **kw)


RCON_PACKET_HEADER = six.b('\xFF' * 4)
RCON_RESPONSE_HEADER = RCON_PACKET_HEADER + six.b('n')
CHALLENGE_PACKET = RCON_PACKET_HEADER + six.b('getchallenge')
CHALLENGE_RESPONSE_HEADER = RCON_PACKET_HEADER + six.b('challenge ')


def rcon_nosecure_packet(password, command):
    return RCON_PACKET_HEADER + six.b('rcon {password} {command}'
        .format(password=password, command=command))


if six.PY2:
    def to_bytes(text):
        return str(text)

    def hmac_md4(key, msg):
        return hmac.new(key, msg, md4)
else:
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
