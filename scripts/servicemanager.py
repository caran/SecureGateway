#!/usr/bin/env python3

# A servicemanager for the Secure Gateway concept architecture.
#
# Author: Jonas Berg
# Copyright (c) 2016, Semcon Sweden AB
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

import argparse
import collections
import logging
import signal
import sys
import types

assert sys.version_info >= (3, 3, 0), "Python version 3.3 or later required!"

import sgframework
import sgframework.constants as constants


def signal_handler(signum, frame):
    # This seems necessary to get code coverage measurements from subprocesses to work
    print('Handled Linux signal number:', signum)

signal.signal(signal.SIGTERM, signal_handler)


DESCRIPTIVE_TEXT_TEMPLATE = """
A Service Manager for the Secure Gateway concept architecture

It requires a MQTT broker (for example Mosquitto), and a MQTT client library (Paho).

It registers on the Secure Gateway network, and can connect to
the broker in a secure or insecure way.
The settings of the broker determines what is allowed. To connect in the secure way,
the directory of the certificate files must be specified.

The certificate files should be named:
  CA file:          {}
  Certificate file: {}
  Key file:         {}

"""
MQTT_KEEPALIVE_TIME = 10  # Seconds
CLIENT_NAME = 'servicemanager'


def main():
    epilog = DESCRIPTIVE_TEXT_TEMPLATE.format(sgframework.Resource.CA_CERTS,
                                              sgframework.Resource.CERTFILE, sgframework.Resource.KEYFILE)
    commandlineparser = argparse.ArgumentParser(epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
    commandlineparser.add_argument('-v',
                                   action='count', default=0,
                                   help="Increase verbosity level. Can be repeated.")
    commandlineparser.add_argument('-version',
                                   action='version', version="Version of sgframework is {}.".
                                   format(sgframework.__version__))
    commandlineparser.add_argument('-host',
                                   default='localhost',
                                   help="Broker host name. Defaults to '%(default)s'.")
    commandlineparser.add_argument('-port',
                                   default=1883,
                                   help="Broker port number. Defaults to %(default)s.")
    commandlineparser.add_argument('-cert',
                                   help="Directory for certificate files. Defaults to not using certificates.")
    commandlineparser.add_argument('-qos',
                                   type=int,
                                   choices=[0, 1, 2],
                                   default=0,
                                   help="MQTT quality-of-service setting. Defaults to '%(default)s'.")
    commandline = commandlineparser.parse_args()
    if commandline.v == 1:
        loglevel = logging.INFO
    elif commandline.v >= 2:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.WARNING
    logging.basicConfig(level=loglevel)

    storage = {}
    storage['available_resources'] = set()
    storage['available_commands'] = collections.defaultdict(set)
    storage['available_data'] = collections.defaultdict(set)

    logging.info(" ")
    logging.info(" ")
    logging.info("  ***** Starting servicemanager *****")

    manager = sgframework.framework.BaseFramework(CLIENT_NAME, commandline.host, commandline.port, commandline.cert)
    manager._on_incoming_message = types.MethodType(on_incoming_message, manager)
    manager._subscribe_to_inputsignals = types.MethodType(subscribe_to_inputsignals, manager)
    manager.keepalive = MQTT_KEEPALIVE_TIME
    manager.qos = commandline.qos
    manager.userdata = storage

    manager.start()

    while True:
        manager.loop()


def on_incoming_message(self, mqttclient, userdata, message):
    """MQTT callback at incoming messages.

    Method signature according to Paho documentation.

    """
    storage = userdata

    ## Extract information from the message ##
    inputpayload = str(message.payload, encoding='latin1').strip()  # Paho MQTT delivers bytes for Python3
    inputtopic = str(message.topic).strip()

    topic_hierarchy = inputtopic.split(constants.MQTT_TOPIC_SEPARATOR)
    if len(topic_hierarchy) != constants.MQTT_TOPIC_DEPTH:
        self.logger.warning("Received wrong MQTT topic structure: {}, payload: '{}'".format(inputtopic, inputpayload))
        return

    self.logger.debug("Received message. Topic: {}, payload: '{}'".format(inputtopic, inputpayload))

    messagetype, servicename, signalname = topic_hierarchy
    messagetype = messagetype.strip()
    servicename = servicename.strip()
    signalname = signalname.strip()

    # Available resource
    if messagetype == constants.PREFIX_RESOURCEAVAILABLE \
            and signalname == constants.SUFFIX_PRESENCE \
            and inputpayload == constants.PAYLOAD_TRUE:
        storage['available_resources'].update([servicename])
        self.logger.info("Available resource: {}".format(servicename))

    # Available data and commands
    elif messagetype == constants.PREFIX_COMMANDAVAILABLE and inputpayload == constants.PAYLOAD_TRUE:
        self.logger.info("Available command: '{}' for resource '{}'".format(signalname, servicename))
        storage['available_resources'].update([servicename])
        storage['available_commands'][servicename].update([signalname])
    elif messagetype == constants.PREFIX_DATAAVAILABLE and inputpayload == constants.PAYLOAD_TRUE:
        self.logger.info("Available data: '{}' for resource '{}'".format(signalname, servicename))
        storage['available_resources'].update([servicename])
        storage['available_data'][servicename].update([signalname])

    # Resource now offline
    elif messagetype == constants.PREFIX_RESOURCEAVAILABLE \
            and signalname == constants.SUFFIX_PRESENCE \
            and inputpayload == constants.PAYLOAD_FALSE:
        if servicename in storage['available_resources']:
            self.logger.info("Resource now offline: '{}'".format(servicename))

            if servicename in storage['available_commands']:
                for commandname in storage['available_commands'][servicename]:
                    topic = constants.MQTT_TOPIC_TEMPLATE.format(constants.PREFIX_COMMANDAVAILABLE,
                                                                 servicename,
                                                                 commandname)
                    self.logger.info("Sending out command unavailable: '{}' for resource '{}'".format(
                            commandname, servicename))
                    mqttclient.publish(topic,
                                       constants.PAYLOAD_FALSE,
                                       qos=self.qos,
                                       retain=True)

            if servicename in storage['available_data']:
                for dataname in storage['available_data'][servicename]:
                    topic = constants.MQTT_TOPIC_TEMPLATE.format(constants.PREFIX_DATAAVAILABLE,
                                                                 servicename,
                                                                 dataname)
                    self.logger.info("Sending out data unavailable: '{}' for resource '{}'".format(
                            dataname, servicename))
                    mqttclient.publish(topic,
                                       constants.PAYLOAD_FALSE,
                                       qos=self.qos,
                                       retain=True)

            storage['available_resources'] -= set([servicename])
            storage['available_data'].pop(servicename, None)
            storage['available_commands'].pop(servicename, None)
        else:
            self.logger.warning("Message about offline resource, but it was not listed before. " +
                                "Topic: '{}' Payload: '{}'".format(inputtopic, inputpayload))

    # Messages not to handle
    elif messagetype in [constants.PREFIX_DATAAVAILABLE, constants.PREFIX_COMMANDAVAILABLE] \
            and inputpayload == constants.PAYLOAD_FALSE:
        self.logger.debug("Unavailability message for data or command. Probably old from broker. " +
                          "Topic: '{}' Payload: '{}'".format(inputtopic, inputpayload))
    else:
        self.logger.warning("Wrong message structure. Topic: '{}' Payload: '{}'".format(inputtopic, inputpayload))


def subscribe_to_inputsignals(self):
    """Override the _subscribe_to_inputsignals method in sgframework.framework.BaseFramework"""
    for prefix in [constants.PREFIX_RESOURCEAVAILABLE,
                   constants.PREFIX_COMMANDAVAILABLE,
                   constants.PREFIX_DATAAVAILABLE]:
        self.mqttclient.subscribe(prefix +
                                  constants.MQTT_TOPIC_SEPARATOR +
                                  constants.SUFFIX_WILDCARD_MULTILEVEL,
                                  qos=self.qos)

if __name__ == '__main__':
    main()
