#
# Utilities for the Secure Gateway concept architecture.
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

import collections
import itertools
import json
import logging
import textwrap

# JSON file key definitions #
JSON_KEY_ENTITIES_NODE_ROOT = 'entities'
JSON_KEY_ENTITIES_NODE_SIGNALS = 'signals'
JSON_KEY_ENTITIES_NODE_AGGREGATES = 'aggregates'
JSON_KEY_SIGNAL_CANNAME = 'canName'
JSON_KEY_SIGNAL_MULTIPLIER = 'canMultiplier'
JSON_KEY_MQTTNAME = 'mqttName'
JSON_KEY_MQTTTYPE = 'mqttType'
JSON_KEY_SENDCAN = 'toCan'
JSON_KEY_RECEIVECAN = 'fromCan'
JSON_KEY_ECHOMQTT = 'mqttEcho'

# MQTT wire key definitions
JSON_KEY_MQTT_VALUES = 'values'


class Converter:
    """Converter between CAN and MQTT.

    Does not store any CAN or MQTT messages.

    Arguments:
        can_config (can4python.Configuration)
        mqttfile_path (str or None): Full path to the configuration (JSON) file
        sort_json_keys (bool): Sort keys in resulting JSON strings.

    If the mqttfile_path argument not is given, it listens to all CAN signals (without name or value conversion).

    """

    def __init__(self, can_config, mqttfile_path=None, sort_json_keys=False):
        self.can_config = can_config
        self.sort_json_keys = sort_json_keys

        ## Read MQTT file ##
        if mqttfile_path is not None:
            translationinfos = translationfile_read(mqttfile_path)
        else:
            # Without an MQTT file, there are no aggregates.
            # Find all CAN signal names (for incoming CAN signals)
            translationinfos = [IndividualInfo(x) for x in self._get_incoming_cansignal_names()]
            if not translationinfos:
                logging.error("There are no CAN signalnames defined (for incoming frames). Quitting.")
                exit()

        ## Set frame_id for each translationinfo ##
        for x in translationinfos:
            self._precalculate_frame_id(x)

        ## Store look-up tables ##
            # MQTT to CAN: An IndividualInfo or AggregateInfo for each MQTT name
        self.mqttname_to_translationinfo = {}
        for x in translationinfos:
            if x.send_can:
                framedef = self.can_config.framedefinitions[x.frame_id]
                if framedef.is_outbound(self.can_config.ego_node_ids):
                    self.mqttname_to_translationinfo[x.mqtt_name] = x
                else:
                    TEMPLATE = "An incoming MQTT message '{}' would send on CAN frame id {}, " \
                               "but that frame is not outbound for ego node ids {}."
                    logging.error(TEMPLATE .format(x.mqtt_name,
                                                   x.frame_id,
                                                   sorted(list(self.can_config.ego_node_ids))))

            # CAN to MQTT: A list of IndividualInfo and AggregateInfo for each CAN frame
        self.canframeid_to_translationinfos = collections.defaultdict(list)
        for x in translationinfos:
            if x.receive_can:
                framedef = self.can_config.framedefinitions[x.frame_id]
                if not framedef.is_outbound(self.can_config.ego_node_ids):
                    self.canframeid_to_translationinfos[x.frame_id].append(x)
                else:
                    TEMPLATE = "An outgoing MQTT message '{}' would take its data from CAN frame id {}, " \
                               "but that frame is not inbound for ego node ids {}."
                    logging.error(TEMPLATE.format(x.mqtt_name,
                                                  x.frame_id,
                                                  sorted(list(self.can_config.ego_node_ids))))

    def __repr__(self):
        TEMPLATE = "Converter with {} incoming CAN frames and {} incoming MQTT commands. Ego node ids {}."
        return TEMPLATE.format(len(self.canframeid_to_translationinfos),
                               len(self.mqttname_to_translationinfo),
                               sorted(list(self.can_config.ego_node_ids)))

    def canframe_to_mqtt(self, frame):
        """
        Args:
            frame (can4python.CanFrame): Incoming CAN frame with data.

        Returns a list of MQTT messages, each represented as the tuple (MQTT signalname, MQTT payload).
        The payload is later converted to a string before sending.

        """
        messages = []
        can_signals = dict(frame.unpack(self.can_config.framedefinitions).items())
        infos = self.canframeid_to_translationinfos.get(frame.frame_id, [])

        for translationinfo in infos:
            if isinstance(translationinfo, IndividualInfo):
                payload = translationinfo.mqtt_type(can_signals[translationinfo.can_name]
                                                    * translationinfo.multiplier)
                messages.append((translationinfo.mqtt_name, payload))
            else:
                json_aggregate = {JSON_KEY_MQTT_VALUES: {}}
                for subsignalinfo in translationinfo.subsignals:
                    subsignalvalue = subsignalinfo.mqtt_type(can_signals[subsignalinfo.can_name]
                                                             * subsignalinfo.multiplier)
                    json_aggregate[JSON_KEY_MQTT_VALUES][subsignalinfo.mqtt_name] = subsignalvalue
                messages.append((translationinfo.mqtt_name,
                                 json.dumps(json_aggregate, sort_keys=self.sort_json_keys)))
        return messages

    def mqtt_to_cansignals(self, command_name, command_payload):
        """

        Args:
            command_name (str): Incoming MQTT command name (from the splitted MQTT topic)
            command_payload (str): Incoming MQTT payload

        Returns a dictionary with the signal values to send.
        The keys are the CAN signalnames (*str*), and the items are the CAN
        values (*numerical* or *None*). If the CAN value is *None* the default value is used.

        """
        signal_value_pairs = {}
        translationinfo = self.mqttname_to_translationinfo.get(command_name)

        if isinstance(translationinfo, IndividualInfo):
            signal_value_pairs[translationinfo.can_name] = float(command_payload)/translationinfo.multiplier
        elif isinstance(translationinfo, AggregateInfo):
            json_aggregate = json.loads(command_payload)
            for subsignalinfo in translationinfo.subsignals:
                signal_value_pairs[subsignalinfo.can_name] = float(json_aggregate[JSON_KEY_MQTT_VALUES][subsignalinfo.mqtt_name]) \
                                                             / subsignalinfo.multiplier

        return signal_value_pairs

    def get_definitions_incoming_mqtt_command(self):
        """Find the incoming MQTT command signalnames etc.

        Returns a list of dictionaries, each having the arguments for the resource.register_incoming_command() call.

        Note that the 'callback' keyword argument not is set in the output from this function,
        but needs to be set separately.

        """
        infos = set(self.mqttname_to_translationinfo.values())
        return [{'signalname': x.mqtt_name, 'echo': x.echo_mqtt} for x in infos]

    def get_definitions_outgoing_mqtt_data(self):
        """Find the outgoing MQTT data signalnames etc.

        Returns a list of dictionaries, each having the arguments for the resource.register_outgoing_data() call.

        """
        infos = set(itertools.chain.from_iterable(self.canframeid_to_translationinfos.values()))
        return [{'signalname': x.mqtt_name} for x in infos]

    def get_descriptive_ascii_art(self):
        """Return a string describing the conversion between CAN and MQTT."""

        infos_outgoing_mqtt = set(itertools.chain.from_iterable(
                self.canframeid_to_translationinfos.values()))
        infos_incoming_mqtt = set(self.mqttname_to_translationinfo.values())

        signalnames_incoming_mqtt = sorted(list(set([x.mqtt_name for x in infos_incoming_mqtt])))
        signalnames_outgoing_mqtt = sorted(list(set([x.mqtt_name for x in infos_outgoing_mqtt])))
        frameids_incoming_can = sorted(list(set([x.frame_id for x in infos_outgoing_mqtt])))
        frameids_outgoing_can = sorted(list(set([x.frame_id for x in infos_incoming_mqtt])))
        node_all_incoming_frameids = self._get_node_incoming_can_frameids()
        node_all_outgoing_frameids = self._get_node_outgoing_can_frameids()

        infos = list(infos_outgoing_mqtt | infos_incoming_mqtt)
        infos.sort(key=lambda x: (x.frame_id, isinstance(x, IndividualInfo), x.mqtt_name))

        text = "{!r} Summary:\n".format(self)
        text += "  Using incoming CAN frame IDs: {!r}. All incoming CAN frame IDs for this node: {!r}\n".format(
                frameids_incoming_can,
                node_all_incoming_frameids)
        text += "    Outgoing MQTT data names: {!r}\n".format(signalnames_outgoing_mqtt)
        text += "  Incoming MQTT command names: {!r}\n".format(signalnames_incoming_mqtt)
        text += "    Using outgoing CAN frame IDs: {!r}. All outgoing CAN frame IDs for this node: {!r}\n".format(
                frameids_outgoing_can,
                node_all_outgoing_frameids)
        text += "  Details: \n"
        for info in infos:
            infostring = "{!s}\n".format(info)  # multiline
            text += textwrap.indent(infostring, ' '*4)
        return text.strip()

    def _get_incoming_cansignal_names(self):
        """Return a list (str) of incoming cansignal names (according to the CAN configuration)."""
        can_signalnames_incoming = []
        for frame_id, framedef in self.can_config.framedefinitions.items():
            if not framedef.is_outbound(self.can_config.ego_node_ids):
                for sigdef in framedef.signaldefinitions:
                    can_signalnames_incoming.append(sigdef.signalname)
        return can_signalnames_incoming

    def _get_node_incoming_can_frameids(self):
        """Return a list (int) of all incoming CAN frame ids for this node, according to the CAN configutation."""
        result = []
        for frame_id, framedef in self.can_config.framedefinitions.items():
            if not framedef.is_outbound(self.can_config.ego_node_ids):
                result.append(frame_id)
        result.sort()
        return result

    def _get_node_outgoing_can_frameids(self):
        """Return a list (int) of all outgoing CAN frame ids for this node, according to the CAN configutation."""
        result = []
        for frame_id, framedef in self.can_config.framedefinitions.items():
            if framedef.is_outbound(self.can_config.ego_node_ids):
                result.append(frame_id)
        result.sort()
        return result

    def _get_canframe_id(self, can_signal_name):
        """Find the CAN frame id for a CAN signal name.

        Arguments:
            can_signal_name (str)

        Returns the frame_id (int).

        Raises:
            KeyError if the can_signal_name not is found.

        """
        for frame_id, framedef in self.can_config.framedefinitions.items():
            for sigdef in framedef.signaldefinitions:
                if sigdef.signalname == can_signal_name:
                    return frame_id
        raise KeyError("The signal name {} was not found in the CAN configuration".format(can_signal_name))

    def _precalculate_frame_id(self, translationinfo):
        """Set the frame_id field of the translationinfo.

        Does not return anything.

        """
        if isinstance(translationinfo, IndividualInfo):
            translationinfo.frame_id = self._get_canframe_id(translationinfo.can_name)
        else:
            frame_ids = set()
            for subsignalinfo in translationinfo.subsignals:
                subsignalinfo.frame_id = self._get_canframe_id(subsignalinfo.can_name)
                frame_ids.add(subsignalinfo.frame_id)
            if len(frame_ids) != 1:
                raise ValueError("An aggregate has signals from several (or none) CAN frames: {!r}".format(
                        translationinfo))
            translationinfo.frame_id = frame_ids.pop()


class IndividualInfo:
    """A class for describing the translation between a CAN signal and an individual MQTT signal.

    Attributes:
      can_name (str): Signal name in the KCD file for CAN
      mqtt_name (str or None): Signal name on MQTT (part of the topic). Defaults to None (use
                        same name on MQTT as on CAN.
      mqtt_type (type): Conversion function used to convert the value to correct type inside the MQTT message
                        (which itself is a string). Defaults to float.
      send_can (bool): Whether the signal should be sent to CAN. Defaults to False.
      echo_mqtt (bool): Whether the incoming MQTT message should be echoed back. Defaults to False.
      receive_can (bool): Whether the signal should be sent to MQTT. Defaults to True.
      multiplier (float): Multiplier when converting a CAN signal to an MQTT signal. In the other
                          direction is 1/multiplier used. Defaults to 1.0.
      frame_id (int or None): The id of the CAN frame the signal is using


    """
    def __init__(self, can_name, mqtt_name=None, send_can=False, echo_mqtt=False,
                 receive_can=True, multiplier=1.0, frame_id=None, mqtt_type=float):
        self.can_name = str(can_name)
        self.receive_can = bool(receive_can)
        self.send_can = bool(send_can)
        self.frame_id = frame_id
        if mqtt_name is None:
            self.mqtt_name = can_name
        else:
            self.mqtt_name = str(mqtt_name)
        self.echo_mqtt = bool(echo_mqtt)
        self.multiplier = float(multiplier)
        self.mqtt_type = mqtt_type

    def __repr__(self):
        text = "Translationinfo {}={!r} CAN frame ID={!r} {}={!r} {}={!r} {}={!r} {}={!r} {}={!r} {}={!r}".format(
            JSON_KEY_SIGNAL_CANNAME, self.can_name,
            self.frame_id,
            JSON_KEY_MQTTNAME, self.mqtt_name,
            JSON_KEY_SENDCAN, self.send_can,
            JSON_KEY_RECEIVECAN, self.receive_can,
            JSON_KEY_ECHOMQTT, self.echo_mqtt,
            JSON_KEY_MQTTTYPE, self.mqtt_type,
            JSON_KEY_SIGNAL_MULTIPLIER, self.multiplier)
        return text


class AggregateInfo:
    """A class for describing the translation between a CAN signal aggregate and a MQTT signal.

    All CAN signals must be located in the same CAN frame. The send_can and receive_can fields
    of the subsignals are not used.

    Attributes:
      mqtt_name (str): Signal name on MQTT (part of the topic).
      send_can (bool): Whether the subsignals should be sent to CAN. Defaults to False.
      receive_can (bool): Whether the aggregate should be sent to MQTT. Defaults to True.
      echo_mqtt (bool): Whether the incoming MQTT message should be echoed back. Defaults to False.
      frame_id (int or None): The id of the CAN frame the aggregate data is using
      subsignals (list of IndividualInfo): Definitions for the signals within the aggregate

    """
    def __init__(self, mqtt_name, send_can=False, receive_can=True, echo_mqtt=False, frame_id=None):
        self.mqtt_name = str(mqtt_name)
        self.send_can = bool(send_can)
        self.receive_can = bool(receive_can)
        self.echo_mqtt = bool(echo_mqtt)
        self.frame_id = frame_id
        self.subsignals = []

    def __repr__(self, long_text=True, newline=False):
        text = "AggregateInfo {}={!r} CAN frame ID={!r} {}={!r} {}={!r} Contains {} signals".format(
                JSON_KEY_MQTTNAME, self.mqtt_name,
                self.frame_id,
                JSON_KEY_RECEIVECAN, self.receive_can,
                JSON_KEY_SENDCAN, self.send_can,
                len(self.subsignals))
        if long_text:
            if newline:
                text += ":\n"
                for sig in self.subsignals:
                    text += "  {!r} \n".format(sig)
            else:
                text += ": {!r}".format(self.subsignals)
        return text.strip()

    def __str__(self):
        return self.__repr__(True, True).strip()


def translationfile_read(filename):
    """Read a translation file, having the CAN signal names and the MQTT signal names etc.

    Args:
        filename (str): Full path to the input file.

    The input file should be a valid JSON file, having a top object with the name 'entities'
    and the objects 'aggregates' and 'signals'. Item inside 'signals' is a list
    of signaldefinition objects. Item in aggregates are several 'signals'.

    See the sgframework documentation for a more detailed discussion on the file format.

    Returns a single list containing AggregateInfo and IndividualInfo. The order in the list is not relevant.

    """
    # Read JSON file #
    logging.info("Reading JSON file: {}".format(filename))
    with open(filename, 'r') as json_file:
        try:
            json_root = json.load(json_file)
        except ValueError:
            raise ValueError("The file {} seems to be invalid JSON data.".format(filename))

    # Parse top level node #
    try:
        json_entities = json_root[JSON_KEY_ENTITIES_NODE_ROOT]
    except KeyError:
        raise ValueError("There must be a '{}' JSON object as top root in the file: {}".format(
                         JSON_KEY_ENTITIES_NODE_ROOT, filename))

    # Parse signal level node #
    json_signals = json_entities.get(JSON_KEY_ENTITIES_NODE_SIGNALS, [])
    if type(json_signals) != list:
        raise ValueError("The '{}' JSON object as top root must be a list. File: {}".format(
                         JSON_KEY_ENTITIES_NODE_SIGNALS, filename))
    translationtable = []
    for json_signal in json_signals:
        translationtable.append(parse_signal(json_signal, filename))

    # Parse aggregate level node #
    json_aggregates = json_entities.get(JSON_KEY_ENTITIES_NODE_AGGREGATES, [])
    if type(json_aggregates) != list:
        raise ValueError("The '{}' JSON object in the '{}' node must be a list. File: {}".format(
                         JSON_KEY_ENTITIES_NODE_AGGREGATES, JSON_KEY_ENTITIES_NODE_ROOT, filename))
    for json_aggregate in json_aggregates:
        translationtable.append(parse_aggregate(json_aggregate, filename))

    return translationtable


def parse_signal(json_signal, filename):
    """Parse signal information from a JSON dict, and convert to an instance of IndividualInfo.

    Args:
        json_signal: a dict from a (part of a) parsed JSON file
        filename (str): Filename (for use in error messages)

    Returns:
        An IndividualInfo instance

    """
    try:
        can_name = json_signal[JSON_KEY_SIGNAL_CANNAME]
    except KeyError:
        raise ValueError("Each signal must have the '{}' key defined. File: {}".format(
                         JSON_KEY_SIGNAL_CANNAME, filename))
    mqtt_name = json_signal.get(JSON_KEY_MQTTNAME)
    try:
        multiplier = float(json_signal.get(JSON_KEY_SIGNAL_MULTIPLIER, "1"))
        _ = 1 / multiplier
    except ValueError:
        raise ValueError("The key '{}' must have a numerical field. File: {}".format(
                         JSON_KEY_SIGNAL_MULTIPLIER, filename))
    except ZeroDivisionError:
        raise ValueError("The key '{}' must not be zero. File: {}".format(
                JSON_KEY_SIGNAL_MULTIPLIER, filename))
    send_can = is_true(json_signal.get(JSON_KEY_SENDCAN, False))
    receive_can = is_true(json_signal.get(JSON_KEY_RECEIVECAN, True))
    echo_mqtt = is_true(json_signal.get(JSON_KEY_ECHOMQTT, False))
    type_in_file = json_signal.get(JSON_KEY_MQTTTYPE, 'float')
    if type_in_file == 'float':
        mqtt_type = float
    elif type_in_file == 'int':
        mqtt_type = int
    else:
        raise ValueError("Wrong mqttType given for signal {}. File: {}".format(json_signal, filename))

    return IndividualInfo(can_name, mqtt_name, send_can, echo_mqtt, receive_can, multiplier, mqtt_type=mqtt_type)


def parse_aggregate(json_aggregate, filename):
    """Parse signal information from a JSON dict, and convert to an instance of AggregateInfo.

    Args:
        json_aggregate: a dict from a (part of a) parsed JSON file
        filename (str): Filename (for use in error messages)

    Returns:
        An AggregateInfo instance

    """
    try:
        aggregate_mqttname = json_aggregate[JSON_KEY_MQTTNAME]
    except KeyError:
        raise ValueError("Each '{}' must have a '{}'. File: {}".format(
                JSON_KEY_ENTITIES_NODE_AGGREGATES, JSON_KEY_MQTTNAME, filename))

    aggregate_signals = []
    try:
        json_ag_signals = json_aggregate[JSON_KEY_ENTITIES_NODE_SIGNALS]
    except KeyError:
        raise ValueError("The '{}' group is expecting a '{}' group. File {}".format(
                JSON_KEY_ENTITIES_NODE_AGGREGATES, JSON_KEY_ENTITIES_NODE_SIGNALS, filename))
    if type(json_ag_signals) != list:
        raise ValueError("The '{}' JSON object in the '{}' node must be a list. File {}".format(
                JSON_KEY_ENTITIES_NODE_SIGNALS, JSON_KEY_ENTITIES_NODE_AGGREGATES, filename))
    for json_ag_signal in json_ag_signals:
        aggregate_signals.append(parse_signal(json_ag_signal, filename))

    send_can = is_true(json_aggregate.get(JSON_KEY_SENDCAN, False))
    receive_can = is_true(json_aggregate.get(JSON_KEY_RECEIVECAN, True))

    aggregateinfo = AggregateInfo(aggregate_mqttname, send_can=send_can, receive_can=receive_can)
    aggregateinfo.subsignals = aggregate_signals
    return aggregateinfo


########################
## Helper objects etc ##
########################

def is_true(obj):
    VALID_STRINGS_FOR_TRUE = ["True", "true"]

    if type(obj) == bool:
        return obj
    if type(obj) != str:
        raise TypeError("The comparison object is of wrong type: {}. Object: {!r}".format(type(obj), obj))
    if obj in VALID_STRINGS_FOR_TRUE:
        return True
    return False
