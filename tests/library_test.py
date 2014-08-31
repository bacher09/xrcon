from .base import TestCase, mock
from xrcon import utils
import six


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
