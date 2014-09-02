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
    description=('Quake and DarkPlaces rcon client.'
        'Suppor such games like Xonotic, Nexuiz and other'),
    author='Slava Bacherikov',
    url="https://github.com/bacher09/xrcon",
    packages=["xrcon"],
    install_requires=requires,
    tests_require=tests_require,
    test_suite="nose.collector",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        ("License :: OSI Approved ::"
        "GNU Library or Lesser General Public License (LGPL)"),
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Topic :: Software Development :: Libraries",
        "Topic :: Internet",
    ],
    platforms='any',
    keywords=['rcon', 'xonotic', 'nexuiz', 'darkplaces', 'quake'],
    license="LGPL",
    version="0.1dev"
)
