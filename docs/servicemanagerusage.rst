Service Manager broker add-on
=============================

Each client can register a last will, that is sent by the broker if the client
connection is unexpectedly lost. We use it to indicate the presence of
resources (not apps). For example, the last will could be::

    dataavailable/sensor1/temperature False

Unfortunately it is possible only to send one message per client, why some trick is required to handle more than one signal per client (resource). Therefore the resource instead register::

    resourceavailable/sensor1/presence False

as the last will, and sends this message at startup (along with the ``dataavailable`` message)::

    resourceavailable/sensor1/presence True

A separare component, the Service Manager, is keeping track of the connected services.
It will send the individual ``datavailable/x/y False`` when resource x disconnects.

Start up the Service Manager::

    $ python3 scripts/servicemanager.py 

Test it from command line by using one subscribe window and one publish window. Subscribe in one terminal::

    $ mosquitto_sub -t +/#  -v

In the other window::
    
    $ mosquitto_pub -t resourceavailable/foo/presence -m True
    $ mosquitto_pub -t dataavailable/foo/bar -m True
    $ mosquitto_pub -t commandavailable/foo/baz -m True

    $ mosquitto_pub -t resourceavailable/foo/presence -m False

The Service Manager will then automatically send these messages::

    dataavailable/foo/bar False
    commandavailable/foo/baz False


Service Manager helptext
---------------------------

.. command-output:: python3 scripts/servicemanager.py -h
   :cwd: ..
