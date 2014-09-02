from .base import TestCase, unittest
from xrcon import client
import os
import socket


@unittest.skipUnless(os.environ.get('XONOTIC_TEST'),
                     'set XONOTIC_TEST env var for testing with real xonotic')
class XonoticRconTest(TestCase):
    """You should start xonotic on localhost computer on 26000 port
    with rcon password test and disabled secure rcon
    You may use such command:
        $ echo -e 'rcon_password "test"\nrcon_secure 0' | \
        > xonotic-dedicated -sessionid test
    """

    def test_rcon_ipv4(self):
        self.rcon = client.XRcon('127.0.0.1', 26000, "test", 0)
        self.execute()

    @unittest.skipUnless(socket.has_ipv6, "IPv6 is not supported")
    def test_rcon_ipv6(self):
        self.rcon = client.XRcon('::1', 26000, "test", 0)
        self.execute()

    def execute(self):
        self.addCleanup(self.close_rcon)
        self.rcon.connect()

        self.rcon.send('status')
        self.assertTrue(self.rcon.read_once().startswith('host'))

        self.rcon.secure_rcon = 1
        self.rcon.send('status')
        self.assertTrue(self.rcon.read_once().startswith('host'))

        self.rcon.secure_rcon = 2
        self.rcon.send('status')
        self.assertTrue(self.rcon.read_once().startswith('host'))

        data = self.rcon.execute('cvarlist sv_vote*', 0.5)
        self.assertTrue(data.startswith('sv_vote'))

    def close_rcon(self):
        self.rcon.close()
