import argparse
import getpass
import os.path
from .client import XRcon


try:
    from configparser import NoOptionError, ConfigParser
except ImportError:
    from ConfigParser import NoOptionError, SafeConfigParser as ConfigParser


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
        cargs = self.rcon_args(config, namespace, namespace.name)
        rcon = XRcon.create_by_server_str(cargs['server'], cargs['password'],
                                          cargs['type'], cargs['timeout'])
        try:
            rcon.connect()
            print(rcon.execute(namespace.command, cargs['timeout']))
        finally:
            rcon.close()

    @staticmethod
    def build_parser():
        parser = argparse.ArgumentParser(description='Executes rcon command')
        parser.add_argument('--config', type=argparse.FileType('r'))
        parser.add_argument('--timeout', type=float)
        parser.add_argument('-n', '--name')
        parser.add_argument('-s', '--server')
        parser.add_argument('-p', '--password')
        parser.add_argument('-t', '--type', type=int, choices=XRcon.RCON_TYPES)
        parser.add_argument('command')
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

        cval = getattr(namespace, 'timeout')
        dct['timeout'] = cval if cval else config.getfloat(name, 'timeout')

        return dct


def xrcon(args=None):
    XRconProgram().run(args)
