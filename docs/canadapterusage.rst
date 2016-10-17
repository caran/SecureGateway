Canadaper usage
========================

The canadaper is a script distributed as part of the sgframework. It converts
CAN signals to MQTT messages and MQTT messages to CAN signals.
All MQTT communication is handled by the MQTT broker which controls the access.
Most often only a specific subset of all available vehicle CAN signals is
implemented in the canadapter. Typically the 'DeployAirbag' CAN signal is
excluded from the implementation in the canadapter.

The configuration of the canadapter consists of providing it with information
about the signals on the CAN bus, and a configuration file telling which of
those that should be possible to send/receive over MQTT.
The Canadapter uses the KCD fileformat for configuring the CAN signals.
This file-format is an open-source alternative to the Vector DBC files.
An DBC-to-KCD conversion tool is available online: CAN-Babel

The usecase for this prototype implementation is to extract a few signals
from a CAN bus and possibly send a few CAN signals. Due to the use of the
MQTT protocol (over TCP/IP) it will not fulfill any hard realtime requirements.


Configuration files for canadapter
-------------------------------------
There are two configuration files for the canadapter. One describes the
frames and signals on the CAN bus, and is in the KCD file format.
The other type of configuration file defines the names each of the CAN signals should have
when sent as MQTT messages and is in JSON file format.


KCD file
^^^^^^^^^
The KCD file format is described here: https://github.com/julietkilo/kcd

Canadapter is using the KCD file format via the can4python library, which is
found here: https://github.com/caran/can4python

Example of a KCD configuration file:

.. literalinclude:: ../examples/configfilesForCanadapter/climateservice_cansignals.kcd
   :caption:
   :lines: 32-
   :language: xml

Edit the KCD file to only contain the CAN frames and signals you are interested in,
otherwise CPU capacity is used to parse CAN frames of data not is used.


JSON file
^^^^^^^^^
The JSON file defines the names of each of the CAN signals should be sent as MQTT messages.
It also represents which of the CAN frames should be sent on MQTT
and which MQTT messages should be allowed to be forwarded to the CAN bus.

Note however which messages are actually allowed to be sent to the CAN bus (they are also controlled by the
CAN configuration file (KCD)) and which of the nodes on the bus are enacted by the canadapter (ego node id). The KCD file
could hold information about all nodes and signals in the system.

For example, consider a KCD file defining that node 1 sends CAN frame id 6 and 7, and node 2 sends CAN frame 8 and 9.
If the canadapter enacts node 2 (ego node id, set by a command line argument),
then it is allowed to send CAN frame 8 and 9 according to the KCD file. The JSON file further defines that this instance
of the canadapter only is allowed to send CAN frame 9.

It is possible to adjust the configuration so several CAN signals to be sent in a single MQTT message.
Here is an example of such an MQTT wire message:

.. code-block:: json

   {"values":
      {
         "ADAS_Seg_MsgType": 1.0,
         "ADAS_Seg_Offset": 2.0,
         "ADAS_Seg_CycCnt": 3.0,
         "ADAS_Seg_EffSpdLmt": 4.0,
         "ADAS_Seg_EffSpdLmtType": 5.0
      }
   }

If an MQTT message contains one CAN signal (extracted from a CAN frame), this is named a "signal" in the JSON configuration file.

If an MQTT message contains information about several CAN signals (all extracted from the same CAN frame)then it is
named an "aggregate" in the JSON configuration file.

The top structure of the JSON configuration file is like this:

.. code-block:: json

   {"entities":
       {
           "signals": [],
           "aggregates": []
       }
   }

Each "signal" object (in the list of signals) should have a structure like this:

.. code-block:: json

   {"canName": "indoortemperature",
    "canMultiplier": 1.0,
    "mqttName": "actualindoortemperature",
    "mqttType": "float",
    "mqttEcho": false,
    "toCan": false,
    "fromCan": true
   }

Only the "canName" field of a signal is mandatory. The "mqttName" defaults to be the same as the "canName". The "mqttType"
is float by default, but could also be "int".
The field "mqttEcho" sets whether an incoming MQTT command should be echoed back as data on MQTT, and defaults to false.
By default a signal is allowed to be converted from CAN (to MQTT), but not to CAN (from MQTT).
The multiplier is used when converting a CAN signal to an MQTT signal. In the other direction is 1/multiplier used. Defaults to 1.0.

Example of a JSON configuration file containing only "signals":

.. literalinclude:: ../examples/configfilesForCanadapter/climateservice_mqttsignals.json
   :caption:
   :linenos:
   :language: json

Each "aggregate" object (in the list of aggregates) should have a structure like this:

.. code-block:: json

   {"mqttName": "ADAS_Seg",
    "toCan": true,
    "fromCan": false,
    "signals": [
         {"canName": "ADAS_Seg_MsgType", "mqttType": "int"},
         {"canName": "ADAS_Seg_Offset"},
         {"canName": "ADAS_Seg_CycCnt", "mqttType": "int"},
         {"canName": "ADAS_Seg_EffSpdLmt"},
         {"canName": "ADAS_Seg_EffSpdLmtType"}
      ]
   }

For aggregates, only the MQTTname key is mandatory. The "signals" part of an aggregate are the same as defined above
for an individual signal. Only the top level "toCan" and "fromCan" fields of an aggregate are used
(not the fields inside the signals, if set). Defaults to allow conversion from CAN (but not to CAN).

Example of a JSON configuration file containing "signals" and "aggregates":

.. literalinclude:: ../examples/configfilesForCanadapter/ADASIS_mqttsignals.json
   :caption:
   :linenos:
   :language: json



Resulting MQTT messages
-----------------------

This is a part of the interpretation of the climateservice_cansignals.kcd file::


    CAN frame definition. ID=8 (0x008, standard) 'vehiclesimulationdata', DLC=8, cycletime None ms, producers: [], no throttling, contains 2 signals
        Signal details:
        ---------------
    
    
        Signal 'vehiclespeed' Startbit 8, bits 16 (min DLC 2) big endian, unsigned, scalingfactor 0.01, unit: 
             valoffset 0.0 (range 0 to 7e+02) min None, max None, default 0.0.
    
             Startbit normal bit numbering, least significant bit: 8
             Startbit normal bit numbering, most significant bit: 7
             Startbit backward bit numbering, least significant bit: 48
    
                      111111   22221111 33222222 33333333 44444444 55555544 66665555
             76543210 54321098 32109876 10987654 98765432 76543210 54321098 32109876
             Byte0    Byte1    Byte2    Byte3    Byte4    Byte5    Byte6    Byte7
             MXXXXXXX XXXXXXXL                                                      
             66665555 55555544 44444444 33333333 33222222 22221111 111111
             32109876 54321098 76543210 98765432 10987654 32109876 54321098 76543210
    
    
        Signal 'enginespeed' Startbit 26, bits 14 (min DLC 4) big endian, unsigned, scalingfactor 1, unit: 
             valoffset 0.0 (range 0 to 2e+04) min None, max None, default 0.0.
    
             Startbit normal bit numbering, least significant bit: 26
             Startbit normal bit numbering, most significant bit: 23
             Startbit backward bit numbering, least significant bit: 34
    
                      111111   22221111 33222222 33333333 44444444 55555544 66665555
             76543210 54321098 32109876 10987654 98765432 76543210 54321098 32109876
             Byte0    Byte1    Byte2    Byte3    Byte4    Byte5    Byte6    Byte7
                               MXXXXXXX XXXXXL                                      
             66665555 55555544 44444444 33333333 33222222 22221111 111111
             32109876 54321098 76543210 98765432 10987654 32109876 54321098 76543210


Run the Canadaper::

    $ python3 scripts/canadapter.py examples/configfilesForCanadapter/climateservice_cansignals.kcd \
    -mqttfile examples/configfilesForCanadapter/climateservice_mqttsignals.json -mqttname climateservice -i vcan0


Send a CAN frame with ID=8::

    $ cansend vcan0 008#00FF00FF00000000

Study the traffic on the CAN bus::

    $ candump vcan0

Resulting output::

    vcan0  008   [8]  00 FF 00 FF 00 00 00 00

Study the resulting MQTT messages using this command::

    $ mosquitto_sub -v -t +/#

Resulting MQTT messages::

    data/climateservice/vehiclespeed 2.5500000000000003
    data/climateservice/enginespeed 63.0





CAN adapter helptext
----------------------

.. command-output:: python3 scripts/canadapter.py -h
   :cwd: ..
