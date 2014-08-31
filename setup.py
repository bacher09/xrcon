from setuptools import setup
import sys


requires = [
    'six',
]


tests_require = [
    'nose>=1.0',
    'coverage',
]


def lt27():
    v = sys.version_info
    return (v[0], v[1]) < (2, 7)


def lt33():
    v = sys.version_info
    return (v[0], v[1]) < (3, 3)


if lt33():
    tests_require.append('mock')


if lt27():
    tests_require.append('unittest2')


setup(
    name='xrcon',
    description='Xonotic rcon client',
    author='Slava Bacherikov',
    packages=["xrcon"],
    install_requires=requires,
    tests_require=tests_require,
    test_suite="nose.collector",
    keywords=['rcon', 'xonotic', 'darkplaces', 'quake'],
    license="GPL",
)
