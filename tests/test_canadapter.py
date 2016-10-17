#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_canadapter
----------------------------------

Tests for the canadapter


"""

import collections
import io
import json
import logging
import os.path
import os
import signal
import subprocess
import sys
import time
import unittest

assert sys.version_info >= (3, 3, 0), "Python version 3.3 or later required!"
import unittest.mock

THIS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PARENT_DIRECTORY = os.path.dirname(THIS_DIRECTORY)
SOURCE_DIRECTORY = os.path.join(PARENT_DIRECTORY, 'scripts/')
sys.path.append(SOURCE_DIRECTORY)

import can4python as can

import canadapter
import canadapterlib

VIRTUAL_CAN_BUS_NAME = "vcan0"
NONEXISTING_CAN_BUS_NAME = "can25"

MQTT_TOPICS_TO_DELETE = [
    "commandavailable/climateservice/aircondition",
    "dataavailable/climateservice/vehiclespeed",
    "dataavailable/climateservice/enginespeed",
    "dataavailable/climateservice/actualindoortemperature",
    "dataavailable/climateservice/aircondition",
    "resourceavailable/climateservice/presence",
    "commandavailable/canadapter/no_interesting",
    "commandavailable/canadapter/ADAS_Pos2",
    "commandavailable/canadapter/aircondition",
    "commandavailable/canadapter/ADAS_Posn",
    "commandavailable/canadapter/ADAS_Seg",
    "dataavailable/canadapter/ADAS_Seg",
    "dataavailable/canadapter/ADAS_Pos2",
    "dataavailable/canadapter/ADAS_Posn",
    "dataavailable/canadapter/ADAS_Posn_1",
    "dataavailable/canadapter/ADAS_Posn_2",
    "dataavailable/canadapter/ADAS_Posn_MsgType",
    "dataavailable/canadapter/ADAS_Posn_Offset",
    "dataavailable/canadapter/ADAS_ProfShort_CtrlPoint",
    "dataavailable/canadapter/vehiclespeed",
    "dataavailable/canadapter/no_interesting",
    "dataavailable/canadapter/enginespeed",
    "dataavailable/canadapter/actualindoortemperature",
    "dataavailable/canadapter/indoortemperature",
    "dataavailable/canadapter/aircondition",
    "dataavailable/canadapter/acstatus",
    "resourceavailable/canadapter/presence",
    ]


class TestConverter(unittest.TestCase):

    def test_converter_individual(self):
        can_config = can.FilehandlerKcd.read('examples/configfilesForCanadapter/climateservice_cansignals.kcd', None)
        can_config.ego_node_ids = ["1"]
        print(can_config.get_descriptive_ascii_art())
        converter = canadapterlib.Converter(can_config, 'examples/configfilesForCanadapter/climateservice_mqttsignals.json')
        print(converter.get_descriptive_ascii_art())

        # REGISTER INCOMING COMMANDS
        commands = converter.get_definitions_incoming_mqtt_command()
        print("INCOMING MQTT COMMAND DEFINITIONS", commands)
        self.assertEqual(commands[0]['signalname'], 'aircondition')

        # REGISTER OUTGOING DATA
        data = converter.get_definitions_outgoing_mqtt_data()
        data.sort(key=lambda x: x['signalname'])
        print("OUTGOING MQTT DATA DEFINITIONS", data)
        self.assertEqual(data[0]['signalname'], 'actualindoortemperature')
        self.assertEqual(data[1]['signalname'], 'enginespeed')
        self.assertEqual(data[2]['signalname'], 'vehiclespeed')

        print("TO CAN", converter.mqttname_to_translationinfo)
        print("TO MQTT", converter.canframeid_to_translationinfos)

        # TO CAN
        signals = converter.mqtt_to_cansignals('aircondition', '0')
        print("RESULTING CAN", signals)
        self.assertIn('acstatus', signals)
        self.assertAlmostEqual(signals['acstatus'], 0)

        signals = converter.mqtt_to_cansignals('aircondition', '1')
        print("RESULTING CAN", signals)
        self.assertIn('acstatus', signals)
        self.assertAlmostEqual(signals['acstatus'], 1)

        # TO MQTT
        frame = can.canframe.CanFrame(9, b'\x03\x31\x00\x00\x00\x00\x00\x00')
        messages = converter.canframe_to_mqtt(frame)
        print("RESULTING MQTT", messages)
        self.assertIn(messages[0][0], 'actualindoortemperature')
        self.assertAlmostEqual(messages[0][1], 31.7)

        frame = can.canframe.CanFrame(8, b'\x14\xAD\x1E\x10\x00\x00\x00\x00')
        messages = converter.canframe_to_mqtt(frame)
        print("RESULTING MQTT", messages)
        messages.sort(key=lambda x: x[0])
        self.assertIn(messages[0][0], 'enginespeed')
        self.assertAlmostEqual(messages[0][1], 1924)
        self.assertIn(messages[1][0], 'vehiclespeed')
        self.assertAlmostEqual(messages[1][1], 52.93)

    def test_converter_aggregate(self):
        logging.basicConfig(level=logging.DEBUG)
        can_config = can.FilehandlerKcd.read('examples/configfilesForCanadapter/ADASIS_cansignals.kcd', None)
        can_config.ego_node_ids = ["1"]
        print(can_config.get_descriptive_ascii_art())
        converter = canadapterlib.Converter(can_config, 'examples/configfilesForCanadapter/ADASIS_mqttsignals.json')
        print(converter.get_descriptive_ascii_art())

        # REGISTER INCOMING COMMANDS
        commands = converter.get_definitions_incoming_mqtt_command()
        print("INCOMING MQTT COMMAND DEFINITIONS", commands)
        self.assertEqual(commands[0]['signalname'], 'ADAS_Seg')

        # REGISTER OUTGOING DATA
        data = converter.get_definitions_outgoing_mqtt_data()
        data.sort(key=lambda x: x['signalname'])
        print("OUTGOING MQTT DATA DEFINITIONS", data)
        self.assertEqual(data[0]['signalname'], 'ADAS_Posn_1')
        self.assertEqual(data[1]['signalname'], 'ADAS_Posn_2')
        self.assertEqual(data[2]['signalname'], 'ADAS_Posn_MsgType')
        self.assertEqual(data[3]['signalname'], 'ADAS_Posn_Offset')
        self.assertEqual(data[4]['signalname'], 'ADAS_ProfShort_CtrlPoint')

        # TO CAN
        print("\nSENDING MQTT ...")
        signals = converter.mqtt_to_cansignals('ADAS_Seg',
                                               '{"values": {"ADAS_Seg_MsgType": 1.0, '
                                                '"ADAS_Seg_Offset": 2.0, '
                                                '"ADAS_Seg_CycCnt": 3.0, '
                                                '"ADAS_Seg_EffSpdLmt": 4.0, '
                                                '"ADAS_Seg_EffSpdLmtType": 5.0}}')

        print("RESULTING CAN SIGNALS", signals)
        self.assertAlmostEqual(signals['ADAS_Seg_MsgType'], 1.0)
        self.assertAlmostEqual(signals['ADAS_Seg_Offset'], 2.0)
        self.assertAlmostEqual(signals['ADAS_Seg_CycCnt'], 3.0)
        self.assertAlmostEqual(signals['ADAS_Seg_EffSpdLmt'], 4.0)
        self.assertAlmostEqual(signals['ADAS_Seg_EffSpdLmtType'], 5.0)

        # TO MQTT
        frame = can.canframe.CanFrame(0x100, b'\x03\x31\x00\x00\x00\x00\x00\x00')
        print("\nSENDING CAN FRAME: {}".format(frame))
        messages = converter.canframe_to_mqtt(frame)
        messages.sort(key=lambda x: x[0])
        print("RESULTING MQTT MESSAGES", messages)

        self.assertEqual(messages[0][0], 'ADAS_Posn_1')
        j = json.loads(messages[0][1])
        self.assertEqual(j['values']['ADAS_Posn_CycCnt'], 0)
        self.assertEqual(j['values']['ADAS_Posn_MsgType'], 0)
        self.assertAlmostEqual(j['values']['ADAS_Posn_Spd'], 0.0)
        self.assertAlmostEqual(j['values']['Position_offset'], 817.0)

        self.assertEqual(messages[1][0], 'ADAS_Posn_2')
        j = json.loads(messages[1][1])
        self.assertAlmostEqual(j['values']['ADAS_Posn_PosProbb'], 0.0)
        self.assertAlmostEqual(j['values']['ADAS_Posn_CurLane'], 0.0)

        self.assertEqual(messages[2][0], 'ADAS_Posn_MsgType')
        self.assertEqual(messages[2][1], 0)

        self.assertEqual(messages[3][0], 'ADAS_Posn_Offset')
        self.assertAlmostEqual(messages[3][1], 817.0)

        frame = can.canframe.CanFrame(0x100, b'\x00\x00\x00\x00\x00\x00\x00\x00')
        print("\nSENDING CAN FRAME: {}".format(frame))
        messages = converter.canframe_to_mqtt(frame)
        messages.sort(key=lambda x: x[0])
        print("RESULTING MQTT MESSAGES", messages)

        self.assertEqual(messages[0][0], 'ADAS_Posn_1')
        j = json.loads(messages[0][1])
        self.assertEqual(j['values']['ADAS_Posn_CycCnt'], 0)
        self.assertEqual(j['values']['ADAS_Posn_MsgType'], 0)
        self.assertAlmostEqual(j['values']['ADAS_Posn_Spd'], 0.0)
        self.assertAlmostEqual(j['values']['Position_offset'], 0.0)

        frame = can.canframe.CanFrame(0x100, b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF')
        print("\nSENDING CAN FRAME: {}".format(frame))
        messages = converter.canframe_to_mqtt(frame)
        messages.sort(key=lambda x: x[0])
        print("RESULTING MQTT MESSAGES", messages)

        self.assertEqual(messages[0][0], 'ADAS_Posn_1')
        j = json.loads(messages[0][1])
        self.assertEqual(j['values']['ADAS_Posn_CycCnt'], 3)
        self.assertEqual(j['values']['ADAS_Posn_MsgType'], 7)
        self.assertAlmostEqual(j['values']['ADAS_Posn_Spd'], 511.0)
        self.assertAlmostEqual(j['values']['Position_offset'], 8191.0)

        frame = can.canframe.CanFrame(0x104, b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF')
        print("\nSENDING CAN FRAME: {}".format(frame))
        messages = converter.canframe_to_mqtt(frame)
        messages.sort(key=lambda x: x[0])
        print("RESULTING MQTT MESSAGES", messages)

        self.assertEqual(messages[0][0], 'ADAS_ProfShort_CtrlPoint')
        self.assertEqual(messages[0][1], 1)


class TestCanAdapter(unittest.TestCase):

    OUTPUT_FILE_CANDUMPER = 'temporary-candump.txt'
    OUTPUT_FILE_SUBSCRIBER = 'temporary-sub.txt'

    def setUp(self):
        self.environment = os.environ.copy()
        self.environment["COVERAGE_PROCESS_START"] = os.path.join(THIS_DIRECTORY, "coveragerc")

    def tearDown(self):
        # Remove temporary files
        try:
            os.remove(self.OUTPUT_FILE_CANDUMPER)
        except FileNotFoundError:
            pass
        try:
            os.remove(self.OUTPUT_FILE_SUBSCRIBER)
        except FileNotFoundError:
            pass

        # Delete persistent MQTT messages
        for topic in MQTT_TOPICS_TO_DELETE:
            pub = subprocess.Popen(['mosquitto_pub', '-t', topic, '-r', '-n'])
            time.sleep(0.2)
            pub.terminate()

    def testConstructor(self):
        with unittest.mock.patch('sys.argv', ['scriptname',
                                              'examples/configfilesForCanadapter/climateservice_cansignals.kcd',
                                              '-listentoallcan']):
            resource = canadapter.init_canadapter()
        time.sleep(0.5)
        resource.stop()

    def testConstructorVerbose(self):
        with unittest.mock.patch('sys.argv', ['scriptname',
                                              'examples/configfilesForCanadapter/climateservice_cansignals.kcd',
                                              '-listentoallcan',
                                              '-v']):
            resource = canadapter.init_canadapter()
        time.sleep(0.5)
        resource.stop()

    def testConstructorVerbose2(self):
        with unittest.mock.patch('sys.argv', ['scriptname',
                                              'examples/configfilesForCanadapter/climateservice_cansignals.kcd',
                                              '-listentoallcan',
                                              '-vv']):
            resource = canadapter.init_canadapter()
        time.sleep(0.5)
        resource.stop()

    def testConstructorJSON(self):
        with unittest.mock.patch('sys.argv', ['scriptname',
                                              'examples/configfilesForCanadapter/climateservice_cansignals.kcd',
                                              '-mqttfile',
                                              'examples/configfilesForCanadapter/climateservice_mqttsignals.json']):
            resource = canadapter.init_canadapter()
        time.sleep(0.5)
        resource.stop()

    def testConstructorWrongArguments(self):
        wrong_arguments = [['scriptname', '-j'],
                           ['scriptname', 'examples/configfilesForCanadapter/climateservice_cansignals.kcd', '-listentoallcan', '-k', '-10'],
                           ['scriptname', 'examples/configfilesForCanadapter/climateservice_cansignals.kcd', '-listentoallcan', '-t', '-10'],
                           ['scriptname', 'examples/configfilesForCanadapter/climateservice_cansignals.kcd', '-listentoallcan', '-t', '100000'],
                           ['scriptname', 'examples/configfilesForCanadapter/climateservice_cansignals.kcd'],
                           ['scriptname', '-mode', 'commandline'],
                           ]

        for arguments in wrong_arguments:
            with unittest.mock.patch('sys.argv', arguments):
                with self.assertRaises(SystemExit) as context_manager:
                    canadapter.init_canadapter()
                self.assertEqual(context_manager.exception.code, 2)  # 'Incorrect usage'

    def testConstructorWrongCanInterface(self):
        with unittest.mock.patch('sys.argv', ['scriptname',
                                              'examples/configfilesForCanadapter/climateservice_cansignals.kcd',
                                              '-listentoallcan',
                                              '-i',
                                              NONEXISTING_CAN_BUS_NAME]):
            with self.assertRaises(can.CanException) as context_manager:
                canadapter.init_canadapter()

    def testHelpText(self):
        original_stdout = sys.stdout
        try:
            temporary_stdout = io.StringIO()  # Redirect stdout
            sys.stdout = temporary_stdout
            with unittest.mock.patch('sys.argv', ['scriptname', '-h']):
                with self.assertRaises(SystemExit) as context_manager:
                    canadapter.init_canadapter()
                self.assertEqual(context_manager.exception.code, 0)  # 'OK exit'
            result = temporary_stdout.getvalue()
        finally:
            sys.stdout = original_stdout
        self.assertIn("usage:", result)
        self.assertIn("CAN interface name. Defaults to ", result)

    def testLoopIndividualsignals(self):
        with open(self.OUTPUT_FILE_CANDUMPER, 'w') as candumper_outputfile, \
             open(self.OUTPUT_FILE_SUBSCRIBER, 'w') as subscriber_outputfile:
            candumper = subprocess.Popen(['candump', VIRTUAL_CAN_BUS_NAME],
                                         stdout=candumper_outputfile,
                                         stderr=subprocess.STDOUT)

            subcriber = subprocess.Popen(['mosquitto_sub', '-v', '-t', '+/climateservice/+'],
                                         stdout=subscriber_outputfile,
                                         stderr=subprocess.STDOUT)

            canadapter_process = subprocess.Popen(['python3',
                                                   'scripts/canadapter',
                                                   'examples/configfilesForCanadapter/climateservice_cansignals.kcd',
                                                   '-mqttfile',
                                                   'examples/configfilesForCanadapter/climateservice_mqttsignals.json',
                                                   '-mqttname',
                                                   'climateservice',
                                                   '-vv'
                                                   ],
                                                  env=self.environment)
            time.sleep(5)

            # Send MQTT commands to the canadapter
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'command/climateservice/aircondition', '-m', '1'])
            time.sleep(1)
            pub1.terminate()
            pub2 = subprocess.Popen(['mosquitto_pub', '-t', 'command/climateservice/aircondition', '-m', '0'])
            time.sleep(3)
            pub2.terminate()

            # Send CAN frames to the canadapter
            pub1 = subprocess.Popen(['cansend', VIRTUAL_CAN_BUS_NAME, '009#0331000000000000'])
            time.sleep(1)
            pub1.terminate()
            pub2 = subprocess.Popen(['cansend', VIRTUAL_CAN_BUS_NAME, '008#14AD1E1000000000'])
            time.sleep(1)
            pub2.terminate()

            # Send wrong CAN frames to the canadapter
            pub3 = subprocess.Popen(['cansend', VIRTUAL_CAN_BUS_NAME, '009#03'])
            time.sleep(1)
            pub3.terminate()

            # Terminate, and flush files
            time.sleep(3)
            canadapter_process.send_signal(signal.SIGINT)
            time.sleep(1)
            canadapter_process.terminate()
            time.sleep(1)
            canadapter_process.kill()
            time.sleep(3)  # Wait for last will to be sent

            candumper.kill()
            subcriber.kill()
            time.sleep(0.2)
            candumper_outputfile.flush()
            os.fsync(candumper_outputfile.fileno())
            subscriber_outputfile.flush()
            os.fsync(subscriber_outputfile.fileno())

        # Verify that the canadapter has sent proper MQTT messages
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'r') as subscriber_outputfile:
            text = ' '.join(subscriber_outputfile.readlines())
            self.assertIn("resourceavailable/climateservice/presence True", text)
            self.assertIn("dataavailable/climateservice/vehiclespeed True", text)
            self.assertIn("dataavailable/climateservice/enginespeed True", text)
            self.assertIn("dataavailable/climateservice/actualindoortemperature True", text)
            self.assertIn("dataavailable/climateservice/aircondition True", text)
            self.assertIn("commandavailable/climateservice/aircondition True", text)
            self.assertIn("data/climateservice/aircondition 1", text)
            self.assertIn("data/climateservice/aircondition 0", text)
            self.assertIn("data/climateservice/actualindoortemperature 31", text)
            self.assertIn("data/climateservice/enginespeed 1924", text)
            self.assertIn("data/climateservice/vehiclespeed 52", text)
            self.assertIn("resourceavailable/climateservice/presence False", text)

        # Verify that the canadapter has sent proper CAN frames
        with open(self.OUTPUT_FILE_CANDUMPER, 'r') as candumper_outputfile:
            text = ' '.join(candumper_outputfile.readlines())
            self.assertIn("007   [8]  80 00 00 00 00 00 00 00", text)
            self.assertIn("007   [8]  00 00 00 00 00 00 00 00", text)

    def testLoopThrottleCanFrames(self):
        NUMBER_OF_INCOMING_CAN_FRAMES = 50
        THROTTLING_TIME = 1000  # milliseconds
        CAN_FRAME_INTERVAL = 0.2  # seconds
        ERROR_MARGIN = 3  # number of sent MQTT messages

        assert THROTTLING_TIME > CAN_FRAME_INTERVAL * 1000

        with open(self.OUTPUT_FILE_CANDUMPER, 'w') as candumper_outputfile, \
                open(self.OUTPUT_FILE_SUBSCRIBER, 'w') as subscriber_outputfile:
            candumper = subprocess.Popen(['candump', VIRTUAL_CAN_BUS_NAME],
                                         stdout=candumper_outputfile,
                                         stderr=subprocess.STDOUT)

            subcriber = subprocess.Popen(['mosquitto_sub', '-v', '-t', '+/climateservice/+'],
                                         stdout=subscriber_outputfile,
                                         stderr=subprocess.STDOUT)

            canadapter_process = subprocess.Popen(['python3',
                                                   'scripts/canadapter',
                                                   'examples/configfilesForCanadapter/climateservice_cansignals.kcd',
                                                   '-mqttfile',
                                                   'examples/configfilesForCanadapter/climateservice_mqttsignals.json',
                                                   '-mqttname',
                                                   'climateservice',
                                                   '-vv',
                                                   '-t', str(THROTTLING_TIME)
                                                   ],
                                                  env=self.environment)
            time.sleep(5)

            # Send CAN frames to the canadapter
            for i in range(NUMBER_OF_INCOMING_CAN_FRAMES):
                pub1 = subprocess.Popen(['cansend', VIRTUAL_CAN_BUS_NAME, '008#14AD1E1000000000'])
                time.sleep(CAN_FRAME_INTERVAL)
                pub1.terminate()

            # Terminate, and flush files
            time.sleep(3)
            canadapter_process.send_signal(signal.SIGINT)
            time.sleep(1)
            canadapter_process.terminate()
            time.sleep(1)
            canadapter_process.kill()
            time.sleep(3)  # Wait for last will to be sent

            candumper.kill()
            subcriber.kill()
            time.sleep(0.2)
            candumper_outputfile.flush()
            os.fsync(candumper_outputfile.fileno())
            subscriber_outputfile.flush()
            os.fsync(subscriber_outputfile.fileno())

        # Verify that the total number of  CAN frames
        with open(self.OUTPUT_FILE_CANDUMPER, 'r') as candumper_outputfile:
            can_lines = candumper_outputfile.readlines()
        number_of_can_frames = 0
        for line in can_lines:
            if line.startswith("  "+VIRTUAL_CAN_BUS_NAME+"  008   [8]  "):
                number_of_can_frames += 1
        self.assertEqual(number_of_can_frames, NUMBER_OF_INCOMING_CAN_FRAMES)

        # Calculate approximate number of sent MQTT messages
        can_send_time = NUMBER_OF_INCOMING_CAN_FRAMES * CAN_FRAME_INTERVAL  # seconds
        approx_number_of_vehiclespeed_messages = can_send_time * 1000 / THROTTLING_TIME

        # Verify that the canadapter has sent correct number of MQTT messages (throttling)
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'r') as subscriber_outputfile:
            mqtt_lines = subscriber_outputfile.readlines()
        number_of_vehiclespeed_mqtt_messages = 0
        for line in mqtt_lines:
            if line.startswith("data/climateservice/vehiclespeed"):
                number_of_vehiclespeed_mqtt_messages += 1
        self.assertLessEqual(number_of_vehiclespeed_mqtt_messages, approx_number_of_vehiclespeed_messages + ERROR_MARGIN)
        self.assertGreaterEqual(number_of_vehiclespeed_mqtt_messages, approx_number_of_vehiclespeed_messages - ERROR_MARGIN)

    def testLoopAggregates(self):
        with open(self.OUTPUT_FILE_CANDUMPER, 'w') as candumper_outputfile, \
             open(self.OUTPUT_FILE_SUBSCRIBER, 'w') as subscriber_outputfile:
            candumper = subprocess.Popen(['candump', VIRTUAL_CAN_BUS_NAME],
                                         stdout=candumper_outputfile,
                                         stderr=subprocess.STDOUT)

            subcriber = subprocess.Popen(['mosquitto_sub', '-v', '-t', '+/canadapter/+'],
                                         stdout=subscriber_outputfile,
                                         stderr=subprocess.STDOUT)

            canadapter_process = subprocess.Popen(['python3', 'scripts/canadapter',
                                                   'examples/configfilesForCanadapter/ADASIS_cansignals.kcd',
                                                   '-mqttfile', 'examples/configfilesForCanadapter/ADASIS_mqttsignals.json',
                                                   '-mqttname', 'canadapter',
                                                   '-vv'],
                                                  env=self.environment)
            time.sleep(3)

            # Send MQTT commands to the canadapter
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'command/canadapter/ADAS_Seg', '-m',
                                     '{"values": {"ADAS_Seg_MsgType": 1.0, '
                                                 '"ADAS_Seg_Offset": 2.0, '
                                                 '"ADAS_Seg_CycCnt": 3.0, '
                                                 '"ADAS_Seg_EffSpdLmt": 4.0, '
                                                 '"ADAS_Seg_EffSpdLmtType": 5.0}}'])
            time.sleep(3)
            pub1.terminate()

            # Send CAN frames to the canadapter
            pub1 = subprocess.Popen(['cansend', VIRTUAL_CAN_BUS_NAME, '100#0331000000000000'])
            time.sleep(1)
            pub1.terminate()
            pub2 = subprocess.Popen(['cansend', VIRTUAL_CAN_BUS_NAME, '104#FFFFFFFFFFFFFFFF'])
            time.sleep(1)
            pub2.terminate()
            pub3 = subprocess.Popen(['cansend', VIRTUAL_CAN_BUS_NAME, '100#FFFFFFFFFFFFFFFF'])
            time.sleep(1)
            pub3.terminate()

            # Terminate, and flush files
            time.sleep(3)
            canadapter_process.send_signal(signal.SIGINT)
            time.sleep(1)
            canadapter_process.terminate()
            time.sleep(1)
            canadapter_process.kill()
            time.sleep(3)  # Wait for the last will to be sent

            candumper.kill()
            subcriber.kill()
            time.sleep(0.2)
            candumper_outputfile.flush()
            os.fsync(candumper_outputfile.fileno())
            subscriber_outputfile.flush()
            os.fsync(subscriber_outputfile.fileno())

        # Verify that the canadapter has sent proper CAN frames
        with open(self.OUTPUT_FILE_CANDUMPER, 'r') as candumper_outputfile:
            text = ' '.join(candumper_outputfile.readlines())
            print("CAN:\n", text)
            self.assertIn("101   [8]  20 02 C0 00 00 00 25 00", text)

        # Verify that the canadapter has sent proper MQTT messages
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'r') as subscriber_outputfile:
            text = ' '.join(subscriber_outputfile.readlines())
            rows = text.splitlines()
            messages = collections.defaultdict(list)
            print("MQTT:")
            for row in rows:
                topic, payload = row.strip().split(' ', maxsplit=1)
                print("T {:42} P {}".format(topic, payload))
                messages[topic].append(payload)

            self.assertEqual(messages['resourceavailable/canadapter/presence'], ['True', 'False'])
            self.assertEqual(messages['dataavailable/canadapter/ADAS_Posn_1'][0], 'True')
            self.assertEqual(messages['dataavailable/canadapter/ADAS_Posn_2'][0], 'True')
            self.assertEqual(messages['dataavailable/canadapter/ADAS_Posn_Offset'][0], 'True')
            self.assertEqual(messages['dataavailable/canadapter/ADAS_Posn_MsgType'][0], 'True')
            self.assertEqual(messages['dataavailable/canadapter/ADAS_ProfShort_CtrlPoint'][0], 'True')
            self.assertEqual(messages['commandavailable/canadapter/ADAS_Seg'][0], 'True')

            self.assertEqual(int(messages['data/canadapter/ADAS_Posn_MsgType'][0]), 0)
            self.assertEqual(int(messages['data/canadapter/ADAS_Posn_MsgType'][1]), 7)
            self.assertAlmostEqual(float(messages['data/canadapter/ADAS_Posn_Offset'][0]), 817.0)
            self.assertAlmostEqual(float(messages['data/canadapter/ADAS_Posn_Offset'][1]), 8191.0)
            self.assertEqual(int(messages['data/canadapter/ADAS_ProfShort_CtrlPoint'][0]), 1)

            j = json.loads(messages['data/canadapter/ADAS_Posn_1'][0])
            self.assertEqual(j["values"]["ADAS_Posn_CycCnt"], 0)
            self.assertAlmostEqual(j["values"]["ADAS_Posn_Spd"], 0.0)
            self.assertAlmostEqual(j["values"]["Position_offset"], 817.0)
            self.assertEqual(j["values"]["ADAS_Posn_MsgType"], 0)

            j = json.loads(messages['data/canadapter/ADAS_Posn_1'][1])
            self.assertEqual(j["values"]["ADAS_Posn_CycCnt"], 3)
            self.assertAlmostEqual(j["values"]["ADAS_Posn_Spd"], 511.0)
            self.assertAlmostEqual(j["values"]["Position_offset"], 8191.0)
            self.assertEqual(j["values"]["ADAS_Posn_MsgType"], 7)

            j = json.loads(messages['data/canadapter/ADAS_Posn_2'][0])
            self.assertAlmostEqual(j["values"]["ADAS_Posn_PosProbb"], 0.0)
            self.assertAlmostEqual(j["values"]["ADAS_Posn_CurLane"], 0.0)

            j = json.loads(messages['data/canadapter/ADAS_Posn_2'][1])
            self.assertAlmostEqual(j["values"]["ADAS_Posn_PosProbb"], 31.0)
            self.assertAlmostEqual(j["values"]["ADAS_Posn_CurLane"], 7.0)


if __name__ == '__main__':

    # NOTE: Run this test from parent directory, for the relative filepaths to match

            # Run all tests #
    unittest.main(verbosity=2)

            # Run a single test #
    # suite = unittest.TestSuite()
    # suite.addTest(TestCanAdapter("testLoopAggregates"))
    # suite.addTest(TestCanAdapter("testLoopThrottleCanFrames"))
    # suite.addTest(TestConverter("test_converter_individual"))
    # suite.addTest(TestConverter("test_converter_aggregate"))
    # unittest.TextTestRunner(verbosity=2).run(suite)
