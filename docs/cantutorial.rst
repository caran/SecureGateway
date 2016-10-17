CAN communication tutorial, using simulated CAN bus
====================================================

It is possible to create a virtual (simulated) CAN bus on Linux systems.
This can be used to simulate the activity of a real CAN bus, and for testing CAN software.
Install a virtual CAN bus as described elsewhere in this documentation, and name it vcan0 (look at DEPENDENCIES.rst file for installation commands).

Linux CAN command-line tools
-----------------------------

In order to test the CAN communication, we are using the can-utils command line CAN tools.
These are used similarly on real and simulated CAN buses.
For example, one of the tools is ``candump`` which allows you to print all data that is being received by a CAN interface.

In order to test this facility, start it in a terminal window::
 
    $ candump vcan0
 

From another terminal window, send a CAN frame with identifier 0x1A (26 dec) and 8 bytes of data::
 
    $ cansend vcan0 01a#11223344AABBCCDD
 

This will appear in the first terminal window (running candump)::
 
    vcan0  01A   [8]  11 22 33 44 AA BB CC DD
 
  
To send large amount of random CAN data, use the cangen tool::
 
    $ cangen vcan0 -v
 

In order to record this type of received CAN data to file (including timestamp), use::
 
    $ candump -l vcan0
 
The resulting file will be named like: candump-2015-03-20_123001.log 

In order to print logfiles in a user friendly format::
 
    $ log2asc -I candump-2015-03-20_123001.log vcan0
 

Recorded CAN log files can also be re-played back to the same or another CAN interface::
 
    $ canplayer -I candump-2015-03-20_123001.log 
 

If you need to use another can interface than defined in the logfile, use the
expression ``CANinterfaceToUse=CANinterfaceInFile``. This example also prints the frames::
 
    $ canplayer vcan0=can1 -v -I candump-2015-03-20_123001.log 
 

The cansniffer command line application is showing the latest CAN messages. Start it with::
 
    $ cansniffer vcan0
 
It shows one CAN-ID (and its data) per line, sorted by CAN-ID, and shows the cycle
time per CAN-ID. The time-out until deleting a CAN-ID row is 5 seconds by default.

There is an example CAN log file distributed with the Secure Gateway.
Download it, replay it, and study the result using cansniffer.

Also the Wireshark program can be used to analyse CAN frames. 

There is a description on how to analyze CAN using Wireshark: https://libbits.wordpress.com/2012/05/07/capturing-and-analyzing-can-frames-with-wireshark/
Make sure to enable the CAN interface before starting the program.


Setting up CAN communication between two embedded Linux boards
---------------------------------------------------------------
In order to test real CAN communication, you need two embedded Linux machines,
for example Raspberry Pi and Beaglebone. Both should be equipped with
CAN interface boards, set to a speed of 500 kbit/s. The installation of
software and hardware is described elsewhere in this documentation.

Test the communication using command line tools. Send a CAN frame from one of the machines::

    $ cansend can0 01a#01020304

This will be repeatedly sent on the CAN bus until there is an acknowledgement from at least one other node.

For the CAN controller to be able to send a message, a CAN transceiver must be connected (as it senses the CAN bus voltage). Otherwise it will stop immediately after the first try.

To cancel this sending, you need to disable and re-enable the can0::

    $ sudo ip link set can0 down
    $ sudo ip link set can0 up

On the other machine receive the CAN frames using::

    $ candump can0 
