#
# An "App" and "Resource" framework the Secure Gateway concept architecture.
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
#

import logging
import os
import ssl
import sys
import time

import paho.mqtt.client as mqtt

assert sys.version_info >= (3, 2, 0), "Python version 3.2 or later required!"

from . import constants


class BaseFramework:
    # App and Resource framework base for the Secure Gateway.
    # NOTE: The docstring is reused also for the App and Resource objects.
    """

    Parameters:
        name (str): Name of the app/resource. For resources, it is also used
            in the MQTT topic hierarchy.
        host (str): Broker host name.
        port (int): Broker port number.
        certificate_directory (str or None): Full path to the directory
            of the certificate files.

    Attributes:
        protocol (enum in the Paho module): MQTT protocol version,
            defaults to ``MQTTv31``, as older versions of the Mosquitto
            broker can not handle ``MQTTv311``.
        tls_version (enum in the ssl module): SSL protocol version,
            defaults to ``ssl.PROTOCOL_TLSv1``
        qos (int): MQTT quality of service. 0, 1 or 2. See Paho
            documentation. Default value ``DEFAULT_QOS`` is set in :mod:`sgframework.constants`.
        timeout (numerical): MQTT socket timeout, when running the ``loop()``
            method. Default value ``DEFAULT_TIMEOUT``.
        keepalive (numerical): MQTT keepalive message interval.
            Default value ``DEFAULT_KEEPALIVE_TIME``.

    Also the parameters appear as attributes. The public attributes are
    used when calling :meth:`.start`. Any changes are valid from next :meth:`.start`.

    References to sub-objects:

    * **mqttclient** (object): See Paho documentation
    * **logger** (object): See Python standard library documentation
    * **userdata** (whatever): Convenience object that is available for user
      code in callbacks. Not used by the framework itself.
    * **on_broker_connectionstatus_info**: Implement this callback if you
      would like notifications on broker connection status changes. See below.

    Callback to the user application on changed broker connection status::

        on_broker_connectionstatus_info(app_or_resource, broker_connected)

    Where *app_or_resource* is the app or resource object, and
    *broker_connected* (**bool**) is :const:`True` if the user
    application is connected to the broker.

    Callbacks to the user application on incoming information are registered
    using separate methods. The callbacks should have this interface::

        callbackname(resource_or_app, messagetype, servicename, signalname, inputpayload)

    where *messagetype*, *servicename*, *signalname* and *inputpayload* are strings.
    The callback is protected by try/except.
    The strings to the callback have been through ``.strip()``.

    When using echo and the returnvalue of the callback is ``None``,
    the command payload is used in the echo.
    For returnvalues other then ``None``, the echo payload will be ``str(returnvalue)``.
    More than one input signal can use the same callback.

    The certificate files should be named according to ``CA_CERTS``,
    ``CERTFILE`` and ``KEYFILE``.

    """
    # Constants useful for users of this library
    CA_CERTS = constants.CA_CERTS
    KEYFILE = constants.KEYFILE
    CERTFILE = constants.CERTFILE
    PREFIX_RESOURCEAVAILABLE = constants.PREFIX_RESOURCEAVAILABLE
    PAYLOAD_TRUE = constants.PAYLOAD_TRUE
    PAYLOAD_FALSE = constants.PAYLOAD_FALSE

    def __init__(self, name, host, port=1883, certificate_directory=None):
        self.name = str(name).strip()
        self.host = str(host).strip()
        self.port = int(port)
        self.certificate_directory = certificate_directory

        self.protocol = mqtt.MQTTv31
        self.tls_version = ssl.PROTOCOL_TLSv1
        self.qos = constants.DEFAULT_QOS
        self.timeout = constants.DEFAULT_TIMEOUT
        self.keepalive = constants.DEFAULT_KEEPALIVE_TIME

        self.on_broker_connectionstatus_info = None
        self.mqttclient = None
        self.userdata = None
        self.logger = logging.getLogger(self.name)

        self._use_clean_session = True
        self._use_threaded_networking = False
        self._use_last_will = False

        # This is the 'last will' topic
        self._servicepresence_topic = constants.MQTT_TOPIC_TEMPLATE.format(
                                        constants.PREFIX_RESOURCEAVAILABLE,
                                        self.name,
                                        constants.SUFFIX_PRESENCE)

        # Storage of incoming signal definitions that should be subscribed to.
        # It can be data, dataavailable, command, commandavailable, resourceavailable
        # Also holds the callback to be used at incoming signals.
        # Key: topic, Item: Inputsignalinfo
        self._inputsignal_infodict = {}

        # Storage of outgoing signal definitions.
        # (Probably only data).
        # Typically for sending dataavailable at start
        # Key: topic, Item: Outputsignalinfo
        self._outputsignal_infodict = {}

    def __repr__(self):
        return "SG Base Framework: '{}', connecting to host '{}', port {}. Has {} incoming and {} outgoing topics registered.".format(
            self.name, self.host, self.port, len(self._inputsignal_infodict), len(self._outputsignal_infodict))

    def get_descriptive_ascii_art(self):
        """Display an overview with registered incoming and outgoing topics.

        Returns:
          A multi-line string.

        """
        text = repr(self) + " Details: \n"
        text += "  Registered incoming topics:\n"
        for topic in self._inputsignal_infodict:
            text += "    " + topic + "\n"
            text += "        " + repr(self._inputsignal_infodict[topic]) + "\n"
        text += "  Registered outgoing topics:\n"
        for topic in self._outputsignal_infodict:
            text += "    " + topic + "\n"
            text += "        " + repr(self._outputsignal_infodict[topic]) + "\n"

        return text

    def start(self, use_threaded_networking=False, use_clean_session=True):
        """Connect to the broker.

        Args:
            use_threaded_networking (bool): Start MQTT networking
                activity in a separate thread.
            use_clean_session (bool): Connect to broker using a clean session.

        If not using threaded networking, you need to call the ``loop()``
        method frequently.

        If using a clean session, also the client name is changed to include
        the process ID. This in order to avoid client name collisions
        in the broker.


        """
        self._use_threaded_networking = use_threaded_networking
        self._use_clean_session = use_clean_session

        if self.mqttclient is not None:
            self.stop()

        self._set_broker_connectionstatus(False)

        if self._use_clean_session:
            client_id = constants.CLIENT_ID_TEMPLATE.format(self.name, os.getpid())
        else:
            client_id = self.name
        self.mqttclient = mqtt.Client(client_id=client_id,
                                      clean_session=self._use_clean_session,
                                      userdata=self.userdata,
                                      protocol=self.protocol)
        self.mqttclient.on_connect      = self._on_connect
        self.mqttclient.on_disconnect   = self._on_disconnect
        self.mqttclient.on_subscribe    = self._on_subscribe
        self.mqttclient.on_unsubscribe  = self._on_unsubscribe
        self.mqttclient.on_publish      = self._on_publish
        self.mqttclient.on_message      = self._on_incoming_message
        self.mqttclient.on_log          = self._on_mqttclient_log_event

        self.logger.info("Setting up connection to the MQTT broker. Host: {}, Port: {}, QoS: {}".
                         format(self.host, self.port, self.qos))

        if self.certificate_directory is not None:
            ca_file = os.path.join(self.certificate_directory, constants.CA_CERTS)
            certfile = os.path.join(self.certificate_directory, constants.CERTFILE)
            keyfile = os.path.join(self.certificate_directory, constants.KEYFILE)
            self.logger.info('Using certificate for MQTT communication.')
            self.logger.info('   CA file: {}'.format(ca_file))
            self.logger.info('   Certificate file: {}'.format(certfile))
            self.logger.info('   Key file: {}'.format(keyfile))
            self.mqttclient.tls_set(ca_file, certfile, keyfile, tls_version=self.tls_version)

        if self._use_last_will:
            self.mqttclient.will_set(self._servicepresence_topic,
                                     constants.PAYLOAD_FALSE,
                                     qos=self.qos,
                                     retain=True)
            self.logger.debug('    Setting last will: {}'.format(self._servicepresence_topic))

        self.mqttclient.connect_async(self.host, self.port, keepalive=int(self.keepalive))  # Keepalive must be int

        if self._use_threaded_networking:
            self.mqttclient.loop_start()
            time.sleep(constants.SLEEP_START)

    def stop(self):
        """Disconnect from the broker"""
        self.logger.info('Disconnecting from the MQTT broker. Host: {}, Port: {}'.format(self.host, self.port))
        if self._use_last_will:
            try:
                self.mqttclient.publish(self._servicepresence_topic,
                                        constants.PAYLOAD_FALSE,
                                        qos=1,
                                        retain=True)
            except AttributeError:
                raise ValueError("You must call start() before stop().")
        time.sleep(constants.SLEEP_STOP)
        self.mqttclient.disconnect()
        self.mqttclient.loop_stop()
        self._set_broker_connectionstatus(False)

    def loop(self):
        """Run network activities.

        This function needs to be called frequently to keep the network
        traffic alive, if not using threaded networking.
        It will block until a message is received, or until
        the self.timeout value.

        If not connected to the broker, it will try to connect once.

        Do not use this function when running threaded networking.

        """
        if self._use_threaded_networking:
            self.logger.warning("You must should not use the loop() method when running a threaded networking interface.")
            return

        try:
            errorcode = self.mqttclient.loop(self.timeout)
        except AttributeError:
            raise ValueError("You must call start() before loop().")

        if not errorcode:
            return

        if errorcode == mqtt.MQTT_ERR_UNKNOWN:
            self.logger.warning("Probably keyboard interrupt, quitting (MQTT error message: '{}')".format(
                                mqtt.error_string(errorcode)))
            self.stop()
            sys.exit()
        if errorcode == mqtt.MQTT_ERR_CONN_LOST:
            self.logger.info("MQTT connection error, trying to reconnect. Error message: '{}'".format(
                    mqtt.error_string(errorcode)))
        elif errorcode in [mqtt.MQTT_ERR_NO_CONN, mqtt.MQTT_ERR_CONN_REFUSED]:
            self.logger.warning("MQTT connection error, trying to reconnect. Error message: '{}'".format(
                    mqtt.error_string(errorcode)))
        else:
            self.logger.warning("MQTT error. Error message: '{}'".format(mqtt.error_string(errorcode)))
            return

        try:
            self.mqttclient.reconnect()
        except Exception:
            self.logger.warning("Failed to connect to the MQTT broker. Host: {}, Port: {}".format(self.host, self.port))
            self._set_broker_connectionstatus(False)
            time.sleep(1)

    def register_incoming_data(self, servicename, signalname, callback, callback_on_change_only=False):
        """Register a callback for incoming data (incoming MQTT message).

        Primarily useful for apps (but is useful for resources to receive data
        from other resources).

        Args:
            servicename (str): name of the service sending the data
            signalname (str):  name of the signal
            callback (function): Callback that will be used when data is received.
            callback_on_change_only (bool): Trigger callback only for changed payload.

        For details on the callback, see the class documentation.

        Subscribes to: ``data/``\ *servicename*\ ``/``\ *signalname*

        for example: ``data/climateservice/actualindoortemperature``.

        """
        self.logger.debug("Registering incoming data. Servicename: {}, Signalname: {}".
                          format(servicename, signalname))
        self._register_inputsignal(constants.PREFIX_DATA, servicename, signalname, callback, callback_on_change_only)

    def register_incoming_availability(self, prefix,
                                       servicename, signalname, callback):
        """Register a callback for incoming availability information (incoming MQTT message).

        Primarily useful for apps (but is useful for resources to receive data
        etc from other resources).

        Args:
            prefix (str): one of PREFIX_COMMANDAVAILABLE, PREFIX_DATAAVAILABLE
                (or maybe PREFIX_RESOURCEAVAILABLE)
            servicename (str): name of the service sending the availability info
            signalname (str):  name of the data or command
            callback (function): Callback that will be used when availability information is received.

        When registering a callback for RESOURCEAVAILABLE the actual value of
        the signalname is not used. Just pass in any string.

        For details on the callback, see the class documentation.

        Subscribes to: *prefix*\ ``/``\ *servicename*\ ``/``\ *signalname*

        for example: ``dataavailable/climateservice/actualindoortemperature``.

        """
        assert prefix in [constants.PREFIX_COMMANDAVAILABLE,
                          constants.PREFIX_DATAAVAILABLE,
                          constants.PREFIX_RESOURCEAVAILABLE], \
            "Wrong prefix given: {!r}".format(prefix)

        if prefix == constants.PREFIX_RESOURCEAVAILABLE:
            signalname = constants.SUFFIX_PRESENCE
        self.logger.debug("Registering incoming availability. Prefix: {}, Servicename: {}, Signalname: {}".
                          format(prefix, servicename, signalname))
        self._register_inputsignal(prefix, servicename, signalname, callback)

    def send_command(self, servicename, signalname, value, send_command_as_retained=False):
        """Send a command.

        Primarily useful for apps (but is useful for resources to control other resources).

        Args:
            servicename (str): destination service name
            signalname (str): destination signal name
            value: Value to be sent. Is converted to a string before sending.
            send_command_as_retained (bool): Publish the command as retained.

        Sends messages on topic: ``command/``\ *servicename*\ ``/``\ *signalname*

        for example ``command/climateservice/aircondition``.

        Most often commands are sent as non-retained messages.


        """
        topic = constants.MQTT_TOPIC_TEMPLATE.format(
                    constants.PREFIX_COMMAND,
                    str(servicename).strip(),
                    str(signalname).strip())
        try:
            self.mqttclient.publish(topic, str(value), qos=self.qos, retain=send_command_as_retained)
        except AttributeError:
            raise ValueError("You must call start() before send_command().")
        self.logger.debug("    Sending command. Topic: {}, payload: {!s}".format(topic, value))
        time.sleep(constants.SLEEP_PUBLISH)

    def _register_inputsignal(self, messagetype, servicename, signalname, callback,
                              callback_on_change_only=False, echo=False, send_echo_as_retained=False,
                              defaultvalue=None):
        """Register a callback for an incoming MQTT message.

        Args:
            messagetype (str): One of the predefined message types (also known as prefix).
            servicename (str): service name
            signalname (str): signal name
            callback (function): Callback that will be used when a signal is received.
            callback_on_change_only (bool): Trigger callback only for changed payload.
            echo (bool): True if the incoming signal should be echoed back (as "data")
            send_echo_as_retained (bool): True if the echo should be published as retained.
            defaultvalue: Value to be echoed on startup. Set to None to avoid sending.
                  The value is converted to a string before sending. It will be updated by _on_incoming_message().

        For details on the callback, see the class documentation.

        Subscribes to: *messagetype*\ ``/``\ *servicename*\ ``/``\ *signalname*

        The *messagetype* can be ``data``, ``dataavailable``, ``command``,
        ``commandavailable``, ``resourceavailable``.

        For example: ``data/climateservice/actualindoortemperature``.

        """
        topic = constants.MQTT_TOPIC_TEMPLATE.format(str(messagetype).strip(),
                                                     str(servicename).strip(),
                                                     str(signalname).strip())
        self._inputsignal_infodict[topic] = Inputsignalinfo(str(messagetype).strip(),
                                                            str(servicename).strip(),
                                                            str(signalname).strip(),
                                                            callback,
                                                            bool(callback_on_change_only),
                                                            bool(echo),
                                                            bool(send_echo_as_retained),
                                                            defaultvalue)

    def _register_outputsignal(self, messagetype, servicename, signalname,
                               defaultvalue, send_as_retained):
        """Registering outgoing MQTT messages.

        This is typically used for automatically send availability information.

        Args:
            messagetype (str): One of the predefined message types (also known as prefix),
                most often ``data``.
            servicename (str): service name, most often ``self.name``.
            signalname (str): signal name
            defaultvalue: Value to be sent on startup. Set to None to avoid sending.
                  The value is converted to a string before sending.
            send_as_retained (bool): True if the signal should be published as retained.

        Publishes to: *messagetype*\ ``/``\ *servicename*\ ``/``\ *signalname*

        for example: ``data/climateservice/actualindoortemperature``.

        There is also a mechanism to automatically publish availability topics,
        for example: ``dataavailable/climateservice/actualindoortemperature``.


        """
        topic = constants.MQTT_TOPIC_TEMPLATE.format(str(messagetype).strip(),
                                                     str(servicename).strip(),
                                                     str(signalname).strip())
        self._outputsignal_infodict[topic] = Outputsignalinfo(str(messagetype).strip(),
                                                              str(servicename).strip(),
                                                              str(signalname).strip(),
                                                              defaultvalue,
                                                              bool(send_as_retained))

    def _publish_capablities_and_defaultvalues(self):
        """To be overrided"""
        pass

    def _subscribe_to_inputsignals(self):
        """Do the subscription to input signals"""
        for signalname, inputsignalinformation in self._inputsignal_infodict.items():
            subscription_topic = constants.MQTT_TOPIC_TEMPLATE.format(
                                    inputsignalinformation.messagetype,
                                    inputsignalinformation.servicename,
                                    inputsignalinformation.signalname)
            self.logger.info("    Subscribing to MQTT topic: '{}'".format(subscription_topic))
            self.mqttclient.subscribe(subscription_topic, qos=self.qos)

    def _set_broker_connectionstatus(self, broker_connected):
        """
        Set information whether the broker is connected.
        This is triggering a callback to the user script.

        The information is not stored in the framework, it is the responsibility of the user script.

        Args:
            broker_connected (bool): Indicates whether the broker is connected or not

        """
        if self.on_broker_connectionstatus_info is not None:
            self.logger.debug("    Setting broker connection status to user script: {}".format(broker_connected))
            try:
                self.on_broker_connectionstatus_info(self, broker_connected)
            except Exception as err:
                self.logger.warning("Failed to run callback for broker connection. Status: '{}'. Error: '{}'".format(
                                        broker_connected, err))

    ## Callbacks ##

    def _on_incoming_message(self, mqttclient, userdata, message):
        """MQTT callback at incoming messages.

        Executes a preregistered callback, and publishes an echo (if configured).

        Updates the default value for echoed signals if configured.

        Method signature according to Paho documentation.

        """

        ## Extract information from the message ##
        inputpayload = str(message.payload, encoding='utf-8').strip()  # Paho MQTT delivers bytes for Python3
        inputtopic = str(message.topic).strip()

        topic_hierarchy = inputtopic.split(constants.MQTT_TOPIC_SEPARATOR)
        if len(topic_hierarchy) != constants.MQTT_TOPIC_DEPTH:
            self.logger.warning("Received wrong MQTT topic structure: {}, payload: '{}'".format(
                    inputtopic, inputpayload))
            return

        self.logger.debug("Received message. Topic: {}, payload: '{}'".format(inputtopic, inputpayload))

        try:
            inputsignalinformation = self._inputsignal_infodict[inputtopic]
        except KeyError:
            self.logger.warning("Received unregistered input message. Topic: {}, payload: '{}'".format(
                    inputtopic, inputpayload))
            return

        messagetype, servicename, signalname = topic_hierarchy
        messagetype = messagetype.strip()
        servicename = servicename.strip()
        signalname = signalname.strip()

        ## Check for input payload changes (compared to last message) ##
        if inputsignalinformation.callback_on_change_only:
            if inputsignalinformation.last_payload is not None:
                if inputsignalinformation.last_payload == inputpayload:
                    self.logger.debug("The payload has not changed, skipping callback. Topic: {}, payload: '{}'".format(
                            inputtopic, inputpayload))
                    return
            inputsignalinformation.last_payload = inputpayload

        ## Run registered callback ##
        try:
            returnvalue = inputsignalinformation.callback(self,
                                                          messagetype,
                                                          servicename,
                                                          signalname,
                                                          inputpayload)
        except Exception as err:
            self.logger.warning("Failed to run callback for topic: {}, payload: {}. Error: '{}'".format(
                                inputtopic, inputpayload, err))
            return

        ## Send echo message ##
        if inputsignalinformation.echo:
            echo_payload = inputpayload if returnvalue is None else str(returnvalue)
            echo_messagetype = constants.ECHO_MESSAGETYPES[messagetype]
            echo_publication_topic = constants.MQTT_TOPIC_TEMPLATE.format(
                                        echo_messagetype,
                                        servicename,
                                        signalname)
            self.mqttclient.publish(echo_publication_topic,
                                    echo_payload,
                                    qos=self.qos,
                                    retain=inputsignalinformation.send_echo_as_retained)
            self.logger.debug("    Sending message echo. Topic: {}, payload: {}'".
                              format(echo_publication_topic, echo_payload))
            if inputsignalinformation.defaultvalue is not None:
                inputsignalinformation.defaultvalue = echo_payload

    def _on_connect(self, mqttclient, userdata, flags, rc):
        """MQTT callback at connection attempts.

        This callback is responsible for doing the subscriptions, and to
        publish capabilities and default values.

        Method signature according to Paho documentation.

        """
        if rc != mqtt.CONNACK_ACCEPTED:
            self.logger.warning("  Failed connection to MQTT broker. Host: {}, Port: {}, Result: '{}'".format(
                mqttclient._host, mqttclient._port, mqtt.connack_string(rc)))
            self._set_broker_connectionstatus(False)
            return

        self.logger.info("  Successful connection to MQTT broker. Host: {}, Port: {}, Result: '{}'".format(
            mqttclient._host, mqttclient._port, mqtt.connack_string(rc)))
        self._set_broker_connectionstatus(True)
        self._subscribe_to_inputsignals()
        self._publish_capablities_and_defaultvalues()

    def _on_disconnect(self, mqttclient, userdata, rc):
        """MQTT callback at disconnect.

        Method signature according to Paho documentation.

        """
        self.logger.warning("Now disconnected from MQTT broker. Host: {}, Port: {}, Result: '{}'".format(
                mqttclient._host, mqttclient._port, mqtt.connack_string(rc)))
        self._set_broker_connectionstatus(False)

    def _on_subscribe(self, mqttclient, userdata, mid, granted_qos):
        """MQTT callback at subscribe.

        Method signature according to Paho documentation.

        """
        self.logger.debug('  Subscribed. Message id: {}, QOS: {}'.format(mid, granted_qos))

    def _on_unsubscribe(self, mqttclient, userdata, mid):
        """MQTT callback at unsubscribe.

        Method signature according to Paho documentation.

        """
        self.logger.info('  Unsubscribed. Message id: {}'.format(mid))

    def _on_publish(self, mqttclient, userdata, mid):
        """MQTT callback at publication confirmation.

        Method signature according to Paho documentation.

        """
        self.logger.debug('  Publication confirmation. Message id: {}'.format(mid))

    def _on_mqttclient_log_event(self, mqttclient, userdata, level, buf):
        """MQTT callback at log event.

        Method signature according to Paho documentation.

        """
        self.logger.debug("  MQTT client has log info. Level: {}, Message: '{}'".format(level, buf))


class App(BaseFramework):
    __doc__ = """App framework for the Secure Gateway

    Sends commands to any resource. Handles incoming MQTT messages (data) from any resource.

    It does not have any 'last will'. Typically sends (non retained=non persistent) commands to:

    ``command/``\ *resource_to_be_controlled*\ ``/``\ *signalname*

    and listens to data on topic:

    ``data/``\ *dataproducing_resource*\ ``/``\ *signalname*


    """ + str(BaseFramework.__doc__)

    def __repr__(self):
        return "SG App: '{}', connecting to host '{}', port {}. Has {} input signals registered.".format(
            self.name, self.host, self.port, len(self._inputsignal_infodict))


class Resource(BaseFramework):
    __doc__ = """Resource framework for the Secure Gateway

    Receives commands from apps (incoming MQTT messages).
    Sends data to apps (outgoing MQTT messages).

    It can also recieve incoming data from other resources, and can send
    commands to other resources.

    The resource name is typically part of incoming and outgoing message topics:

    ``command/``\ *myresourcename*\ ``/``\ *signalname*

    ``data/``\ *myresourcename*\ ``/``\ *signalname*

    Also publishes availability of commands and data, using retained messages:

    ``commandavailable/``\ *myresourcename*\ ``/``\ *signalname*

    ``dataavailable/``\ *myresourcename*\ ``/``\ *signalname*

    When starting up, it sends 'True' to the 'last will' topic in a retained message:

    ``resourceavailable/``\ *myresourcename*\ ``/presence``

    The broker is automatically broadcasting 'False' on 'last will' topic at lost connection.

    """ + str(BaseFramework.__doc__)

    def __init__(self, name, host, port=1883, certificate_directory=None):
        super().__init__(name, host, port, certificate_directory)
        self._use_last_will = True

    def __repr__(self):
        return "SG Resource: '{}', connecting to host '{}', port {}. Has {} incoming and {} outgoing topics registered.".format(
            self.name, self.host, self.port, len(self._inputsignal_infodict), len(self._outputsignal_infodict))

    def register_incoming_command(self, signalname, callback,
                                  callback_on_change_only=False, echo=True, send_echo_as_retained=False,
                                  defaultvalue=None):
        """Register a callback for an incoming command (incoming MQTT message).

        Args:
            signalname (str): command name
            callback (function): Callback that will be used when a command is received.
            callback_on_change_only (bool): Trigger callback only for changed payload.
            echo (bool): True if the incoming command should be echoed
                back (as "data")
            send_echo_as_retained (bool): True if the echo should be
                published as retained.
            defaultvalue: Value to be echoed on startup and reconnect. Set
                to None to avoid sending. The value is converted to a string
                before sending. It will be updated by the internal
                :meth:`._on_incoming_message()` callback for incoming MQTT messages.

        For details on the callback, see the class documentation.

        Subscribes to: ``command/``\ *myresourcename*\ ``/``\ *signalname*

        When the resource is starting, it is publishing a retained message to:

        ``commandavailable/``\ *myresourcename*\ ``/``\ *signalname*

        """
        self.logger.debug("Registering incoming command. Signalname: {}".
                          format(signalname))
        self._register_inputsignal(constants.PREFIX_COMMAND,
                                   self.name,
                                   signalname,
                                   callback,
                                   callback_on_change_only,
                                   echo,
                                   send_echo_as_retained,
                                   defaultvalue)

    def register_outgoing_data(self, signalname, defaultvalue=None, send_data_as_retained=False):
        """Pre-register information on a outgoing data topic (MQTT messages).
        Note that the actual data sending is later done with the :meth:`.send_data()` method.

        Args:
            signalname (str): signal name
            defaultvalue: Value to be sent on startup and reconnect. Set to None to avoid sending.
                         The value is converted to a string before sending. It will be updated by send_data().
            send_data_as_retained (bool): Whether the data should be published as retained

        When the resource is starting, it is publishing a retained message to:

        ``dataavailable/``\ *myresourcename*\ ``/``\ *signalname*

        Upon sending data, the topic is: ``data/``\ *myresourcename*\ ``/``\ *signalname*

        for example: ``data/climateservice/actualindoortemperature``.

        Typically the data is published using non-retained messages.

        """
        self.logger.debug("Registering outgoing data. Signalname: {}".format(signalname))
        self._register_outputsignal(constants.PREFIX_DATA,
                                    self.name,
                                    signalname,
                                    defaultvalue,
                                    send_data_as_retained)

    def send_data(self, signalname, value):
        """Send data on a pre-registered topic.

        Args:
            signalname (str): signal name
            value: Value to be sent. Is convered to a string before sending.

        Sends to the topic: ``data/``\ *myresourcename*\ ``/``\ *signalname*

        for example: ``data/climateservice/actualindoortemperature``.

        Updates the defaultvalue for this signal.

        Whether the signal should be sent as retained or not is set already during registration.

        """
        signalname = str(signalname).strip()
        topic = constants.MQTT_TOPIC_TEMPLATE.format(constants.PREFIX_DATA,
                                                     self.name,
                                                     signalname)
        try:
            output_data_information = self._outputsignal_infodict[topic]
        except KeyError:
            self.logger.warning("This data signalname has not been registered: {}, value: '{!s}'".format(
                    signalname, value))
            return
        try:
            self.mqttclient.publish(topic,
                                    str(value),
                                    qos=self.qos,
                                    retain=output_data_information.send_as_retained)
        except AttributeError:
            raise ValueError("You must call start() before send_data().")
        self.logger.debug("    Sending data. Name: {}, payload: '{!s}'".format(topic, value))
        time.sleep(constants.SLEEP_PUBLISH)
        if output_data_information.defaultvalue is not None:
            output_data_information.defaultvalue = str(value)

    def _publish_capablities_and_defaultvalues(self):
        """

        Sends 'True' to the topic: ``resourceavailable/``\ *myresourcename*\ ``/presence``

        For data in outputsignal storage:

        * Sends ``dataavailable/``\ *myresourcename*\ ``/``\ *signalname*
        * If configured, sends defaultvalue ``data/``\ *myresourcename*\ ``/``\ *signalname*

        For commands in inputsignal storage:

        * Sends ``commandavailable/``\ *myresourcename*\ ``/``\ *signalname*
        * If echo configured, sends  ``dataavailable/``\ *myresourcename*\ ``/``\ *signalname*
        * If configured, sends defaultvalue ``data/``\ *myresourcename*\ ``/``\ *signalname*

        """
        ## Indicate service presence (same topic as 'last will') ##
        self.mqttclient.publish(self._servicepresence_topic,
                                constants.PAYLOAD_TRUE,
                                qos=self.qos,
                                retain=True)
        self.logger.debug("    Capabilities: '{}'".format(self._servicepresence_topic))

        ## Publish dataavailable/ (and default value for data/) for outputsignals ##
        for datatopic, datainformation in self._outputsignal_infodict.items():
            if datainformation.messagetype != constants.PREFIX_DATA:
                continue

            dataavailable_topic = constants.MQTT_TOPIC_TEMPLATE.format(
                                    constants.PREFIX_DATAAVAILABLE,
                                    self.name,
                                    datainformation.signalname)
            self.mqttclient.publish(dataavailable_topic,
                                    constants.PAYLOAD_TRUE,
                                    qos=self.qos,
                                    retain=True)
            self.logger.debug("    Capabilities: {}'".format(dataavailable_topic))
            if datainformation.defaultvalue is not None:
                payload = str(datainformation.defaultvalue)
                self.mqttclient.publish(datatopic,
                                        payload,
                                        qos=self.qos,
                                        retain=datainformation.send_as_retained)
                self.logger.info("  Publishing initial value for {}: {!r}".format(datatopic, payload))

        ## Publish commandavailable/ for inputsignals ##
        ## Also dataavailable/ and defaultvalue for data/ for echoed commands ##
        for commandtopic, commandinformation in self._inputsignal_infodict.items():
            if commandinformation.messagetype != constants.PREFIX_COMMAND:
                continue

            commandavailable_topic = constants.MQTT_TOPIC_TEMPLATE.format(
                                        constants.PREFIX_COMMANDAVAILABLE,
                                        self.name,
                                        commandinformation.signalname)
            self.mqttclient.publish(commandavailable_topic,
                                    constants.PAYLOAD_TRUE,
                                    qos=self.qos,
                                    retain=True)
            self.logger.debug("    Capabilities: '{}'".format(commandavailable_topic))
            if commandinformation.echo:
                dataavailable_topic = constants.MQTT_TOPIC_TEMPLATE.format(
                                        constants.PREFIX_DATAAVAILABLE,
                                        self.name,
                                        commandinformation.signalname)
                self.mqttclient.publish(dataavailable_topic,
                                        constants.PAYLOAD_TRUE,
                                        qos=self.qos,
                                        retain=True)
                self.logger.debug("    Capabilities: '{}'".format(dataavailable_topic))
                if commandinformation.defaultvalue is not None:
                    data_topic = constants.MQTT_TOPIC_TEMPLATE.format(
                                        constants.PREFIX_DATA,
                                        self.name,
                                        commandinformation.signalname)
                    payload = str(commandinformation.defaultvalue)
                    self.mqttclient.publish(data_topic,
                                            payload,
                                            qos=self.qos,
                                            retain=commandinformation.send_echo_as_retained)
                    self.logger.info("  Publishing initial value for {}: {!r}".format(data_topic, payload))

####################
## Helper objects ##
####################

class Inputsignalinfo:
    """Object for storing configuration information about incoming MQTT messages.

    Storage of incoming signal definitions that should be subscribed to.
    It can be data, dataavailable, command, commandavailable, resourceavailable.
    Also holds the callback to be used at incoming signals, and possibly
    a copy of last received payload.

    Arguments are described in the :meth:`.BaseFramework._register_inputsignal` method.

    For details on the callback signature, see the :class:`.BaseFramework` documentation.

    TODO: .messagetype should be a property.

    """
    def __init__(self, messagetype, servicename, signalname,
                 callback, callback_on_change_only,
                 echo, send_echo_as_retained, defaultvalue):

        messagetype = str(messagetype).strip()
        if messagetype not in [constants.PREFIX_COMMANDAVAILABLE,
                               constants.PREFIX_DATAAVAILABLE,
                               constants.PREFIX_RESOURCEAVAILABLE,
                               constants.PREFIX_DATA,
                               constants.PREFIX_COMMAND]:
            raise ValueError("Trying to register an input signal, but the messagetype is wrong: {}".format(
                messagetype))

        self.messagetype = messagetype
        self.servicename = str(servicename).strip()
        self.signalname = str(signalname).strip()
        self.send_echo_as_retained = bool(send_echo_as_retained)
        self.callback = callback
        self.callback_on_change_only = bool(callback_on_change_only)
        self.echo = bool(echo)
        self.defaultvalue = defaultvalue
        self.last_payload = None

    def __repr__(self):
        TEMPLATE = "IN: '{}'-'{}'-'{}' Default: '{}' Echo: {} (echo retained: {}) Callback only on change: {}"
        return TEMPLATE.format(self.messagetype,
                               self.servicename,
                               self.signalname,
                               self.defaultvalue,
                               self.echo,
                               self.send_echo_as_retained,
                               self.callback_on_change_only)


class Outputsignalinfo:
    """Object for storing configuration information about (some of the)
    outgoing MQTT messages, typically outgoing data (not outgoing commands).

    Arguments are described in the :meth:`.BaseFramework._register_outputsignal` method.

    TODO: .messagetype should be a property.

    """
    def __init__(self, messagetype, servicename, signalname, defaultvalue, send_as_retained):
        messagetype = str(messagetype).strip()
        if messagetype not in [constants.PREFIX_COMMANDAVAILABLE,
                               constants.PREFIX_DATAAVAILABLE,
                               constants.PREFIX_RESOURCEAVAILABLE,
                               constants.PREFIX_DATA,
                               constants.PREFIX_COMMAND]:
            raise ValueError("Trying to register an output signal, but the messagetype is wrong: {}".format(
                messagetype))

        self.messagetype = messagetype
        self.servicename = str(servicename).strip()
        self.signalname = str(signalname).strip()
        self.defaultvalue = defaultvalue
        self.send_as_retained = bool(send_as_retained)

    def __repr__(self):
        TEMPLATE = "OUT: '{}'-'{}'-'{}' Default: '{}' Retained: {}"
        return TEMPLATE.format(self.messagetype,
                               self.servicename,
                               self.signalname,
                               self.defaultvalue,
                               self.send_as_retained)
