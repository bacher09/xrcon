from setuptools import setup
import os.path
import sys
import re


requires = [
    'six',
]


tests_require = [
    'nose>=1.0',
    'coverage',
]


if sys.version_info[0] == 2:
    tests_require.append('mock')


ROOT_PATH = os.path.dirname(__file__)
with open(os.path.join(ROOT_PATH, "README.rst")) as f:
    long_description = f.read()


with open(os.path.join(ROOT_PATH, 'xrcon', '__init__.py')) as f:
    VERSION = re.match(r".*__version__\s*=\s*'(.*?)'", f.read(), re.S).group(1)


setup(
    name='xrcon',
    description=('Quake and DarkPlaces rcon client.'
                 'Suppor such games like Xonotic, Nexuiz and other'),
    long_description=long_description,
    author='Slava Bacherikov',
    author_email='slava@bacher09.org',
    url="https://github.com/bacher09/xrcon",
    packages=["xrcon", "xrcon.commands"],
    install_requires=requires,
    tests_require=tests_require,
    test_suite="nose.collector",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        ("License :: OSI Approved ::"
         " GNU Library or Lesser General Public License (LGPL)"),
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Libraries",
        "Topic :: Internet",
        "Topic :: Games/Entertainment",
        "Topic :: Games/Entertainment :: First Person Shooters"
    ],
    entry_points="""\
    [console_scripts]
    xrcon = xrcon.commands.xrcon:XRconProgram.start
    xping = xrcon.commands.xping:XPingProgram.start
    """,
    platforms='any',
    keywords=['rcon', 'xonotic', 'nexuiz', 'darkplaces', 'quake'],
    license="LGPL",
    version=VERSION
)
