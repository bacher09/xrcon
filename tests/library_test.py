from .base import TestCase, mock, unittest
from xrcon import utils
from xrcon import client
import six
import socket


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

    @mock.patch('socket.socket', spec=socket.socket)
    def test_client_connect(self, socket_mock):
        rcon = client.XRcon('127.0.0.1', 26000, 'passw', timeout=1)
        rcon.connect()
        socket_mock.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
        socket_mock.return_value \
            .connect.assert_called_once_with(('127.0.0.1', 26000))

        socket_mock.return_value.settimeout.assert_called_once_with(1)
        rcon.close()
        self.assertTrue(socket_mock.return_value.close.called)

        with self.assertRaises(client.NotConnected):
            rcon.close()

    @unittest.skipUnless(socket.has_ipv6, "IPv6 is not supported")
    @mock.patch('socket.socket', spec=socket.socket)
    def test_client_connect_ipv6(self, socket_mock):
        rcon = client.XRcon('::1', 26000, 'passw')
        rcon.connect()
        socket_mock.assert_called_once_with(socket.AF_INET6, socket.SOCK_DGRAM)
        rcon.close()
        self.assertTrue(socket_mock.return_value.close.called)

    @mock.patch('socket.socket', spec=socket.socket)
    def test_client_getchallenge(self, socket_mock):
        socket_mock.return_value.recv.side_effect = [
            six.b('\xFF\xFF\xFF\xFFBAD PACKET'),
            six.b('\xff\xff\xff\xffchallenge 11111111111\x00vle ')
        ]
        rcon = client.XRcon('127.0.0.1', 26000, 'passw')
        rcon.connect()
        challenge = rcon.getchallenge()
        self.assertEqual(challenge, six.b('11111111111'))
        rcon.close()

    @mock.patch('time.time')
    @mock.patch('socket.socket', spec=socket.socket)
    def test_client_getchallenge_timeout(self, socket_mock, time_mock):
        time_mock.return_value = 100.0

        def recv(num):
            time_mock.return_value += 20
            return six.b('\xFF\xFF\xFF\xFFBAD PACKET')

        socket_mock.return_value.recv.side_effect = recv
        rcon = client.XRcon('127.0.0.1', 26000, 'passw')
        rcon.connect()
        with self.assertRaises(socket.timeout):
            rcon.getchallenge()

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
