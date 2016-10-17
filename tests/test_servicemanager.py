#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_servicemanager
----------------------------------

Tests for the servicemanager


"""

import os.path
import os
import signal
import subprocess
import sys
import time
import unittest

assert sys.version_info >= (3, 3, 0), "Python version 3.3 or later required!"

THIS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
PARENT_DIRECTORY = os.path.dirname(THIS_DIRECTORY)
SOURCE_DIRECTORY = os.path.join(PARENT_DIRECTORY, 'scripts/')
sys.path.append(SOURCE_DIRECTORY)

MQTT_TOPICS_TO_DELETE = [
                         'dataavailable/testresource2/testdata1',
                         'dataavailable/testresource2/testdata2',
                         'dataavailable/testresource2/testdata3',
                         'commandavailable/testresource2/testcommand1',
                         'commandavailable/testresource2/testcommand2',
                         'commandavailable/testresource2/testcommand3',
                         'resourceavailable/testresource2/presence',
                         ]


class TestServicemanager(unittest.TestCase):

    OUTPUT_FILE_SUBSCRIBER = 'temporary-sub.txt'

    def setUp(self):
        self.environment = os.environ.copy()
        self.environment["COVERAGE_PROCESS_START"] = os.path.join(THIS_DIRECTORY, "coveragerc")

    def tearDown(self):

        # Delete temporary filess
        try:
            os.remove(self.OUTPUT_FILE_SUBSCRIBER)
        except FileNotFoundError:
            pass

        # Delete persistent MQTT messages
        for topic in MQTT_TOPICS_TO_DELETE:
            pub = subprocess.Popen(['mosquitto_pub', '-t', topic, '-r', '-n'])
            time.sleep(0.2)
            pub.terminate()

    def testServicemanager(self):
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'w') as subscriber_outputfile:
            subcriber = subprocess.Popen(['mosquitto_sub', '-v', '-t', '+/#'],
                                         stdout=subscriber_outputfile,
                                         stderr=subprocess.STDOUT)
            servicemanager = subprocess.Popen(['python3', 'scripts/servicemanager'],
                                              stderr=subprocess.STDOUT,
                                              env=self.environment)
            time.sleep(3)

            # Simulate a starting resource (so the servicemanager can store the data)
            mqtt_message_list = [('resourceavailable/testresource2/presence', 'True'),
                                 ('dataavailable/testresource2/testdata1', 'True'),
                                 ('dataavailable/testresource2/testdata2', 'True'),
                                 ('dataavailable/testresource2/testdata3', 'True'),
                                 ('commandavailable/testresource2/testcommand1', 'True'),
                                 ('commandavailable/testresource2/testcommand2', 'True'),
                                 ('commandavailable/testresource2/testcommand3', 'True'),
                                 ]
            for topic, payload in mqtt_message_list:
                pub1 = subprocess.Popen(['mosquitto_pub', '-t', topic, '-m', payload])
                time.sleep(0.2)
                pub1.terminate()

            time.sleep(3)

            # Simulate a stopping resource
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'resourceavailable/testresource2/presence', '-m', 'False'])
            time.sleep(2)
            pub1.terminate()

            # Test error handling
            mqtt_message_list = [('resourceavailable/testresource3/presence/extralevel', 'True'),
                                 ('resourceavailable/testresource4/presence', 'False'),
                                 ('a/b', '1.2.3'),
                                 ('hatt/testresource5/presence', 'True'),
                                 ]
            for topic, payload in mqtt_message_list:
                pub1 = subprocess.Popen(['mosquitto_pub', '-t', topic, '-m', payload])
                time.sleep(0.2)
                pub1.terminate()

            # Terminate servicemanager, and flush files
            servicemanager.send_signal(signal.SIGINT)
            time.sleep(1)
            servicemanager.terminate()
            time.sleep(1)
            servicemanager.kill()
            time.sleep(3)
            subcriber.kill()
            time.sleep(0.5)
            subscriber_outputfile.flush()
            os.fsync(subscriber_outputfile.fileno())

        # Verify that the servicemanager has sent proper MQTT messages
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'r') as subscriber_outputfile:
            text = ' '.join(subscriber_outputfile.readlines())
            self.assertIn("dataavailable/testresource2/testdata1 False", text)
            self.assertIn("dataavailable/testresource2/testdata2 False", text)
            self.assertIn("dataavailable/testresource2/testdata3 False", text)
            self.assertIn("commandavailable/testresource2/testcommand1 False", text)
            self.assertIn("commandavailable/testresource2/testcommand2 False", text)
            self.assertIn("commandavailable/testresource2/testcommand3 False", text)


if __name__ == '__main__':

            # Run all tests #
    unittest.main(verbosity=2)

            # Run a single test #
    # suite = unittest.TestSuite()
    # suite.addTest(TestCanBus("testReceiveNoData"))
    # unittest.TextTestRunner(verbosity=2).run(suite)
