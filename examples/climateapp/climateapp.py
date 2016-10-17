#
# Vehicle app example for the Secure Gateway concept architecture.
#
# Authors: Jonas Berg
#          Chuan Jin
# Copyright (c) 2015, Semcon Sweden AB
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted
# provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
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

if sys.version_info < (3, 2, 0):
    raise EnvironmentError("Python version 3.2 or later required!")

MODULES_DIRECTORY = os.path.abspath('../../modules')
sys.path.append(MODULES_DIRECTORY)
import sgframework

DESCRIPTIVE_TEXT_TEMPLATE = """
A vehicle app example for the Secure Gateway concept architecture.

This is an "App" according to the Secure Gateway nomenclature. It registers on
the Secure Gateway network, and receives vehicle data. It can also send commands
to the CAN-adapter to turn on the air condition.

It can be used in two different modes. The command line mode should always be
available. The graphical mode requires Tk installed on the machine.
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

APPNAME = "climateapp"
CLIMATERESOURCE_NAME = "climateservice"

MQTT_SIGNALNAME_AIRCONDITION = "aircondition"
MQTT_SIGNALNAME_VEHICLESPEED = "vehiclespeed"
MQTT_SIGNALNAME_ENGINESPEED = "enginespeed"
MQTT_SIGNALNAME_INDOORTEMPERATURE = "actualindoortemperature"

CAN_PAYLOAD_TRUE = 1
CAN_PAYLOAD_FALSE = 0

TIMEOUT = 0.1  # seconds


def init_climateapp():

    ## Parse command line and set output verbosity ##
    epilog = DESCRIPTIVE_TEXT_TEMPLATE.format(sgframework.Resource.CA_CERTS,
                                              sgframework.Resource.CERTFILE,
                                              sgframework.Resource.KEYFILE)
    commandlineparser = argparse.ArgumentParser(epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
    commandlineparser.add_argument('-v', action='count', default=0, help="Increase verbosity level. Can be repeated.")
    commandlineparser.add_argument('-host', default='localhost', help="Broker host name. Defaults to %(default)s.")
    commandlineparser.add_argument('-port', default=1883, help="Broker port number. Defaults to %(default)s.")
    commandlineparser.add_argument('-cert', help="Directory for certificate files. Defaults to not using certificates.")
    commandlineparser.add_argument('-mode', choices=['commandline', 'graphical'], default='commandline',
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
    app.register_incoming_availability(app.PREFIX_RESOURCEAVAILABLE, CLIMATERESOURCE_NAME, "", on_resource_presence)

    for mqtt_signalname in [MQTT_SIGNALNAME_AIRCONDITION, MQTT_SIGNALNAME_VEHICLESPEED,
                            MQTT_SIGNALNAME_ENGINESPEED, MQTT_SIGNALNAME_INDOORTEMPERATURE]:
        app.register_incoming_data(CLIMATERESOURCE_NAME, mqtt_signalname, on_incoming_data)
    app.on_broker_connectionstatus_info = on_broker_connectionstatus_info

    ## Select display mode ##
    if commandline.mode == 'graphical':
        displ = GraphicalAppDisplay(app)
    else:
        displ = CommandlineAppDisplay(app)
    app.userdata = displ

    app.start()
    return app


def loop_climateapp(app):

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

    Sets the presence information (on the display) about the resource in use.

    """
    displ = app.userdata
    if payload == app.PAYLOAD_TRUE:
        presence = True
    else:
        presence = False
    displ.resource_online = presence
    logging.info("Resource online: {}".format(presence))


def on_incoming_data(app, messagetype, servicename, signalname, payload):
    """Callback for use when receiving a MQTT message.

    Sets display fields.

    """
    displ = app.userdata
    if not displ.resource_online:
        app.logger.warning("Received signal from an offline resource. Servicename: {}, signalname: {}, payload: {}".format(
                            servicename, signalname, payload))
        return

    if signalname == MQTT_SIGNALNAME_VEHICLESPEED:
        displ.vehiclespeed = float(payload)
    elif signalname == MQTT_SIGNALNAME_ENGINESPEED:
        displ.enginespeed = float(payload)
    elif signalname == MQTT_SIGNALNAME_INDOORTEMPERATURE:
        displ.indoortemperature = float(payload)
    elif signalname == MQTT_SIGNALNAME_AIRCONDITION:
        displ.aircondition_state = bool(int(payload))


######################
## Main application ##
######################

def main():
    app = init_climateapp()

    ## Main loop ##
    while True:
        try:
            loop_climateapp(app)
        except KeyboardInterrupt:
            sys.exit()


##########################
## Displays for the app ##
##########################

STATE_UNKNOWN = -1


class CommandlineAppDisplay:

    def __init__(self, app):
        self.app = app
        self._broker_connectionstatus = False
        self._resource_online = False
        self._initialize_values()

    def _initialize_values(self):
        self._aircondition_state = STATE_UNKNOWN
        self._enginespeed = 0.0
        self._vehiclespeed = 0.0
        self._indoortemperature = 0.0

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
    def aircondition_state(self):
        return self._aircondition_state

    @aircondition_state.setter
    def aircondition_state(self, value):
        self._aircondition_state = bool(value)
        self.redraw()

    @property
    def vehiclespeed(self):
        return self._vehiclespeed

    @vehiclespeed.setter
    def vehiclespeed(self, value):
        self._vehiclespeed = float(value)
        self.redraw()

    @property
    def enginespeed(self):
        return self._enginespeed

    @enginespeed.setter
    def enginespeed(self, value):
        self._enginespeed = float(value)
        self.redraw()

    @property
    def indoortemperature(self):
        return self._indoortemperature

    @indoortemperature.setter
    def indoortemperature(self, value):
        self._indoortemperature = float(value)
        self.redraw()

    def loop(self):
        self.redraw()
        answer = input("       AC input: 'on'/'off' or Enter to redraw: ")
        if not answer:
            return
        if not self.resource_online:
            return
        if answer == 'on':
            logging.info("Turning on air condition")
            self.app.send_command(CLIMATERESOURCE_NAME, MQTT_SIGNALNAME_AIRCONDITION, CAN_PAYLOAD_TRUE)
        elif answer == 'off':
            logging.info("Turning off air condition")
            self.app.send_command(CLIMATERESOURCE_NAME, MQTT_SIGNALNAME_AIRCONDITION, CAN_PAYLOAD_FALSE)

    def redraw(self):
        if not self.broker_connectionstatus:
            statustext = "Not connected to broker            "
        elif not self.resource_online:
            statustext = "Climateservice offline.            "
        else:
            if self.aircondition_state == STATE_UNKNOWN:
                acstatus = "unknown"
            elif self.aircondition_state:
                acstatus = "on"
            else:
                acstatus = "off"
            TEMPLATE = "{:5.1f} km/h {:4.0f} RPM {:5.1f} degC, AC {:<8s}"
            statustext = TEMPLATE.format(self.vehiclespeed, self.enginespeed, self.indoortemperature, acstatus)
        sys.stdout.write("\r" + statustext)
        sys.stdout.flush()

    def close(self):
        pass


class GraphicalAppDisplay(CommandlineAppDisplay):

    DISPLAY_TITLE = "Climate app"
    TEMPLATE_AIRCONDITION = "Air condition: {}"
    TEMPLATE_VEHICLESPEED = "Vehicle speed: {:.1f} km/h"
    TEMPLATE_ENGINESPEED = "Engine speed: {:.0f} RPM"
    TEMPLATE_TEMPERATURE = "In-car temperature: {:.1f} deg C"
    TEMPLATE_CONNECTION = "Connection status: {}"

    def __init__(self, app):
        if tkinter is None:
            raise ImportError("TK or tkinter is not installed")

        self._rootframe = tkinter.Tk()
        self._rootframe.title(self.DISPLAY_TITLE)

        self._label_temperature = tkinter.Label(self._rootframe, text="")
        self._label_temperature.pack()

        self._label_aircondition = tkinter.Label(self._rootframe, text="")
        self._label_aircondition.pack()

        self._button_on = tkinter.Button(self._rootframe, text="Air condition: Turn ON", width=25)
        self._button_on.pack()
        self._button_on.bind('<Button-1>', self._button_on_handler)

        self._button_off = tkinter.Button(self._rootframe, text="Air condition: Turn OFF", width=25)
        self._button_off.pack()
        self._button_off.bind('<Button-1>', self._button_off_handler)

        dummylabel = tkinter.Label(self._rootframe, text=" ")
        dummylabel.pack()

        self._label_vehiclespeed = tkinter.Label(self._rootframe, text="")
        self._label_vehiclespeed.pack()

        self._label_enginespeed = tkinter.Label(self._rootframe, text="")
        self._label_enginespeed.pack()

        dummylabel = tkinter.Label(self._rootframe, text=" ")
        dummylabel.pack()

        self._label_connectionstatus = tkinter.Label(self._rootframe, text="")
        self._label_connectionstatus.pack()

        super().__init__(app)
        self.loop()

    def _button_on_handler(self, event):
        if self.resource_online:
            logging.info("Turning on air condition")
            self.app.send_command(CLIMATERESOURCE_NAME, MQTT_SIGNALNAME_AIRCONDITION, CAN_PAYLOAD_TRUE)

    def _button_off_handler(self, event):
        if self.resource_online:
            logging.info("Turning off air condition")
            self.app.send_command(CLIMATERESOURCE_NAME, MQTT_SIGNALNAME_AIRCONDITION, CAN_PAYLOAD_FALSE)

    def loop(self):
        """Update the GUI"""
        self._rootframe.update_idletasks()
        self._rootframe.update()

    def close(self):
        """Close the GUI"""
        self._rootframe.destroy()

    def redraw(self):
        if not self.broker_connectionstatus:
            self._initialize_values()
            connectionstatus = "No broker"
            widget_state = tkinter.DISABLED
            ac_statustext = "unknown"
            ac_color = 'black'
        elif not self.resource_online:
            self._initialize_values()
            connectionstatus = "Climateservice offline"
            widget_state = tkinter.DISABLED
            ac_statustext = "unknown"
            ac_color = 'black'
        else:
            connectionstatus = "Climateservice online"
            widget_state = tkinter.NORMAL
            if self.aircondition_state == STATE_UNKNOWN:
                ac_statustext = "unknown"
                ac_color = 'black'
            elif self.aircondition_state:
                ac_statustext = "on"
                ac_color = 'green4'
            else:
                ac_statustext = "off"
                ac_color = 'red'

        self._label_connectionstatus.config(text=self.TEMPLATE_CONNECTION.format(connectionstatus))
        self._button_on.config(state=widget_state)
        self._button_off.config(state=widget_state)
        self._label_vehiclespeed.config(text=self.TEMPLATE_VEHICLESPEED.format(self.vehiclespeed), state=widget_state)
        self._label_enginespeed.config(text=self.TEMPLATE_ENGINESPEED.format(self.enginespeed), state=widget_state)
        self._label_aircondition.config(text=self.TEMPLATE_AIRCONDITION.format(ac_statustext),
                                        state=widget_state, foreground=ac_color)
        self._label_temperature.config(text=self.TEMPLATE_TEMPERATURE.format(self.indoortemperature), state=widget_state)


if __name__ == '__main__':
    main()
