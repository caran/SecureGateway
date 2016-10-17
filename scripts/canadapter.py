#!/usr/bin/env python3
#
# CAN adapter for the Secure Gateway concept architecture
#
# Author: Jonas Berg
# Copyright (c) 2016, Semcon Sweden AB
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted
# provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the
#    following disclaimer.
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

import argparse
import logging
import signal
import sys

assert sys.version_info >= (3, 3, 0), "Python version 3.3 or later required!"

import can4python
import sgframework
import canadapterlib

def signal_handler(signum, frame):
    # This seems necessary to get code coverage measurements from subprocesses to work
    print('Handled Linux signal number:', signum)

signal.signal(signal.SIGTERM, signal_handler)

EXIT_CODE_WRONG_COMMANDLINE_ARGUMENTS = 2
DESCRIPTIVE_TEXT_TEMPLATE = """
A CAN adapter for the Secure Gateway concept architecture

This is a "Resource" according to the Secure Gateway nomenclature. It registers
on the Secure Gateway network, and accepts commands that will be sent over the
CAN network. Signals received from the CAN network are forwarded to
the Secure Gateway MQTT (over IP) network.

It is intended for running on a Linux machine having a CAN interface,
for example a Beaglebone or Raspberry Pi with appropriate expansion boards
(capes/HATs). It can also be used on simulated (virtual) CAN buses on Linux.

It requires a MQTT broker (for example Mosquitto), and a MQTT client library (Paho).

This resource can connect to the broker in a secure or insecure way.
The settings of the broker determines what is allowed. To connect in the secure way,
the directory of the certificate files must be specified.

The certificate files should be named:
  CA file:          {}
  Certificate file: {}
  Key file:         {}

"""

# Settings #
CAN_TIMEOUT = 1  # seconds


def init_canadapter():
    """Initialize the canadapter.

    Returns a 'resource' in the sgframework terminology.

    """
    # Parse command line and set output verbosity #
    epilog = DESCRIPTIVE_TEXT_TEMPLATE.format(sgframework.Resource.CA_CERTS,
                                              sgframework.Resource.CERTFILE,
                                              sgframework.Resource.KEYFILE)
    commandlineparser = argparse.ArgumentParser(epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
    commandlineparser.add_argument('kcdfile',
                                   help="File name for CAN bus definition (in KCD file format).")
    commandlineparser.add_argument('-mqttfile',
                                   default=None,
                                   help="File name for mqtt-and-CAN signal name and permission translation (JSON). " +
                                        "Defaults to listen to all CAN signals (no JSON file used).")
    commandlineparser.add_argument('-v',
                                   action='count', default=0,
                                   help="Increase verbosity level. Can be repeated.")
    commandlineparser.add_argument('-version',
                                   action='version', version="Version of sgframework is {}. Using can4python {}.".
                                   format(sgframework.__version__, can4python.__version__))
    commandlineparser.add_argument('-i',
                                   dest="interface", default="vcan0",
                                   help="CAN interface name. Defaults to '%(default)s'.")
    commandlineparser.add_argument('-host',
                                   default='localhost',
                                   help="Broker host name. Defaults to '%(default)s'.")
    commandlineparser.add_argument('-port',
                                   default=1883,
                                   help="Broker port number. Defaults to %(default)s.")
    commandlineparser.add_argument('-qos',
                                   type=int,
                                   choices=[0, 1, 2],
                                   default=0,
                                   help="MQTT quality-of-service setting. Defaults to '%(default)s'.")
    commandlineparser.add_argument('-k',
                                   default=10,
                                   type=int,
                                   dest='keepalive',
                                   help="Set keepalive time for MQTT communication to the broker, in seconds. " +
                                        "Defaults to %(default)s seconds.")
    commandlineparser.add_argument('-cert',
                                   help="Directory for certificate files. Defaults to not using certificates.")
    commandlineparser.add_argument('-busname',
                                   default=None,
                                   help="CAN Bus name in the KCD file. " +
                                        "Defaults to use the first busname (alphabetically).")
    commandlineparser.add_argument('-mqttname',
                                   default='canadapter',
                                   help="Resource name for MQTT topics. Defaults to '%(default)s'.")
    commandlineparser.add_argument('-listentoallcan',
                                   action='store_true',
                                   help="Listen to all CAN signals, and send them on MQTT using the same signalname. " +
                                        "Will be overrided by -mqttfile option.")
    commandlineparser.add_argument('-bcm',
                                   action='store_true',
                                   help="Use broadcast manager (BCM) for periodic sending of CAN frames by the Linux kernel. " +
                                   "Defaults to not using the broadcast manager. See documentation for can4python. " +
                                   "Requires Python 3.4 or later.")
    commandlineparser.add_argument('-t',
                                   dest='throttlingtime',
                                   default=None,
                                   type=int,
                                   help="Set throttling time (max update rate) for incoming frames, in milliseconds. " +
                                   "Is automatically setting the '-bcm' option. " +
                                   "Defaults to not throttle incoming frame rate.")
    commandlineparser.add_argument('-ego',
                                   nargs='+',
                                   default=["1"],
                                   help="Set ego node id (string), for defining which of the frames in the " +
                                   "KCD file should be sent. By default other frames are received. Several ids can be given. "
                                   "Defaults to '%(default)s'. " +
                                   "See KCD file definition documentation.")

    commandline = commandlineparser.parse_args()
    if commandline.v == 1:
        loglevel = logging.INFO
    elif commandline.v >= 2:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.WARNING
    logging.basicConfig(level=loglevel)
    if commandline.throttlingtime is not None:
        commandline.bcm = True
        if commandline.throttlingtime < 0 or \
                commandline.throttlingtime > can4python.constants.MAX_FRAME_CYCLETIME_MILLISECONDS:
            logging.error("Throttling time out ouf range. Given: {} ms".format(commandline.throttlingtime))
            exit(EXIT_CODE_WRONG_COMMANDLINE_ARGUMENTS)
    if commandline.keepalive < 0:
            logging.error("Keepalive time out ouf range. Given: {} s".format(commandline.keepalive))
            exit(EXIT_CODE_WRONG_COMMANDLINE_ARGUMENTS)
    if commandline.mqttfile is None and not commandline.listentoallcan:
        logging.error("You must give the translation file name, or the listentoallcan flag.")
        exit(EXIT_CODE_WRONG_COMMANDLINE_ARGUMENTS)

    # Set up CAN bus #
    logging.info(" ")
    logging.info(" ")
    logging.info("  ***** Starting canadapter on CAN interface: {!r} *****".format(
            commandline.interface))
    logging.info("CAN file (KCD): {}".format(commandline.kcdfile))
    logging.info("Busname in CAN file (KCD): {}".format(commandline.busname))
    logging.info("Signaldefinition file CAN-to-MQTT (JSON): {}".format(commandline.mqttfile))
    logging.info("MQTT resource name: {}".format(commandline.mqttname))
    logging.info(" ")

    can_config = can4python.FilehandlerKcd.read(filename=commandline.kcdfile,
                                                busname=commandline.busname)
    can_config.ego_node_ids = commandline.ego
    if commandline.throttlingtime is not None:
        for frame_id, framedef in can_config.framedefinitions.items():
            if not framedef.is_outbound(can_config.ego_node_ids):
                framedef.throttle_time = commandline.throttlingtime

    canbus = can4python.CanBus(can_config,
                               interfacename=commandline.interface,
                               timeout=CAN_TIMEOUT,
                               use_bcm=commandline.bcm)
    logging.debug(canbus.get_descriptive_ascii_art())

    # Arrange signal name conversion info #
    # We know that if no mqtt file is given it implies commandline.listentoallcan.
    converter = canadapterlib.Converter(can_config, commandline.mqttfile)
    logging.debug(converter.get_descriptive_ascii_art())

    # Initialize Secure Gateway (MQTT) resource framework #
    resource = sgframework.Resource(commandline.mqttname,
                                    commandline.host,
                                    commandline.port,
                                    commandline.cert)
    resource.keepalive = commandline.keepalive
    resource.qos = commandline.qos
    resource.userdata = (canbus, converter)

            # Register incoming MQTT commands
    for args in converter.get_definitions_incoming_mqtt_command():
        args['callback'] = on_send_can_data
        resource.register_incoming_command(**args)

            # Register outgoing MQTT data
    for args in converter.get_definitions_outgoing_mqtt_data():
        resource.register_outgoing_data(**args)

    logging.debug(resource.get_descriptive_ascii_art())

    resource.start(use_threaded_networking=True)
    canbus.init_reception()
    return resource


def loop_canadapter(resource):
    canbus, converter = resource.userdata

    # Receive CAN data, send MQTT messages #
    # (Note that sending CAN data is made in a callback)
    try:
        frame = canbus.recv_next_frame()
    except (can4python.exceptions.CanTimeoutException, InterruptedError):
        return
    except KeyboardInterrupt:
        logging.warning("Keyboard interrupt. Quitting.")
        raise
    logging.debug("Received CAN frame: {}".format(frame))
    try:
        messages = converter.canframe_to_mqtt(frame)
    except Exception as err:
        logging.error("Failed to convert incoming CAN frame. Error: {}".format(err))
        return
    for mqtt_signal_name, payload_mqtt_data in messages:
        logging.debug("Sending MQTT message. Signal name: '{}' Value: '{}'".format(mqtt_signal_name, payload_mqtt_data))
        resource.send_data(mqtt_signal_name, payload_mqtt_data)


###############
## Callbacks ##
###############

def on_send_can_data(resource, messagetype, servicename, command_name_mqtt, command_payload_mqtt):
    """Callback for use when receiving a MQTT message. Sends a CAN message.

    For callback interface, see sgframework.BaseFramework() documentation.

    """
    canbus, converter = resource.userdata
    signal_value_pairs = converter.mqtt_to_cansignals(command_name_mqtt, command_payload_mqtt)
    logging.info("Sending CAN signals: {}".format(signal_value_pairs))

    if signal_value_pairs:
        canbus.send_signals(signal_value_pairs)


######################
## Main application ##
######################

def main():
    resource = init_canadapter()

    ## Main loop ##
    while True:
        try:
            loop_canadapter(resource)
        except KeyboardInterrupt:
            sys.exit()


if __name__ == '__main__':
    main()
