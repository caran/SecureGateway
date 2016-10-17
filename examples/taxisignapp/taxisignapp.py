#
# A taxi sign app example for the Secure Gateway concept architecture.
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
import sys

try:
    import tkinter
except ImportError:
    tkinter = None

assert sys.version_info >= (3, 2, 0), "Python version 3.2 or later required!"

import sgframework

DESCRIPTIVE_TEXT_TEMPLATE = """
A taxi sign app example for the Secure Gateway concept architecture.

This is an "App" according to the Secure Gateway nomenclature. It registers on
the Secure Gateway network, and sends commands to turn on or off a hardware
taxi sign (or a simulated sign).

The corresponding taxisign resource must be online. This app listens for:
  resourceavailable/taxisignservice/presence True

This app is sending:
  command/taxisignservice/state True

This app is receiving:
  data/taxisignservice/state True

It can be used in two different modes. The command line mode should always
be available. The graphical mode requires Tk installed on the machine.
This is typically installed with:
  sudo apt-get install python3-tk

This app can connect to the broker in a secure or insecure way. The settings
of the broker determines what is allowed. To connect in the secure way,
the directory of the certificate files must be specified.

The certificate files should be named:
  CA file:          {}
  Certificate file: {}
  Key file:         {}

"""

APPNAME = "taxiapp"
TAXISIGN_SERVICE_NAME = "taxisignservice"
TAXISIGN_STATE_SIGNAL = "state"

TIMEOUT = 0.1  # seconds


def init_taxisignapp():

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
                                   choices=['commandline', 'graphical'],
                                   default='commandline',
                                   help="Type of use interface. Depends on graphical display. " +
                                        "Defaults to '%(default)s'.")
    commandline = commandlineparser.parse_args()
    if commandline.v == 1:
        loglevel = logging.INFO
    elif commandline.v >= 2:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.WARNING
    logging.basicConfig(level=loglevel)

    ## Initialize Secure Gateway app framework ##
    app = sgframework.App(APPNAME, commandline.host, commandline.port, commandline.cert)
    app.timeout = TIMEOUT

    if commandline.mode == 'graphical':
        displ = GraphicalAppDisplay(app)
    else:
        displ = CommandlineAppDisplay(app)
    displ.loop()
    app.userdata = displ
    app.register_incoming_availability(app.PREFIX_RESOURCEAVAILABLE, TAXISIGN_SERVICE_NAME, "", on_resource_presence)
    app.register_incoming_data(TAXISIGN_SERVICE_NAME, TAXISIGN_STATE_SIGNAL, on_taxisign_state_data)
    app.on_broker_connectionstatus_info = on_broker_connectionstatus_info
    app.start()

    return app


def loop_taxisignapp(app):

    # Handle MQTT communication
    app.loop()

    # Update GUI if any
    displ = app.userdata
    try:
        displ.loop()
    except tkinter.TclError:
        app.logger.warning("The graphical app window was closed")
        app.stop()
        raise KeyboardInterrupt


###############
## Callbacks ##
###############

def on_broker_connectionstatus_info(app, broker_connected):
    """Callback for use when the broker connection status info is available."""
    displ = app.userdata
    displ.broker_connectionstatus = broker_connected


def on_resource_presence(app, messagetype, servicename, signalname, payload):
    """Callback for use when receiving a MQTT message.

    Sets the presence information for the taxi sign.

    """
    displ = app.userdata
    if payload == app.PAYLOAD_TRUE:
        presence = True
    else:
        presence = False
    displ.resource_online = presence
    logging.info("Taxi sign online: {}".format(presence))


def on_taxisign_state_data(app, messagetype, servicename, signalname, payload):
    """Callback for use when receiving a MQTT message.

    Sets the state of the taxi sign.

    """
    displ = app.userdata
    if payload.strip() == app.PAYLOAD_TRUE:
        state = True
    else:
        state = False
    displ.taxisign_state = state


######################
## Main application ##
######################

def main():
    app = init_taxisignapp()

    ## Main loop ##
    while True:
        try:
            loop_taxisignapp(app)
        except KeyboardInterrupt:
            sys.exit()


##########################
## Displays for the app ##
##########################

STATE_UNKNOWN = -1


class CommandlineAppDisplay:

    TAXISIGN_STATUSTEXT_TEMPLATE = "Taxi sign status: {:<8}"

    def __init__(self, app):
        self.app = app
        self._broker_connectionstatus = False
        self._resource_online = False
        self._taxisign_state = STATE_UNKNOWN

    @property
    def broker_connectionstatus(self):
        return self._broker_connectionstatus

    @broker_connectionstatus.setter
    def broker_connectionstatus(self, value):
        self._broker_connectionstatus = bool(value)
        if not value:
            self._resource_online = False
        self.redraw()

    @property
    def resource_online(self):
        return self._resource_online

    @resource_online.setter
    def resource_online(self, value):
        self._resource_online = bool(value)
        self.redraw()

    @property
    def taxisign_state(self):
        return self._taxisign_state

    @taxisign_state.setter
    def taxisign_state(self, value):
        self._taxisign_state = bool(value)
        self.redraw()

    def loop(self):
        self.redraw()
        answer = input("    Input 'on', 'off' or enter to redraw: ")
        if not answer:
            return
        if not self.resource_online:
            return
        if answer == 'on':
            logging.info("Turning on taxi sign")
            self.app.send_command(TAXISIGN_SERVICE_NAME, TAXISIGN_STATE_SIGNAL, self.app.PAYLOAD_TRUE)
        elif answer == 'off':
            logging.info("Turning off taxi sign")
            self.app.send_command(TAXISIGN_SERVICE_NAME, TAXISIGN_STATE_SIGNAL, self.app.PAYLOAD_FALSE)

    def redraw(self):
        if not self.broker_connectionstatus:
            status_text = "Not connected to broker"
        elif not self.resource_online:
            status_text = "Taxisign offline"
        elif self.taxisign_state == STATE_UNKNOWN:
            status_text = "Taxisign ?"
        elif self.taxisign_state:
            status_text = "Taxisign on"
        else:
            status_text = "Taxisign off"
        sys.stdout.write("\r" + self.TAXISIGN_STATUSTEXT_TEMPLATE.format(status_text))
        sys.stdout.flush()

    def close(self):
        pass


class GraphicalAppDisplay(CommandlineAppDisplay):

    DISPLAY_TITLE = "Taxi app"

    def __init__(self, app):
        if tkinter is None:
            raise ImportError("TK or tkinter is not installed")
        self._rootframe = tkinter.Tk()
        self._rootframe.title(self.DISPLAY_TITLE)

        self._label_status = tkinter.Label(self._rootframe, text="")
        self._label_status.pack()

        self._button_on = tkinter.Button(self._rootframe, text='Turn ON', state=tkinter.DISABLED, width=25)
        self._button_on.pack()
        self._button_on.bind('<Button-1>', self._button_on_handler)

        self._button_off = tkinter.Button(self._rootframe, text='Turn OFF', state=tkinter.DISABLED, width=25)
        self._button_off.pack()
        self._button_off.bind('<Button-1>', self._button_off_handler)

        super().__init__(app)
        self.loop()

    def _button_on_handler(self, event):
        if self.resource_online:
            logging.info("Turning on taxi sign")
            self.app.send_command(TAXISIGN_SERVICE_NAME, TAXISIGN_STATE_SIGNAL, self.app.PAYLOAD_TRUE)

    def _button_off_handler(self, event):
        if self.resource_online:
            logging.info("Turning off taxi sign")
            self.app.send_command(TAXISIGN_SERVICE_NAME, TAXISIGN_STATE_SIGNAL, self.app.PAYLOAD_FALSE)

    def close(self):
        """Close the GUI"""
        self._rootframe.destroy()

    def loop(self):
        """Update the GUI"""
        self._rootframe.update_idletasks()
        self._rootframe.update()

    def redraw(self):
        if not self.broker_connectionstatus:
            status_text = "Not connected to broker"
            status_color = 'black'
            button_state = tkinter.DISABLED
        elif not self.resource_online:
            status_text = "Taxisign: offline"
            status_color = 'black'
            button_state = tkinter.DISABLED
        elif self.taxisign_state == STATE_UNKNOWN:
            status_text = "Taxisign: Unknown state"
            status_color = 'black'
            button_state = tkinter.NORMAL
        elif self.taxisign_state:
            status_text = "Taxisign: on"
            status_color = 'green4'
            button_state = tkinter.NORMAL
        else:
            status_text = "Taxisign: off"
            status_color = 'red'
            button_state = tkinter.NORMAL
        self._label_status.config(text=status_text, foreground=status_color)
        self._button_on.config(state=button_state)
        self._button_off.config(state=button_state)


if __name__ == '__main__':
    main()
