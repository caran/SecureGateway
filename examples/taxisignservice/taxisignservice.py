#
# A taxi sign service example for the Secure Gateway concept architecture.
#
# Authors: Jonas Berg
#          Chuan Jin
# Copyright (c) 2015, Semcon Sweden AB
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted
# provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,  this list of conditions and
#    the following disclaimer in the documentation and/or other materials provided with the distribution.
# 3. Neither the name of the Semcon Sweden AB nor the names of its contributors may be used to endorse or
#    promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import argparse
import logging
import os.path
import sys

try:
    import tkinter
except ImportError:
    tkinter = None

assert sys.version_info >= (3, 2, 0), "Python version 3.2 or later required!"

CURRENT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
DRIVERS_DIRECTORY = os.path.join(CURRENT_DIRECTORY, 'drivers')
IMAGES_DIRECTORY = os.path.join(CURRENT_DIRECTORY, 'images')

import sgframework

sys.path.append(DRIVERS_DIRECTORY)
try:
    import taxisign_driver
except ImportError:
    taxisign_driver = None

DESCRIPTIVE_TEXT_TEMPLATE = """
A taxi sign service example for the Secure Gateway concept architecture.

This is a "Resource" according to the Secure Gateway nomenclature. It registers on
the Secure Gateway network, and accepts commands to turn on or off a
hardware taxi sign. It is intended for running on Beaglebone with appropriate
electronics connected to a GPIO output pin to contol the taxi sign. Note that
root/sudo permissions typically are required to control GPIO pins.

This resource sends out on start-up:
  resourceavailable/taxisignservice/presence True
  commandavailable/taxisignservice/state True
  datavailable/taxisignservice/state  True

This resource is listening for:
  command/taxisignservice/state True/False

This resource sends out on state change:
  data/taxisignservice/state True/False

It can also be used in two different simulation modes. This is handy when no
taxisign hardware is available (or no sudo/root permission is available). The
command line mode simulator should always be available. The graphical mode
simulator requires Tk installed on the machine. This is typically installed with:
  sudo apt-get install python3-tk

This resource can connect to the broker in a secure or insecure way. The settings
of the broker determines what is allowed. To connect in the secure way,
the directory of the certificate files must be specified.

The certificate files should be named:
  CA file:          {}
  Certificate file: {}
  Key file:         {}

"""

RESOURCENAME = "taxisignservice"
TAXISIGN_COMMANDNAME = "state"


def init_taxisignservice():
    """Initialize the taxi sign service.

    Returns ..

    """

    ## Parse command line and set output verbosity ##
    epilog = DESCRIPTIVE_TEXT_TEMPLATE.format(sgframework.Resource.CA_CERTS,
                                              sgframework.Resource.CERTFILE,
                                              sgframework.Resource.KEYFILE)
    commandlineparser = argparse.ArgumentParser(epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
    commandlineparser.add_argument('-v',
                                   action='count',
                                   default=0,
                                   help="Increase verbosity level. Can be repeated.")
    commandlineparser.add_argument('-host',
                                   default='localhost',
                                   help="Broker host name. Defaults to %(default)s.")
    commandlineparser.add_argument('-port',
                                   default=1883,
                                   help="Broker port number. Defaults to %(default)s.")
    commandlineparser.add_argument('-cert',
                                   help="Directory for certificate files. Defaults to not using certificates.")
    commandlineparser.add_argument('-mode',
                                   choices=['hardware', 'commandline', 'graphical'],
                                   default='commandline',
                                   help="Type of simulator to use. Depends on graphical display or taxi sign hardware. " +
                                        "Defaults to '%(default)s'.")
    commandline = commandlineparser.parse_args()
    if commandline.v == 1:
        loglevel = logging.INFO
    elif commandline.v >= 2:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.WARNING
    logging.basicConfig(level=loglevel)

    ## Initialize taxisign ##
    logging.info("Initializing the taxi sign in mode: {}".format(commandline.mode))
    if commandline.mode == 'hardware':
        if taxisign_driver is None:
            raise ImportError("The driver for the taxi sign hardware is not properly installed.")
        sign = taxisign_driver.Taxisign()
    elif commandline.mode == 'graphical':
        sign = GraphicalDummyTaxisign()
    else:
        sign = CommandlineDummyTaxisign()
    sign.state = False

    ## Initialize Secure Gateway resource framework ##
    resource = sgframework.Resource(RESOURCENAME, commandline.host,
                                    commandline.port, commandline.cert)
    resource.userdata = sign
    resource.on_broker_connectionstatus_info = on_broker_connectionstatus_info
    resource.register_incoming_command(TAXISIGN_COMMANDNAME,
                                       on_taxisign_state_command,
                                       defaultvalue=resource.PAYLOAD_FALSE,
                                       echo=True,
                                       send_echo_as_retained=True)
    resource.start()
    return resource


def loop_taxisignservice(resource):

    # Handle MQTT communication
    resource.loop()

    # Update GUI if any
    sign = resource.userdata
    try:
        sign.loop()
    except tkinter.TclError:
        resource.logger.warning("The graphical app window was closed")
        resource.stop()
        raise KeyboardInterrupt


###############
## Callbacks ##
###############

def on_broker_connectionstatus_info(resource, broker_connected):
    """Callback for use when the broker connection status info is available."""
    sign = resource.userdata
    sign.broker_connectionstatus = broker_connected


def on_taxisign_state_command(resource, messagetype, servicename, commandname, commandpayload):
    """Callback for use when receiving a MQTT message.

    Sets the state of the taxi sign.

    Returns the payload (str) that should be included in the command echo MQTT message.
    """
    sign = resource.userdata
    if commandpayload.strip() == resource.PAYLOAD_TRUE:
        sign.state = True
        logging.info("Turning on taxi sign.")
        returnvalue = resource.PAYLOAD_TRUE
    else:
        sign.state = False
        logging.info("Turning off taxi sign.")
        returnvalue = resource.PAYLOAD_FALSE
    return returnvalue


######################
## Main application ##
######################

def main():
    resource = init_taxisignservice()

    ## Main loop ##
    while True:
        try:
            loop_taxisignservice(resource)
        except KeyboardInterrupt:
            sys.exit()


######################################################################
## Dummy taxi signs for use when no taxi sign hardware is available ##
######################################################################

class CommandlineDummyTaxisign:
    """Taxi sign simulator for command line.

    Prints out whether the taxi sign is on or off.

    Attributes:
     * state (bool): Set to True to turn on the taxi sign.

    """
    def __init__(self):
        self._broker_connectionstatus = False
        self._state = False
        self.redraw()

    @property
    def broker_connectionstatus(self):
        return self._broker_connectionstatus

    @broker_connectionstatus.setter
    def broker_connectionstatus(self, value):
        self._broker_connectionstatus = bool(value)
        self.redraw()

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = bool(value)
        self.redraw()

    def loop(self):
        # Graphical taxi sign simulators must update the GUI frequently. Not required here.
        pass

    def close(self):
        # Close graphical taxi sign. Not required here.
        pass

    def redraw(self):
        broker_status = "Online" if self.broker_connectionstatus else "Offline"
        taxisign_status = "On" if self.state else "Off"

        sys.stdout.write("\rTaxi signal simulator. Broker connection: {:7s}     Taxi sign: {:3s}     ".format(
            broker_status, taxisign_status))
        sys.stdout.flush()


class GraphicalDummyTaxisign(CommandlineDummyTaxisign):
    """Graphical taxi sign simulator.

    Shows a dark or bright taxi sign image in the GUI.

    Attributes:
     * state (bool): Set to True to turn on the taxi sign.

    """
    # It is possible that you need to use tkinter.Toplevel() instead of tkinter.Tk()
    # Tkinter seems to crash at strange intervals

    DISPLAY_TITLE = "Taxi sign simulator"
    FILENAME_TAXISIGN_ON = os.path.join(IMAGES_DIRECTORY, "taxi_sign_on_small.gif")
    FILENAME_TAXISIGN_OFF = os.path.join(IMAGES_DIRECTORY, "taxi_sign_off_small.gif")
    BROKERTEXT_TEMPLATE = "Broker: {:<7s}"

    def __init__(self):
        if tkinter is None:
            raise ImportError("TK or tkinter is not installed")

        self._rootframe = None
        self._rootframe = tkinter.Tk()
        self._rootframe.title(self.DISPLAY_TITLE)

        try:
            self._imageON = tkinter.PhotoImage(file=self.FILENAME_TAXISIGN_ON, name="taxisign_on")
            self._imageOFF = tkinter.PhotoImage(file=self.FILENAME_TAXISIGN_OFF, name="taxisign_off")
        except:
            raise ValueError("Could not load pictures for graphical taxi sign simulator.")
        self._imagebox = tkinter.Label(self._rootframe, image=self._imageOFF)
        self._imagebox.pack()

        self._label_brokerstatus = tkinter.Label(self._rootframe, text="")
        self._label_brokerstatus.pack()

        super().__init__()
        self.loop()

    def loop(self):
        """Update the GUI"""
        self._rootframe.update_idletasks()
        self._rootframe.update()

    def close(self):
        """Close the GUI"""
        self._rootframe.destroy()

    def redraw(self):
        image = self._imageON if self._state else self._imageOFF
        brokerstatus_text = "Online" if self.broker_connectionstatus else "Offline"
        brokerstatus_color = "black" if self.broker_connectionstatus else "red"

        self._label_brokerstatus.config(text=self.BROKERTEXT_TEMPLATE.format(brokerstatus_text),
                                        foreground=brokerstatus_color)
        self._imagebox.config(image=image)


if __name__ == "__main__":
    main()
