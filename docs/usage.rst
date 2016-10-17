Usage introduction for the 'sgframework' package
======================================================
With the sgframework you can implement the 'apps' and 'resources' described in
the previous section. Below are some minimal examples to get you started. 

Minimal 'resource' example
----------------------------
This is an example of a 'resource' implemented using the Secure Gateway framework.
It is a taxi sign listening to commands on the MQTT
topic ``command/taxisignservice/state``. When the received payload is ``True``
the text "Turning on my taxi sign." is printed.

.. literalinclude:: ../examples/minimal/minimaltaxisign.py
   :caption:
   :linenos:

This example resource is using threaded networking, meaning that the
MQTT communication is done in a separate thread.

It is also possible to run the resource in a single thread, but then
you need to call ``resource.loop()`` regularly.


Minimal 'app' example
--------------------------
This example 'app' controls the taxi sign by sending MQTT commands on
the appropriate topic. It also listens to the echo from the taxi sign,
and shows the current taxi sign state.

.. literalinclude:: ../examples/minimal/minimaltaxiapp.py
   :caption:
   :linenos:

This app is an example implementation not using threaded networking.
Apps can also use threaded networking, as described in the API documentation
(see another section).


Usage recommendations
---------------------
It is recommended to use the threaded networking. However when using for
example the TK graphics library, it is not possible to run it in another thread.
Instead you need to call the ``loop()`` method regularly.


Developing your own Resources
--------------------------------------
If you are to develop your own resource for the Secure Gateway network,
you could use the available resource framework (which runs under Python3). 

The main API object is the ``Resource``, and you should use these public methods to get your resource up and running:

 * ``register_incoming_command()``
 * ``register_outgoing_data()``
 * ``start()``
 * ``send_data()``

and:

 * ``stop()``
 * ``loop()`` (if not using the threaded networking interface)

Have a look on the source code for the taxisign service (in the distributed examples)
to have inspiration for the usage of the Secure Gateway resource framework.

Of course, Secure Gateway resources can be implemented in any programming
language having a proper MQTT library with TLS support.


Developing your own Apps
-------------------------------

Similarly, there is Secure Gateway app framework, for usage when implementing custom Python3 apps.

The main API object is the ``App``, and use these public methods to get it running:

 * ``register_incoming_availability()``
 * ``register_incoming_data()``
 * ``start()``
 * ``send_command()``

and:

 * ``stop()``
 * ``loop()`` (if not using the threaded networking interface)

The taxisign app source code should be used for inspiration.


