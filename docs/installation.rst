============
Installation
============

At the command line::

    $ pip3 install sgframework

This will also install the dependencies ``paho-mqtt`` and ``can4python``.
In order to actually use it, you need to install an MQTT broker, etc.
See the "Dependencies" chapter.


Run the canadapter::

    $ canadapter -h


To download the example files and test files, you need to use::
 
    $ git clone https://github.com/caran/sgframework.git

In order to run tests, you might need to enable the virtual CAN bus. On Debian::

    $ sudo make vcan

Run tests::

    $ make test

If running on a desktop machine, it is possible to test also the graphical apps etc (more dependencies required)::

    $ make test-all
