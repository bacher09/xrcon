import argparse


class BaseProgram(object):

    description = None

    def __init__(self):
        self.parser = self.build_parser()

    def run(self, args=None):  # pragma: no cover
        raise NotImplementedError

    @classmethod
    def build_parser(cls):
        parser = argparse.ArgumentParser(description=cls.description)
        return parser

    @classmethod
    def start(cls, args=None):
        cls().run(args)
