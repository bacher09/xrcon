xrcon
=====

.. image:: https://travis-ci.org/bacher09/xrcon.svg?branch=master
    :target: https://travis-ci.org/bacher09/xrcon

.. image:: https://ci.appveyor.com/api/projects/status/d0xmpvmpb8c9skb0?svg=true&branch=master
    :target: https://ci.appveyor.com/project/bacher09/xrcon

.. image:: https://coveralls.io/repos/bacher09/xrcon/badge.svg?branch=master
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
  * Works with python 2.7, 3.3+.

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

Also, there is another one CLI utility — ``xping``. It can be used to measure
rtt_ for server or client. It also supports other games too, so you can measure
ping for Warsow, Quake 3, Urban Terror and some other games.
Here's an example::

  $ xping -c 4 pub.regulars.win
  XPING pub.regulars.win (89.163.144.234) port: 26000
  89.163.144.234 port=26000 time=39.36 ms
  89.163.144.234 port=26000 time=39.63 ms
  89.163.144.234 port=26000 time=39.83 ms
  89.163.144.234 port=26000 time=39.87 ms

  --- pub.regulars.win ping statistics ---
  4 packets transmitted, 4 received, 0.0% packet loss
  rtt min/avg/max/mdev = 39.357/39.672/39.870/0.204 ms

Also, you can ping clients too, this might be helpful for server admins for
checking client networking. First, you need to determine client host and
port. You can do this via `rcon status` command. Let's suppose that status
command returned ``172.16.254.2:33045`` address, then xping command will be
look like this: ``xping -p 33045 172.16.254.2``. Note, that this might not work
for some clients because of firewalls and NATs.

Here's few other examples::

  $ xping -p 26005 mars.regulars.win  # stop it with Ctrl-C
  $ xping -p 44400 -t qfusion 212.83.185.75  # ping warsow server
  $ xping -p 27960 -t q3 144.76.158.173  # ping urban terror server

For more info about CLI options check ``xping --help``.

In some cases results of xping might be inaccurate. For example, if you
experience packet duplication or reordering. All currently supported
gaming protocols have no way to identify concrete response for probe.
Because of this, there is no way to determine if application received original
or duplicated response. It can affect result even more, if duplicated packet
will arrive some time later, so application can process it as response for
new probe.  In some cases application might detect packet duplication.

License
-------
LGPL

.. [#rcon] remote console, for more info read `this`__.
__ Warsow_rcon_


.. _Xonotic: http://www.xonotic.org/
.. _Nexuiz_wiki: https://en.wikipedia.org/wiki/Nexuiz
.. _Warsow: http://www.warsow.net/
.. _Warsow_rcon: http://www.warsow.net/wiki/RCON
.. _rtt: https://en.wikipedia.org/wiki/Round-trip_delay_time
