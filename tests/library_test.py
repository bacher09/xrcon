from .base import TestCase, mock, unittest
from xrcon import utils
from xrcon import client
import six
import socket


b = six.b
STATUS_PACKET = b(
    '\xff\xff\xff\xffstatusResponse\n\\gamename\\Xonotic\\modname'
    '\\data\\gameversion\\700\\sv_maxclients\\14\\clients\\12\\'
    'bots\\0\\mapname\\lostspace2\\hostname\\Xonotic 0.7.0 CTF Server'
    '\\protocol\\3\\qcstatus\\ctf:0.7.0:P315:S2:F6:MMinstaGib::score!'
    '!:caps!!:5:9:14:8\\d0_blind_id\\1 HSALTRUJf4ShAOk+oZDUOtijIquc73'
    'hCoO9tai62qRE=@Xon//KssdlzGkFKdnnN4sgg8H+koTbBn5JTi37BAW1Q=\n'
    '57 72 "^x555[^x0BF\xe5\x8a\x9b^x777] ^xBBBIn^1t^7eger"\n319 116'
    ' "^x777Akd^7"\n-666 41 "me"\n14 53 "^xF00\xc3\x89^7"\n'
    '130 66 "icetea"\n98 33 "^x0c0*^x333r^x222e^x111i^7"\n'
    '56 49 "^x940S^x720Weed^x530^7"\n'
)


PARSED_SERVER_VARS = {
    b('bots'): b('0'),
    b('clients'): b('12'),
    b('d0_blind_id'): b('1 HSALTRUJf4ShAOk+oZDUOtijIquc73hCoO9tai'
                        '62qRE=@Xon//KssdlzGkFKdnnN4sgg8H+koTbBn5'
                        'JTi37BAW1Q='),
    b('gamename'): b('Xonotic'),
    b('gameversion'): b('700'),
    b('hostname'): b('Xonotic 0.7.0 CTF Server'),
    b('mapname'): b('lostspace2'),
    b('modname'): b('data'),
    b('protocol'): b('3'),
    b('qcstatus'): b('ctf:0.7.0:P315:S2:F6:MMinstaGib::score!!'
                     ':caps!!:5:9:14:8'),
    b('sv_maxclients'): b('14')
}


class UtilsTest(TestCase):

    def test_rcon_nosecure_packet(self):
        self.assertEqual(
            utils.rcon_nosecure_packet('passw', 'status'),
            six.b('\xFF\xFF\xFF\xFFrcon passw status')
        )

    @mock.patch('time.time')
    def test_rcon_secure_time_packet(self, time_mock):
        time_mock.return_value = 100.0
        self.assertEqual(
            utils.rcon_secure_time_packet('passw', 'status'),
            six.b('\xff\xff\xff\xffsrcon HMAC-MD4 TIME '
                  'R\xcbv\xf0\xa7p\xcd\xca\xf2!\xc3~\x06'
                  '\xa9\x9f\xa8 100.000000 status')
        )

    @unittest.skipUnless(six.PY3, "works only in python 3")
    @mock.patch('time.time')
    def test_rcon_secure_time_packet_bytes(self, time_mock):
        time_mock.return_value = 100.0
        self.assertEqual(
            utils.rcon_secure_time_packet(b'passw', b'status'),
            six.b('\xff\xff\xff\xffsrcon HMAC-MD4 TIME '
                  'R\xcbv\xf0\xa7p\xcd\xca\xf2!\xc3~\x06'
                  '\xa9\x9f\xa8 100.000000 status')
        )

    def test_rcon_secure_challenge_packet(self):
        self.assertEqual(
            utils.rcon_secure_challenge_packet('passw', six.b('11111111111'),
                                               'status'),
            six.b('\xff\xff\xff\xffsrcon HMAC-MD4 CHALLENGE '
                  'D\x89\xfd\x15\xccZ\xea\xeb\x0e\xbfl\xd6C'
                  '\x05T\x12 11111111111 status')
        )

    def test_parse_challenge_response(self):
        challenge_resp = six.b(
            '\xff\xff\xff\xffchallenge 11111111111\x00vlen.'
            '\x00\x00\x00d0pkXon//KssdlzGkFKdnnN4sgg8H+koTb'
            'Bn5JTi37BAW1t=\x00\x00'
        )
        self.assertEqual(
            utils.parse_challenge_response(challenge_resp),
            six.b('11111111111')
        )

    def test_parse_rcon_response(self):
        self.assertEqual(
            utils.parse_rcon_response(six.b('\xFF\xFF\xFF\xFFnTest')),
            six.b('Test')
        )

    def test_parse_server_addr(self):
        self.assertEqual(
            utils.parse_server_addr('hostname', default_port=1234),
            ('hostname', 1234)
        )

        self.assertEqual(
            utils.parse_server_addr('[::1]', default_port=6060),
            ('::1', 6060)
        )

        with self.assertRaises(ValueError):
            utils.parse_server_addr('[::1]:00')

    def test_parse_server_vars(self):
        s_vars = utils.parse_server_vars(
            b('\\gamename\\somegame\\modname\\somemod\\gameversion\\100')
        )

        self.assertEqual(
            s_vars,
            {b('gamename'): b('somegame'), b('modname'): b('somemod'),
             b('gameversion'): b('100')}
        )

        with self.assertRaises(ValueError):
            utils.parse_server_vars(six.b("bad data"))

    def test_parse_player(self):
        player = utils.Player.parse_player(six.b('4 5 "Player"'))
        self.assertEqual(player.frags, 4)
        self.assertEqual(player.ping, 5)
        self.assertEqual(player.name, six.b('Player'))

        player2 = utils.Player.parse_player(six.b('-666 5 "Player"'))
        self.assertEqual(player2.frags, -666)
        self.assertEqual(player2.ping, 5)

        with self.assertRaises(ValueError):
            # bad data
            utils.Player.parse_player(six.b('666 5 "Player'))

    def test_parse_status_response(self):

        server_vars, players = utils.parse_status_packet(STATUS_PACKET)
        self.assertEqual(server_vars, PARSED_SERVER_VARS)
        self.assertEqual(len(players), 7)
        self.assertEqual(players[2].name, six.b('me'))
        # test repr not raises errors
        players_r = repr(players)
        self.assertIsNotNone(players_r)

        with self.assertRaises(ValueError):
            utils.parse_status_packet(b('BAD DATA' * 40))

    def test_parse_servers_response(self):
        good_packet = six.b(
            '\xff\xff\xff\xffgetserversResponse'
            '\\\x82\x957\x16e\xbd'
            '\\\xc8+\xc0|e\x92'
            '\\zcv\x05e\x91'
            '\\EOT\x00\x00\x00'
        )
        self.assertCountEqual(utils.parse_servers_response(good_packet), [
            ('130.149.55.22', 26045),
            ('200.43.192.124', 26002),
            ('122.99.118.5', 26001)
        ])

        bad_packet1 = six.b(
            '\xff\xff\xff\xffgetserversResponse'
            '\\zcv\x05e\x91'
        )

        with self.assertRaises(ValueError):
            list(utils.parse_servers_response(bad_packet1))

        bad_packet2 = six.b(
            '\xff\xff\xff\xffgetserversResponse'
            'tzcv\x05e\x91'
            '\\EOT\x00\x00\x00'
        )

        with self.assertRaises(ValueError):
            list(utils.parse_servers_response(bad_packet2))


class QuakeProtocolTest(TestCase):

    def test_client_create_by_server_str(self):
        qc = client.QuakeProtocol.create_by_server_str('127.0.0.1:26006')
        self.assertEqual(qc.host, '127.0.0.1')
        self.assertEqual(qc.port, 26006)

    @mock.patch('socket.socket', spec=socket.socket)
    def test_client_connect(self, socket_mock):
        qc = client.QuakeProtocol('127.0.0.1', 26000, timeout=1)
        qc.connect()
        socket_mock.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
        socket_mock.return_value \
            .connect.assert_called_once_with(('127.0.0.1', 26000))

        socket_mock.return_value.settimeout.assert_called_once_with(1)
        qc.close()
        self.assertTrue(socket_mock.return_value.close.called)

        with self.assertRaises(client.NotConnected):
            qc.close()

    @unittest.skipUnless(socket.has_ipv6, "IPv6 is not supported")
    @mock.patch('socket.socket', spec=socket.socket)
    def test_client_connect_ipv6(self, socket_mock):
        qc = client.QuakeProtocol('::1', 26000)
        qc.connect()
        socket_mock.assert_called_once_with(socket.AF_INET6, socket.SOCK_DGRAM)
        qc.close()
        self.assertTrue(socket_mock.return_value.close.called)

    @mock.patch('socket.socket', spec=socket.socket)
    def test_client_getchallenge(self, socket_mock):
        socket_mock.return_value.recv.side_effect = [
            six.b('\xFF\xFF\xFF\xFFBAD PACKET'),
            six.b('\xff\xff\xff\xffchallenge 11111111111\x00vle ')
        ]
        qc = client.QuakeProtocol('127.0.0.1', 26000)
        qc.connect()
        challenge = qc.getchallenge()
        self.assertEqual(challenge, six.b('11111111111'))
        qc.close()

    @mock.patch('time.time')
    @mock.patch('socket.socket', spec=socket.socket)
    def test_client_getchallenge_timeout(self, socket_mock, time_mock):
        time_mock.return_value = 100.0

        def recv(num):
            time_mock.return_value += 20
            return six.b('\xFF\xFF\xFF\xFFBAD PACKET')

        socket_mock.return_value.recv.side_effect = recv
        qc = client.QuakeProtocol('127.0.0.1', 26000)
        qc.connect()
        with self.assertRaises(socket.timeout):
            qc.getchallenge()

    @mock.patch('time.time')
    @mock.patch('socket.socket', spec=socket.socket)
    def test_ping(self, socket_mock, time_mock):
        time_mock.side_effect = [100.0, 100.02]
        qc = client.QuakeProtocol('127.0.0.1', 26000)
        qc.read_iterator = mock.MagicMock()
        qc.read_iterator.return_value = iter([utils.PONG_Q2_PACKET])
        qc.connect()
        self.assertAlmostEqual(qc.ping2(), 0.02)
        socket_mock.return_value \
            .send.assert_called_once_with(utils.PING_Q2_PACKET)

        socket_mock.reset_mock()
        qc.read_iterator.reset_mock()
        qc.read_iterator.side_effect = socket.timeout
        time_mock.side_effect = [100.0]
        self.assertIsNone(qc.ping2())

        socket_mock.reset_mock()
        qc.read_iterator.side_effect = None
        time_mock.side_effect = [100.0, 100.03]
        qc.read_iterator.return_value = iter([utils.PONG_Q3_PACKET])
        self.assertAlmostEqual(qc.ping3(), 0.03)
        socket_mock.return_value \
            .send.assert_called_once_with(utils.PING_Q3_PACKET)
        qc.close()

    @mock.patch('socket.socket', spec=socket.socket)
    def test_getstatus(self, socket_mock):
        qc = client.QuakeProtocol('127.0.0.1', 26000)
        qc.read_iterator = mock.MagicMock()
        qc.read_iterator.return_value = iter([STATUS_PACKET])
        qc.connect()
        server_vars, players = qc.getstatus()
        self.assertEqual(server_vars, PARSED_SERVER_VARS)
        self.assertEqual(len(players), 7)
        self.assertEqual(players[2].name, six.b('me'))
        socket_mock.return_value.send \
            .assert_called_once_with(utils.QUAKE_STATUS_PACKET)

        qc.read_iterator.return_value = iter([])
        self.assertIsNone(qc.getstatus())
        qc.close()


class ClientTest(TestCase):

    def test_validate_secure_rcon(self):
        with self.assertRaises(ValueError):
            client.XRcon('localhost', 26000, 'passw', 4)

        with self.assertRaises(ValueError):
            client.XRcon('localhost', 26000, 'passw', -1)

        rcon = client.XRcon('localhost', 26000, 'passw', 0)

        with self.assertRaises(ValueError):
            rcon.secure_rcon = -1

        self.assertEqual(rcon.secure_rcon, 0)

    def test_client_create_by_server_str(self):
        rcon = client.XRcon.create_by_server_str('127.0.0.1:26006', "test")
        self.assertEqual(rcon.host, '127.0.0.1')
        self.assertEqual(rcon.port, 26006)
        self.assertEqual(rcon.password, "test")

    @mock.patch('time.time')
    @mock.patch('socket.socket', spec=socket.socket)
    def test_client_send(self, socket_mock, time_mock):
        time_mock.return_value = 100.0

        def socket_send_args():
            return socket_mock.return_value.send.call_args[0][0]

        rcon = client.XRcon('127.0.0.1', 26000, 'passw', 0)
        challenge = six.b('11111111111')
        rcon.getchallenge = lambda: challenge
        rcon.connect()
        rcon.send('status')
        self.assertEqual(
            socket_send_args(),
            six.b('\xFF\xFF\xFF\xFFrcon passw status')
        )

        rcon.secure_rcon = 1
        rcon.send('status')
        self.assertEqual(
            socket_send_args(),
            utils.rcon_secure_time_packet("passw", "status")
        )

        rcon.secure_rcon = 2
        rcon.send('status')
        self.assertEqual(
            socket_send_args(),
            utils.rcon_secure_challenge_packet("passw", challenge, "status")
        )

        rcon._secure_rcon = -1
        with self.assertRaises(ValueError):
            rcon.send('status')
        rcon.close()

    @mock.patch('socket.socket', spec=socket.socket)
    def test_client_read_once(self, socket_mock):
        socket_mock.return_value.recv.return_value = \
            six.b('\xFF\xFF\xFF\xFFnTest')

        rcon = client.XRcon('127.0.0.1', 26000, 'passw')
        rcon.connect()
        self.assertEqual(rcon.read_once(), six.b('Test'))
        rcon.close()

    @mock.patch('socket.socket', spec=socket.socket)
    def test_client_execute(self, socket_mock):
        socket_mock.return_value.recv.side_effect = [
            six.b('\xFF\xFF\xFF\xFFn1'),
            six.b('\xFF\xFF\xFF\xFFn2'),
            six.b('\xFF\xFF\xFF\xFFn3'),
            socket.timeout
        ]

        rcon = client.XRcon('127.0.0.1', 26000, 'passw')
        rcon.connect()
        data = rcon.execute('status')
        self.assertEqual(data, six.b('123'))
        rcon.close()
