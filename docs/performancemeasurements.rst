Canadaper performance measurements
===================================

Introduction
------------
In order to measure the performance of the canadapter, we send CAN frames
to it and measure the output of MQTT messages.

Before running the measurements, some preparation needs to be done.

* Use a separate embedded Linux machine (A) sending generated CAN messages,
  and an embedded Linux machine (B) running the canadapter.

* The CAN bus between them should be set to 500 kbit/s.

The basic theory of the test is to:

* Send CAN frames with incrementing data values using cangen from a Linux machine (A).

* Measure CPU load and memory usage on the machine (B) running the canadapter.

* Save raw incoming CAN frames to file with timestamps using shell commands on machine B.

* Save MQTT messages to file with timestamps (also using shell commands) on machine B.

The reason shell commands are used to save measurement data to file is to minimize unnecessary CPU load and to have a reliable environment to extract data from.


Hardware setup example
------------------------
One hardware setup could be:

CAN sender machine (machine A) consists of a Raspberry PI running Raspbian and including a hardware CAN interface.
The CAN interface is set to send at 500 kbit/s.
This hardware supports a maximum CAN busload of 45%

Candapter machine (B) is running the canadapter and the MQTT broker.
It consists of a Beaglebone Black running Debian and is fitted with a CAN-cape (expansion board).

Make sure that your embedded Linux machine is running at full speed. It can be viewed using this command::

    $ cpufreq-info

The result is for example::

    cpufrequtils 008: cpufreq-info (C) Dominik Brodowski 2004-2009
    Report errors and bugs to cpufreq@vger.kernel.org, please.
    analyzing CPU 0:
      driver: cpufreq-voltdm
      CPUs which run at the same hardware frequency: 0
      CPUs which need to have their frequency coordinated by software: 0
      maximum transition latency: 300 us.
      hardware limits: 275 MHz - 720 MHz
      available frequency steps: 275 MHz, 500 MHz, 600 MHz, 720 MHz
      available cpufreq governors: conservative, ondemand, userspace, powersave, performance
      current policy: frequency should be within 275 MHz and 720 MHz.
                      The governor "ondemand" may decide which speed to use
                      within this range.
      current CPU frequency is 275 MHz.
      cpufreq stats: 275 MHz:0.53%, 500 MHz:0.01%, 600 MHz:0.04%, 720 MHz:99.41%  (88)

To change the CPU frequency::

    $ sudo cpufreq-set -f 720MHz


Collecting measurement data
-----------------------------

Generating CAN frames
^^^^^^^^^^^^^^^^^^^^^^
On your CAN sender machine (A), set interface can0 to 500 kbit/s::

    $ sudo ip link set can0 type can bitrate 500000

Using cangen to send frames (observe the g  flag that is used to set the gap)::

    $ cangen can0 -g 50 -I 008 -L 8 -D i -n 1200

The frame rate is defined by the gap/sleep between messages in milliseconds.
It is given by the ``-g`` flag. Invert the number to have the number of
messages per second (f), so ``f = 1/g`` For example ``g=10ms`` gives approximately 100 messages per second.
The ``-I`` flag sets the frame ID, the ``-L`` flag sets the number of bytes in each frame
and the ``-D`` flag sets the frame to have incrementing values.

The total number of CAN frames sent is set by the ``-n`` flag. Adjust it
so that the test is running for, for example, 100 seconds, which is the nominal
duration time.

Avoid using the ``-v`` flag to print the sent frames, as it might slow down the process.


Receiving CAN frames to file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Setup interface can0 to 500 kbit/s on machine B::

    $ sudo ip link set can0 type can bitrate 500000


Save incoming CAN frames to file with timestamps (``-ta`` flag)::

    $ candump can0 -ta -l

See the following example excerpt from a candump log file::

    (1461075290.584362) can0 008#A404000000000000
    (1461075290.634635) can0 008#A504000000000000
    (1461075290.684860) can0 008#A604000000000000
    (1461075290.735140) can0 008#A704000000000000
    (1461075290.785364) can0 008#A804000000000000
    (1461075290.835666) can0 008#A904000000000000
    (1461075290.885870) can0 008#AA04000000000000
    (1461075290.936019) can0 008#AB04000000000000
    (1461075290.986196) can0 008#AC04000000000000
    (1461075291.036391) can0 008#AD04000000000000
    (1461075291.086552) can0 008#AE04000000000000


Measuring CAN bus load
^^^^^^^^^^^^^^^^^^^^^^^
To measure the CAN bus load and save the data to file use::

    $ canbusload can0@500000 -t > canbusload_data.log


See the following example excerpt from a canbusload log file::

    canbusload 2016-04-19 14:16:07 (worst case bitstuffing)
     can0@500000  1595  215325 102080  43%

    canbusload 2016-04-19 14:16:08 (worst case bitstuffing)
     can0@500000  1594  215190 102016  43%

    canbusload 2016-04-19 14:16:09 (worst case bitstuffing)
     can0@500000  1582  213570 101248  42%


Starting the broker
^^^^^^^^^^^^^^^^^^^^^^^
The broker usually runs automatically as a service in the background. However, if it's not running it can be started as a process by typing "mosquitto" in the terminal like so::

    $ mosquitto

To run stop, start or restart mosquitto as a service the following command can be used::

    $ sudo service mosquitto stop/start/restart


Run canadapter to convert CAN frames to MQTT messages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The canadapter needs to be started with parameters. These parameters are the
path to the KCD file that interprets the CAN signals, path to the the MQTT json
file that has the CAN signal names and their corresponding MQTT names.
The other parameters that are good to use (but not obligatory but highly recommended)
are the MQTT name and can interface.

Use the configuration files included in the project source.
Run this command from the project root directory::

    $ python3 scripts/canadapter.py \
    examples/configfilesForCanadapter/climateservice_cansignals.kcd \
    -mqttfile examples/configfilesForCanadapter/climateservice_mqttsignals.json \
    -mqttname climateservice -i can0

Note that there should be no space after the backslashes. If getting problems, remove the backslashes and put the command on a single long line.



Receiving MQTT messages to file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To subscribe to a mosquitto topic and save the data to a file the following command can be used::

    $ mosquitto_sub -t "data/climateservice/#" -v -R > mosquitto_sub_data.log

To subscribe to all topics and add timestamps to the data, this command can be used::

    $ mosquitto_sub -v -R -t "+/#" | while IFS= read -r line; do printf '(%s) %s\n' "$(date '+%s.%N')" "$line"; done > mosquitto_sub_data.log

Note that at high data rates, the timestamping introduces a significant delay.

See the following example excerpt from a log file to see how the result is presented::

    (1457617715.839584510) data/climateservice/enginespeed 0.0
    (1457617715.863914727) data/climateservice/vehiclespeed 0.0
    (1457617715.884274556) data/climateservice/enginespeed 0.0
    (1457617715.915510919) data/climateservice/vehiclespeed 2.56
    (1457617715.941249622) data/climateservice/enginespeed 0.0
    (1457617715.964192934) data/climateservice/vehiclespeed 5.12
    (1457617715.988655770) data/climateservice/enginespeed 0.0
    (1457617716.015374476) data/climateservice/vehiclespeed 7.68
    (1457617716.033834838) data/climateservice/enginespeed 0.0
    (1457617716.063329853) data/climateservice/vehiclespeed 10.24
    (1457617716.087545615) data/climateservice/enginespeed 0.0
    (1457617716.110456886) data/climateservice/vehiclespeed 12.8
    (1457617716.134399576) data/climateservice/enginespeed 0.0
    (1457617716.159300270) data/climateservice/vehiclespeed 15.36

It is  better to write the MQTT messages to file, and write the number of
recived messages (for each second) to another file::

    while true; do echo "(`date +%s.%N`)  `wc -l mosquitto_sub_data.log`" \
    >> mqtt_log_length.txt; sleep 1; done

See the following example excerpt from a filelength measurement file (showing number of total messages so far)::

    (1461076433.847400400)  16442 mosquitto_sub_data.log
    (1461076434.901527780)  16442 mosquitto_sub_data.log
    (1461076435.978809565)  16555 mosquitto_sub_data.log
    (1461076437.134160771)  16789 mosquitto_sub_data.log
    (1461076438.292547163)  17023 mosquitto_sub_data.log
    (1461076439.446994608)  17257 mosquitto_sub_data.log


Measuring processor load on the machine running canadapter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use the program ``top`` to monitor the CPU load and memory usage with this command::

    $ top -cb -n 3 -d 3 > top_data.log

where the ``-n`` flag is number of samples and ``-d`` is the delay between each sample.

See the following example excerpt from a top log file::

    top - 14:36:13 up 5 days, 23:16,  4 users,  load average: 1.29, 0.69, 0.35
    Tasks: 130 total,   2 running, 125 sleeping,   3 stopped,   0 zombie
    %Cpu(s):  0.6 us,  0.7 sy,  0.0 ni, 98.6 id,  0.0 wa,  0.0 hi,  0.1 si,  0.0 st
    KiB Mem:    244088 total,   237832 used,     6256 free,    11960 buffers
    KiB Swap:        0 total,        0 used,        0 free.   106688 cached Mem

      PID USER      PR  NI    VIRT    RES    SHR S %CPU %MEM     TIME+ COMMAND
    16541 debian    20   0   21404  10312   5112 R 37.0  4.2   1:29.27 python3 scripts/canadapter.py examples/configfilesForCanadapter/climateservice_cansig+
    16703 debian    20   0    2988   1604   1300 R 15.8  0.7   0:00.15 top -cb -n 3 -d 3
      521 root     -51   0       0      0      0 S 10.6  0.0   3:28.04 [irq/199-can0]
      930 debian    20   0    4400   2504   1692 S  7.9  1.0  17:08.93 mosquitto
    16525 debian    20   0    9224   3256   2592 S  5.3  1.3   0:05.71 sshd: debian@pts/3
       63 root     -51   0       0      0      0 S  2.6  0.0   3:15.87 [irq/176-4a10000]
    14924 www-data  20   0  228736   2796   1432 S  2.6  1.1   0:12.28 /usr/sbin/apache2 -k start
    16696 root      20   0       0      0      0 S  2.6  0.0   0:00.58 [kworker/0:2]
    16698 debian    20   0    3432   2436   2120 S  2.6  1.0   0:02.98 mosquitto_sub -v -t +/#
        1 root      20   0   22012   3292   2048 S  0.0  1.3   0:56.49 /sbin/init
        2 root      20   0       0      0      0 S  0.0  0.0   0:00.02 [kthreadd]
        3 root      -2   0       0      0      0 S  0.0  0.0  51:10.41 [ksoftirqd/0]
        6 root      20   0       0      0      0 S  0.0  0.0   0:04.12 [kworker/u2:0]



Run the actual measurement
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Typically you would like to run the measurements for different CAN frame rates
and number of sent frames.

Use the CAN frame ID=8, and the KCD file included in the project source.

1. On machine B start (in this order):

  * Mosquitto broker
  * canadapter
  * candump (to file)
  * mosquitto_sub (to file)

2. Start cangen with appropriate CAN framerate and number of frames on machine A.
3. Start top (to file) and canbusload (to file) on machine B.
4. Keep the logs running for an additional 10s to give the system time to work through the buffer.



Analyzing the measurement data
---------------------------------

Calculating lost messages
^^^^^^^^^^^^^^^^^^^^^^^^^^^
First, make sure that all CAN frames sent from machine A are received in machine B.
This is done by verifying that the number of CAN frames (lines) in the candump_data.log file
equals the number of frames sent by cangen.

To calculate the number of lines in a file, use::

    $ wc -l filename

Depending on the contents of the KCD file, each incoming CAN frame might be converted
into several MQTT messages::

    Expected number of MQTT messages = (candump_data.log lines)*(MQTT messages per CAN frame)

Calculate the number of lost MQTT messages::

    Number of lost MQTT messages = (expected number of MQTT messages) - (mosquitto_sub_data.log lines)

Calculate the fraction of lost MQTT messages::

    Message loss ratio = (number of lost MQTT messages) / (expected number of MQTT messages)



Calculating lag for the canadapter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We define the lag for the canadapter as the time it takes for an arriving CAN frame to be
converted to MQTT (and received as a MQTT message). Note that this included any delay
for example in the MQTT broker.

By comparing the timestamps for the first message in each of the candump_data.log
and mosquitto_sub_data.log files, we calculate the start lag.

If there are no lost messages, we also calculate the end lag by comparing the last
timestamps in the two files.

Additionaly calculate the incoming CAN frame rate by dividing the number of
CAN frames with the duration time (measured as the difference between the
first and the last time stamp).

Also calculate the MQTT duration time by comparing the first and last timestamps
in the mosquitto_sub_data.log file.

Compare the CAN and MQTT duration times to the nominal duration time.

Compare the CAN frame rate to the given cangen delay flag (-g) value.

Compare the calculated  CAN frame rate to the canbusload measurement data.


Calculating the processor load for the machine running the canadapter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
From the top_data.log file calculate the minimum and maximum processor load
and memory consumption for the relevant processes. Those include:

* candump
* Mosquitto broker
* canadapter
* canbusload
* mosquitto_sub
* top

Also extract the total processor load (minimum and maximum) from the log file.
Compare this to the sum of the relevant processes.


Plotting graphs
---------------
Use your favourite plotting tool to plot the measuring data.

Processor load
^^^^^^^^^^^^^^
Processor load is measured in ``%`` of the total capacity of the CPU.
It's plotted as a function of the incoming CAN frame rate ``(frames/sec)``.
Plot a line for each of the relevant processes.


Lag
^^^^^^^^^^^^^
Lag is measured in ``seconds`` and is plotted as a function of the incoming frame rate ``(frames/sec)``.

Lost messages
^^^^^^^^^^^^^
Lost messages are plotted as ``data loss (%)`` as function of the incoming frame rate ``(frames/sec)``.


Analyzing the resulting graphs
-------------------------------------
Study the resulting graphs to find the maximum number of CAN frames per second that could be handled.


Running measurements automatically
---------------------------------------
There are scripts that will run the measurements automatically,
for different CAN frame rates.

Before running the automated measurements make sure that:

* The broker is running
* No unwanted processes are running, for example, other instances of 'canadapter'
* Adjust the CPU frequency accordingly

In the directory ``sgframework/tests/automated_measurements`` run::

    $ python3 measurement_script.py

You will most likely need to change some of the settings in the ``measurement_settings.py`` and otherwise to have it running properly.

The measurement scripts will create a measurement directory (named by the start time) with subdirectories,
each representing a datapoint (a specific CAN frame rate).

Analyze data with this command. You should point it to the measurement directory (having the subdirectories).
It is creating a JSON file for each datapoint.
In the directory ``sgframework/tests/automated_measurements`` (also on the embedded Linux machine) run::

    $ python3 parse_canadapter_measurements.py _measurementdata/md-20160425-151125

In order to compare different measurement, put several measurement directories
(each having JSON files) in a top directory. As the measurement directory names
are used in the legend, they should have informative names.
Plot graphs (preferably on a Linux desktop machine) using this in
the directory ``sgframework/tests/automated_measurements``::

    $ python3 dataplotter.py top_directory_name

Measuring the speed of subsystems - Reception of CAN frames
--------------------------------------------------------------
In order to find any bottlenecks is the subsystems made by the canadapter,
it can be useful to measure the speed of the subsystems separately.

Run the reception of incoming CAN frames with increasing incoming CAN frame rates, until there is loss of data.
Calculate the data loss by counting lines in the resulting file.

This will give the maximum CAN frame rate that each subsystem can handle.

Send the CAN frames using 'cangen' as described above.


Reception of raw CAN frames using Python
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Run the measurement using this command::

    $ python3 speedmeasurement_rawcan_receive.py

An example of the resulting log file::

(1458653867.093)   CAN Id:    8 (Hex   8)    Data: 00 00 00 00 00 00 00 00
(1458653867.095)   CAN Id:    8 (Hex   8)    Data: 01 00 00 00 00 00 00 00
(1458653867.097)   CAN Id:    8 (Hex   8)    Data: 02 00 00 00 00 00 00 00
(1458653867.098)   CAN Id:    8 (Hex   8)    Data: 03 00 00 00 00 00 00 00
(1458653867.099)   CAN Id:    8 (Hex   8)    Data: 04 00 00 00 00 00 00 00
(1458653867.100)   CAN Id:    8 (Hex   8)    Data: 05 00 00 00 00 00 00 00
(1458653867.101)   CAN Id:    8 (Hex   8)    Data: 06 00 00 00 00 00 00 00
(1458653867.103)   CAN Id:    8 (Hex   8)    Data: 07 00 00 00 00 00 00 00
(1458653867.106)   CAN Id:    8 (Hex   8)    Data: 08 00 00 00 00 00 00 00
(1458653867.107)   CAN Id:    8 (Hex   8)    Data: 09 00 00 00 00 00 00 00


can4python, which is used by the canadapter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Run the measurement using this command::

    $ python3 can4python_receiver.py

Each line in the log file contains the extracted CAN signals from one CAN frame.
An example of the resulting log file::

(1458654459.307)  Data: dict_items([('vehiclespeed', 0.0), ('enginespeed', 0.0)])
(1458654459.308)  Data: dict_items([('vehiclespeed', 2.56), ('enginespeed', 0.0)])
(1458654459.309)  Data: dict_items([('vehiclespeed', 5.12), ('enginespeed', 0.0)])
(148654459.310)   Data: dict_items([('vehiclespeed', 7.68), ('enginespeed', 0.0)])
(1458654459.311)  Data: dict_items([('vehiclespeed', 10.24), ('enginespeed', 0.0)])
(1458654459.313)  Data: dict_items([('vehiclespeed', 12.8), ('enginespeed', 0.0)])
(1458654459.314)  Data: dict_items([('vehiclespeed', 15.36), ('enginespeed', 0.0)])
(1458654459.315)  Data: dict_items([('vehiclespeed', 17.92), ('enginespeed', 0.0)])
(1458654459.316)  Data: dict_items([('vehiclespeed', 20.48), ('enginespeed', 0.0)])
(1458654459.316)  Data: dict_items([('vehiclespeed', 23.04), ('enginespeed', 0.0)])


Measuring the speed of subsystems - Sending MQTT messages
--------------------------------------------------------------
The idea is to send a number of MQTT messages as fast as possible and
to measure data loss and reception time. Calculate the effective MQTT message rate.

Receive the MQTT messages as described in an earlier section using mosquitto_sub.

Repeat the mesurements with increasing number of MQTT messages sent, until there is data loss
in the broker or in the receiving mosquitto_sub.

This will give the maximum MQTT number of messages we can send at max speed for
each subsystem.


mosquitto_pub
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Send the MQTT messages using::

    $ time for i in `seq 1 1000`; do mosquitto_pub -t mosquitto/test -m testmessage$i; done;

This is a rather slow method, as the mosquitto_pub needs to connect a new client to
the broker for each message sent.

Create a file with a large number of payloads::

    for i in {1..1000}; do echo messagenumber$i ; done > payloads.txt

Send each line in the file as an individual MQTT message (all on same topic)::

    $ time cat payloads.txt | mosquitto_pub -t TODO/testroot/a/b/c -l -q 1


Paho, which is the Python MQTT library
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Send the MQTT messages using the command::

    $ python3 speedmeasurement_paho_send.py -n [NUMBER OF MESSAGES]


sgframework
^^^^^^^^^^^^^^^^
Send the MQTT messages using::

    $ python3 speedmeasurement_sgframework_send.py -n [NUMBER OF MESSAGES]


Using graphviz and pycallgraph to visualize line profiling
-------------------------------------------------------------
Install pycallgraph::

    $ sudo apt-get install pygraphcall

Install graphviz (dot)::

    $ sudo apt-get install graphviz

To collect data from your python file and plot it to a picture use this command::

    $ pycallgraph graphviz -f svg -o ./output_picture_name_here.svg -- your_script_here.py

SVG is used because an error occurs with bitmapping sometimes which leads to an extremely small picture
that is not readable. SVG is based on vector graphics and can be resized as you please.


Converting can4python python modules to cython modules
------------------------------------------------------------

* Make a backup of the can4python lib

Create a file called setup_c.py in the installed can4python lib (/usr/local/lib/python3.4/dist-packages/can4python) it should contain::

   $ from distutils.core import setup
    from Cython.Build import cythonize

    setup(
      ext_modules = cythonize(["*.pyx"]),
    )

Change canbus.py and caninterface_raw.py to the file extension .pyx

Run "python3 setup_c.py build_ext --inplace"


Suggested improvements
-------------------------
The sgframework and the canadapter demonstrate an architecture concept,
and is also useful for prototyping needs.

The usecase is to extract a small number of CAN signals from a CAN bus
for applications without any real-time requirements.

A production implementation should be optimized for speed, for example, by
implementing the software in the C programming language. Note, as the MQTT
publish-subscribe protocol (running on TCP/IP) is used, it is not intended
for usecases with hard real-time requirements.
