Details on installing dependencies and tools
============================================


CAN hardware on BeagleBone
-------------------------------------------------------
BeagleBone ("white") and BeagleBone Black has built-in CAN-controllers.
In order to use it you must add CAN transceivers, to adapt the electrical
levels to the CAN bus.

There are expansion cards ("capes") with CAN transceivers, for example the
"TT3201 CAN Cape" from Towertech. The cape also contains two additional CAN controllers.

The DCAN1 controller inside the BeagleBone processor is named CAN0 interface
in Debian, and is connected to the pins 1 (GND), 3 (CAN_L) and 4 (CAN_H) on the cape.

The Debian distribution has support for the CAN interface.

It is possible to just add the CAN transceiver chip to your BeagleBone.
Then use this pinout for DCAN1:

==================== ==================
Signal               Pin number on P9
==================== ==================
GND                  1, 2, 43-46
VDD_3V3EXP (500 mA)  3, 4
SYS_5V               7, 8
dcan1_rx             24
dcan1_tx             26
==================== ==================


Install Debian on BeagleBone, and get the CAN interface running
-----------------------------------------------------------------------
Have an empty SD-micro card ready.

Download the disk image appropriate for your version of the board from http://beagleboard.org/latest-images
For this installation Debian 8.4 was the latest version.

Follow the instructions on https://beagleboard.org/getting-started to give your SD-card a fresh installation of the Debian OS.

It seems that the Beaglebone Black will boot from the SD card default.
The documentation says that it boots from NAND by default and that you need to
press and hold button S2 when powering on to boot from SD-card.
It will stay in this boot mode until power down (so you can use the reset button without any problem).

On the download web page there is a description how to flash the image to NAND.

By default the Beaglebones IP through the USB connection is ``192.168.7.2``.

If you are running Linux or OSX ssh to the Beaglebone::

    $ ssh debian@192.168.7.2

The default password is ``temppwd``. For the root account the password is ``''`` (none).

If you are running Windows which have no ssh client included in the default OS,
use Putty (http://www.chiark.greenend.org.uk/~sgtatham/putty/download.html)
or another SSH client (http://www.openssh.com/windows.html) to connect to your Beaglebone.

You might resize the partition on your SD card. Follow this guide: http://elinux.org/Beagleboard:Expanding_File_System_Partition_On_A_microSD

Make sure the Beaglebone is connected to the Internet.

At the command prompt::

    $ sudo apt-get update
    $ sudo apt-get upgrade
    $ sudo apt-get install can-utils

The ``upgrade`` step will take more than one hour to finish.

If you need to change the host name, edit the files ``/etc/hostname`` and ``/etc/hosts``. Replace 'beaglebone' with your new hostname.

To enable the CAN interface, add the line ``cape_enable=bone_capemgr.enable_partno=BB-CAN1``
to the end of the ``/boot/uEnv.txt`` file. Add it through nano::

    $ sudo nano /boot/uEnv.txt

If you like to run your Beaglebone without a GUI, add also this line to the file:
``cmdline=systemd.unit=multi-user.target``

Possibly this could be used instead from command line::

    $ sudo systemctl set-default multi-user.target

If the GUI is running, this line will appear when running ``ps -ef``:

    /usr/sbin/lightdm

Reboot the Beaglebone and verify that the CAN interface hardware is enabled::

    $ cat /sys/devices/platform/bone_capemgr/slots

and start the CAN interface with correct speed::

    $ sudo ip link set can0 up type can bitrate 500000

List available network interfaces (including CAN)::

    $ ifconfig

If you need to disable the CAN interface::

    $ sudo ip link set can0 down


CAN hardware on Raspberry Pi
-------------------------------------------------------
In order to run CAN on a Raspberry Pi, you need a separate CAN controller chip
that handles the CAN protocol details. Also a CAN transceiver is necessary to adapt
the voltage levels to the CAN bus. There are several CAN expansion boards available for Raspberry Pi.

Typically an MCP2515 CAN controller chip is used and it is connected to
the Raspberry Pi via the SPI bus having 3.3 V voltage levels.
The MCP2515 chip uses a crystal oscillator, most often 10 MHz or 16 MHz.

Typically these pins are used to connect a CAN controller to the Raspberry Pi:

================ ================== =================== ======================
Pin number on Pi Pi pin description MCP2515 description Comments
================ ================== =================== ======================
1                +3.3 V             +3.3 V
6                GND                GND
19               SPI_MOSI           SI                  SDI
21               SPI_MISO           SO                  SDO
22               GPIO25             int                 Interrupt
23               SPI_SCLK           SCK
24               SPI_CE0            CS
(none)           (none)             reset               Use pull-up to 3.3 V
================ ================== =================== ======================


Install Raspbian on Raspberry Pi and get the CAN interface running
------------------------------------------------------------------------
Download the latest Raspbian image, and install it on an SD card
according to instructions: https://www.raspberrypi.org/downloads/raspbian/

It seems sufficient to use the "Raspbian Jessie Lite" version.

Plug in the SD-card in your Raspberry Pi, and give it some time to boot.

Find the IP address of the Raspberry Pi by using NMAP::

    $ nmap -Pn -p 22 192.168.*.*

Log in to using SSH::

    $ ssh pi@IPNUMBER

Default login credentials:

* User: ``pi``
* Password: ``raspberry``

Using the ``raspi-config`` tool, expand the filesystem and change the hostname::

    $ sudo raspi-config

Also make sure to set it to boot in console mode, in order to save CPU resources.

Update Raspbian and install CAN tools::

    $ sudo apt-get update
    $ sudo apt-get dist-upgrade
    $ sudo apt-get install can-utils

The ``upgrade`` step is very time consuming.

Edit the ``/boot/config.txt file`` using the Nano editor::

    $ sudo nano /boot/config.txt

Add these lines::

    dtparam=spi=on
    dtoverlay=mcp2515-can0,oscillator=10000000,interrupt=25

Adapt the oscillator frequency to the crystal of your MCP2515 board and the GPIO pin used for interrupt.
The most common oscillator frequencies seem to be 10 MHz and 16 MHz.

Reboot::

    $ sudo reboot

After reboot the CAN interface is enabled by::

    $ sudo ip link set can0 up type can bitrate 500000

List available network interfaces (including CAN)::

    $ ifconfig

Verify that the GUI not is running. There should be no line 'lightdm' when running ``ps -ef``.

For Raspberry Pi 3 follow all the above steps, however, in the ``/boot/config.txt file`` add the these lines::

    dtparam=spi=on
    dtoverlay=mcp2515-can0,oscillator=10000000,interrupt=25
    dtoverlay=spi-bcm2835
   
Cables on both Pis match the same pins. 

Verify CAN hardware on two boards
------------------------------------
Use two embedded Linux boards with CAN hardware and enable the CAN interface on each of them. The interface 'can0'
should be listed as 'UP' on both boards when running ifconfig on them.

Connect a twisted pair CAN wire between them and make sure there is proper CAN line termination.

On one of the boards print out received CAN frames::

    $ candump can0

On the other board generate random CAN frames and print them::

    $ cangen can0 -v

The same CAN frames should now be seen in both boards.


Install Secure Gateway and other dependencies on BeagleBone or Raspberry Pi
-------------------------------------------------------------------------------
Install the dependencies listed in the "core and tools" section in the "Dependencies" chapter.

Install sgframework and canadapter as described in the "Install" chapter.



Autostarting software using systemd
------------------------------------------------------

In order to automatically start the canadapter on booting of the BeagleBone,
use a settings file for the systemd daemon. The contents of the file should be (adjust paths accordingly)::

    [Unit]
    Description=CANadapter - CAN to MQTT adapter
    Requires=network.target

    [Service]
    ExecStart=/usr/local/bin/canadapter \
      /home/debian/sgframework/examples/configfilesForCanadapter/climateservice_cansignals.kcd \
      -mqttfile /home/debian/sgframework/examples/configfilesForCanadapter/climateservice_mqttsignals.json \
      -mqttname canadapter -i can0
    Restart=always

    [Install]
    WantedBy=multi-user.target


Put this file in this folder::

    /etc/systemd/system/

Go to the same folder and type in this command to create a symbolic link and enable autostart for your service file::

    $ sudo systemctl enable "filename".service

The service will not be started yet. To start it reboot the system or type the following command::

    $ sudo systemctl restart "filename".service


Simularly, to automatically enable CAN interface `can0`::

    [Unit]
    Description=CAN hardware startup
    After=network.target
    Requires=network.target

    [Service]
    Type=oneshot
    RemainAfterExit=true
    ExecStart=/bin/sleep 5
    ExecStart=/sbin/ip link set can0 up type can bitrate 500000
    ExecStop=/sbin/ip link set can0 down

    [Install]
    WantedBy=multi-user.target

Note that systemd files installed by operating system packages typically end
up in ``/usr/lib/systemd/system`` or ``lib/systemd/system``.
