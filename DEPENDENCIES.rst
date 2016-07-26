Dependencies
============

Core dependencies for sgframework module
----------------------------------------

===================== ================================= ================================== ==============================
Dependency            Description                       License                            Debian/pip package
===================== ================================= ================================== ==============================
Python 3.3+           Python                            PSFL 
Mosquitto 1.4.1+      MQTT broker                       BSD                                D: mosquitto
Paho Python 1.0.2+    MQTT client library               EPL 1.0 and EDL 1.0                P: paho-mqtt
===================== ================================= ================================== ==============================



Dependencies for the scripts and examples
-----------------------------------------
Not all dependencies are required for all examples.

===================== ================================= =========================== ==============================
Dependency            Description                       License                     Debian/pip package
===================== ================================= =========================== ==============================
CAN interface         Should support SocketCAN          Part of Linux kernel       
vcan0                 Virtual CAN bus interface         Part of Linux kernel       
can4python 0.1+       CAN bus library                   BSD 3-clause                P: can4python
mosquitto-clients     MQTT command line tools           BSD 3-clause                D: mosquitto-clients
can-utils             CAN bus command line tools        GPL or BSD 3-clause         D: can-utils
TK                    Graphics library                  Tcl/Tk license (BSD)        D: python3-tk
===================== ================================= =========================== ==============================



Dependencies for testing 
------------------------

===================== ================================= ======================= ==============================
Dependency            Description                       License                 Debian/pip package
===================== ================================= ======================= ==============================
coverage              Test coverage measurement         Apache 2.0              P: coverage
paramiko              Remote control via SSH            LGPL                    P: paramiko
libssl                For paramiko                      Apache 1.0              D: libssl-dev
libffi                For paramiko                      MIT                     D: libffi-dev
===================== ================================= ======================= ==============================



Documentation dependencies
-------------------------- 

===================== ================================= ======================= ==============================
Dependency            Description                       License                 Debian/pip package
===================== ================================= ======================= ==============================
texlive               Latex library (for PDF creation)  "Knuth"                 D: texlive-full
Matplotlib            Plotting library                  PSFL based              D: python3-matplotlib
Sphinx 1.3+           Documentation tool                BSD 2-cl                P: sphinx
programoutput         Spinx add-on for program output   BSD 2-cl                P: sphinxcontrib-programoutput
Sphinx rtd theme      Theme for Sphinx                  MIT                     P: sphinx_rtd_theme
===================== ================================= ======================= ==============================



Installation commands for the dependencies
---------------------------------------------
Core, and tools for usage on embedded Linux machines::

    sudo apt-get install can-utils
    sudo apt-get install mosquitto
    sudo apt-get install mosquitto-clients
    sudo apt-get install python3-pip
    sudo pip3 install paho-mqtt
    sudo pip3 install can4python

Desktop examples, documentation and testing::

    sudo apt-get install python3-tk
    sudo apt-get install python3-matplotlib
    sudo apt-get install build-essential libssl-dev libffi-dev python-dev  # For Paramiko
    sudo pip3 install sphinx
    sudo pip3 install sphinxcontrib-programoutput
    sudo pip3 install sphinx_rtd_theme
    sudo pip3 install coverage
    sudo pip3 install paramiko
    
For PDF, you also need to install (3 GByte)::

    sudo apt-get install texlive-full

Temporary requirements (before publishing on github)::

    sudo apt-get install subversion
