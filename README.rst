xrcon
=====

.. image:: https://travis-ci.org/bacher09/xrcon.svg?branch=master
    :target: https://travis-ci.org/bacher09/xrcon

.. image:: https://coveralls.io/repos/bacher09/xrcon/badge.png?branch=master
    :target: https://coveralls.io/r/bacher09/xrcon?branch=master 


Darkplaces and Quakes rcon [#rcon]_ protocol and client implementation.
Works with such games like Xonotic_, `Nexuiz`__, Warsow_ and other games with
Quakes rcon.

__ Nexuiz_wiki_

Features
--------

  * Support old Quake rcon and new Darkplaces secure rcon protocols.
  * Support both IPv4 and IPv6 connections.
  * Bundled console client.
  * Well tested, test coverage near 100%.
  * Works with python 2.6+, 3.2+.

Installation
------------

  * execute ``pip install xrcon``
  * or run ``pip install -e git+https://github.com/bacher09/xrcon#egg=xrcon``
    to install development version from github

Usage
-----

Using as library::

  from xrcon.client import XRcon
  rcon = XRcon('server', 26000, 'password')
  rcon.connect() # create socket
  try:
      data = rcon.execute('status') # on python3 data would be bytes type
  finally:
      rcon.close()

For more info read ``XRcon`` docstrings.

Using console client::

  $ xrcon -s yourserver:26001 -p password command

If you want use IPv6 address it should be put inside square brackets.
For example::

  $ xrcon -s [1080:0:0:0:8:800:200C:417A]:26002 -p password status
  $ xrcon -s [1080:0:0:0:8:800:200C:417B] -p password status

If port is omitted then by default would be used port 26000.
You may also change type of rcon, by default would be used secure time based
rcon protocol. This protocol works only in Darkplaces based games.
For instance::

  $ xrcon -s warsowserver:44400 -p password -t 0 status

0 means old (unsecure) quakes rcon, 1 means secure time base rcon, and 2 is 
secure challenge based rcon protocol.

You may also create ini configuration file in your home directory
``.xrcon.ini``. 
For example::

  [DEFAULT]
  server = someserver:26000
  password = secret
  type = 1
  timeout = 0.9

  [other]
  server = someserver:26001

  [another]
  server = otherserver
  password = otherpassword
  type = 0
  timeout = 1.2

Then if you wants execute command on this servers just do::

  $ xrcon status # for DEFAULT server
  $ xrcon -n other status # for other server
  $ xrcon -n another status # for another server


License
-------
LGPL

.. [#rcon] remote console, for more info read `this`__.
__ Warsow_rcon_


.. _Xonotic: http://www.xonotic.org/
.. _Nexuiz_wiki: https://en.wikipedia.org/wiki/Nexuiz
.. _Warsow: http://www.warsow.net/
.. _Warsow_rcon: http://www.warsow.net/wiki/RCON
