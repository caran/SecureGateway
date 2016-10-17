Background
==========

Secure Gateway (SG) is an architecture concept, using Internet technology in
automotive and industrial environments. As a concept, it is not intended for inclusion
in products and is not production ready. It is our hope that it can give inspiration
for architectures of future embedded systems. The Secure Gateway concept is the result
of the automotive research project PLINTA, but has since found its use also in
industrial environments. It is further developed in the "Second Road - Open Innovation Lab"
project.

Vehicles have several buses for vehicle data, often of the types Controller Area Network (CAN)
or Flexray. These vehicle buses contain safety-critical data, and must be protected from malicious impact.

Vehicles also have infotainment electronics, for example the Infotainment Head Unit (IHU)
and Rear Seat Entertainment (RSE). Also smart-phone apps for direct communication
with the vehicles can be considered part of the infotainment system, as the user for
example would like to transfer destination information from her smartphone to
the vehicle navigation system. Thus there is a need for a separate infotainment network,
separated from the safety-critical vehicle network. Nevertheless, there must be some
connection between the two networks, as the IHU should control for example the climate settings.




Architecture and MQTT background
----------------------------------
Secure Gateway utilizes the MQTT (Message Queue Telemetry Transport) protocol
for communication via a broker (a MQTT server), which handles access control.
Authentication and encryption is handled by Transport Layer Security (TSL).
The MQTT clients don't have any open ports to the IP network, and they connect to
the broker.

In the Secure Gateway we have defined resources and apps. For example the in-car
climate node can be represented by an SG resource, while an application in the
IHU sending climate control signals corresponds to an SG app.
Note that both resources and apps send and receive MQTT messages. 

The MQTT protocol uses a publish-subscribe pattern. A MQTT broker (server)
acts as the central communication point. Clients register the message types
(MQTT topics) they are interested in (to the broker). A client publishes a message
to the broker, which re-transmits the message to the clients that previously
have subscribed to the topic. The publishers does not know the identity
(or existence) of the subscribers.

Details on the MQTT protocol are found on:

     http://mqtt.org/
     http://en.wikipedia.org/wiki/MQTT   

The Secure Gateway concept was presented at the conference "ESCAR USA"
(embedded security in cars) 2015. The full paper "Secure Gateway – A concept
for an in-vehicle IP network bridging the infotainment and the safety critical domains"
is available for download through the ESCAR website (registration required).


Tutorial overview
-------------------
This documentation contains tutorials, mainly written for running on a Ubuntu
desktop Linux machine. They are also suitable for running on embedded Linux boards,
for example the Beaglebone and the Raspberry Pi. This is especially relevant when
it comes to sending and receiving CAN messages, as there are CAN expansion
boards available for those platforms.


This tutorial will show you how to:

 * Install the necessary components.
 * Test MQTT communication from command line tools.
 * Use the Secure Gateway topic hierarchy.
 * Use a simulated resource (a taxi sign) and an app to control it.
 * Build your own Secure Gateway enabled taxi sign hardware.
 * Work with client-side and server-side certificates and encryption.
 * Send and receive CAN messages on a simulated CAN bus.
 * Run a real CAN-bus between a CAN vehicle simulator and the Secure Gateway, implemented on two embedded Linux boards (Raspberry Pi or Beaglebone).
 * Develop your own resources and apps for the Secure Gateway.


MQTT tutorial
---------------     

In order to be able to try this, you need to install the Mosquitto broker
and the Mosquitto command line tools. See another section of this documentation for installation details.

The Secure Gateway concept builds on using the MQTT protocol over an IP network. 

Each MQTT message has a payload and a topic, which both are strings.
The MQTT topics are arranged in a hierarchy, for example ``A/B/C/D``.

These wildcard are used: ``*`` to listen to everything in a message hierarchy and 
``+`` to allow anything on that particular message hierarchy level.

For example the actual in-car temperature reading might be published on this topic::
 
    data/climateservice/actualindoortemperature 

To listen to all data from the climateservice, use this topic::
 
    data/climateservice/*

Similarly, to listen to all data from any node, use this topic::
 
    data/*

To listen to everything related to the climateservice, use::
 
    +/climateservice/*
 
Mosquitto does not require a config file, if all default settings are accepted.
Then certificates are not used. For some Linux distributions the Mosquitto broker
is started automatically after installation. See below for how to then start and stop it.

In general, start the Mosquitto broker by running::
 
    $ mosquitto 
 
To subscribe to all topics (and print out the topic for each message), use this tool::
 
    $ mosquitto_sub -t +/#  -v
 
It connects to ``localhost`` on port 1883, by default.

Open one terminal window, and run the command above.

To send one message on the ``data/climateservice/actualindoortemperature`` topic, use something like this::

    $ mosquitto_pub -t data/climateservice/actualindoortemperature -m 27.4

Run this command in a second terminal window, and look at the message appearing in the first terminal window.

It is possible to send messages as "retained", which means that the broker is sending the last known value to any new subscriber.

Try out this retained message::
 
    $ mosquitto_pub -t data/climateservice/actualindoortemperature -m 27.4 -r
 
Then open a new terminal window, and subscribe to all topics using the command above. Note that the retained message will appear!

To "delete" a retained message from the broker, send a message with a NULL payload::
 
    mosquitto_pub -t data/climateserviceactualindoortemperature -n -r
 

The "Quality of Service" (QOS) setting is defining how hard the broker is trying
to ensure that messages have been delivered. It ranges from "fire and forget" to a four-step handshake.

Also a "last will" can be defined for each client. That is a message sent out
by the broker, if the client connection is unexpectedly lost. 

     
MQTT topic structure for Secure Gateway
----------------------------------------
In order to handle ``presence`` information, a number of additional topic structures are defined.
With presence information it is possible to have a plug-and-play behavior of new resources and apps.

Secure Gateway uses a topic hierarchy with three levels::

    messagetype/servicename/signalname payload


The message types are basically:

* ``data`` Data sent from a resource (to an app or to another resource)
* ``command`` Command sent to a resource (from an app or from another resource)

In addition there are ``messagetypes`` for indication of ``presence`` of the above functionality:

* ``dataavailable`` Indicates that certain data is available.
* ``commandavailable`` Indicates that a certain command is available.

So if a sensor publishes data on the topic::

    data/sensor1/temperature 29.3

then the sensor is expected to send this message at startup::

    dataavailable/sensor1/temperature True


Applications connecting later are receiving the dataavailable message, as it
was published as "retained". This instructs the broker to send the last known
value to new clients on connection.

(There is also the resourceavailable messagetype, as discussed in a subsequent section).

The signalnames should be unique among commands and data. The command is typically
echoed back as data. There should not be some data topic having the same signalname as a command.

Note that resources and apps are both subscribers and publishers of messages.


Abbreviations
--------------

* ACL - Access Control List
* CA - Certificate Authority
* CN - Common Name. For certificates.
* CAN - Controller Area Network
* CSR - Certification Signature Request. A file format for sending requests to the certificate authority (CA).
* DBC - Database for CAN. A file format for CAN configuration, owned by Vector Informatik GmbH.
* DLC - Data Length Code. Part of a CAN message.
* DNS - Domain Name System
* IP - Internet Protocol
* KCD - Kayak CAN Definition. A file format used by the open-source Kayak application for displaying CAN data.
* MQTT - Message Queue Telemetry Transport
* PEM - Text file format for keys and certificates
* PKI - Public Key Infrastructure
* SSL - Secure Sockets Layer
* TLS - Transport Layer Security
