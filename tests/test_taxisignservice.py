#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_taxisignservice
----------------------------------

Tests for the taxi sign.


"""
import io
import os.path
import os
import subprocess
import sys
import time
import unittest

assert sys.version_info >= (3, 3, 0), "Python version 3.3 or later required!"
import unittest.mock

PARENT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIRECTORY = os.path.join(PARENT_DIRECTORY, 'examples/taxisignservice/')
sys.path.append(SOURCE_DIRECTORY)

import taxisignservice

MQTT_TOPICS_TO_DELETE = [
                         'commandavailable/taxisignservice/state',
                         'dataavailable/taxisignservice/state',
                         'data/taxisignservice/state',
                         'resourceavailable/taxisignservice/presence',
                         ]


class TestTaxisignService(unittest.TestCase):

    OUTPUT_FILE_SUBSCRIBER = 'temporary-sub.txt'

    def setUp(self):

        # Kolla att mosquitto är igång
        pass

    def tearDown(self):

        # Remove temporary files
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
        with unittest.mock.patch('sys.argv', ['scriptname']):
            taxisignservice.init_taxisignservice()
        time.sleep(0.5)

    def testConstructorCommandLine(self):
        with unittest.mock.patch('sys.argv', ['scriptname', '-mode', 'commandline']):
            taxisignservice.init_taxisignservice()
        time.sleep(0.5)

    def testConstructorGraphical(self):
        with unittest.mock.patch('sys.argv', ['scriptname', '-mode', 'graphical']):
            resource = taxisignservice.init_taxisignservice()
        time.sleep(0.5)
        sign = resource.userdata
        sign.close()

    def testHelpText(self):
        original_stdout = sys.stdout
        try:
            temporary_stdout = io.StringIO()  # Redirect stdout
            sys.stdout = temporary_stdout
            with unittest.mock.patch('sys.argv', ['scriptname', '-h']):
                with self.assertRaises(SystemExit) as context_manager:
                    taxisignservice.init_taxisignservice()
                self.assertEqual(context_manager.exception.code, 0)  # 'OK exit'
            result = temporary_stdout.getvalue()
        finally:
            sys.stdout = original_stdout
        self.assertIn("usage:", result)
        self.assertIn("{hardware,commandline,graphical}", result)

    def testConstructorWrongArguments(self):
        wrong_arguments = [['-mode', 'wrongargument'],
                           ]

        for arguments in wrong_arguments:
            with unittest.mock.patch('sys.argv', arguments):
                with self.assertRaises(SystemExit) as context_manager:
                    taxisignservice.init_taxisignservice()
                self.assertEqual(context_manager.exception.code, 2)  # 'Incorrect usage'

    def testLoop(self):
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'w') as subscriber_outputfile:
            subcriber = subprocess.Popen(['mosquitto_sub', '-v', '-t', '+/#'],
                                         stdout=subscriber_outputfile,
                                         stderr=subprocess.STDOUT)

            with unittest.mock.patch('sys.argv', ['scriptname', '-mode', 'graphical']):
                resource = taxisignservice.init_taxisignservice()
            sign = resource.userdata

            for i in range(5):
                taxisignservice.loop_taxisignservice(resource)
                time.sleep(0.2)

            # Verify that the taxi sign reacts to commands
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'command/taxisignservice/state', '-m', 'True'])
            for i in range(5):
                taxisignservice.loop_taxisignservice(resource)
                time.sleep(0.2)

            pub2 = subprocess.Popen(['mosquitto_pub', '-t', 'command/taxisignservice/state', '-m', 'False'])
            for i in range(5):
                taxisignservice.loop_taxisignservice(resource)
                time.sleep(0.2)

            pub1.terminate()
            pub2.terminate()

            time.sleep(1)

            # Terminate, and flush files
            sign.close()
            resource.stop()
            time.sleep(1)  # Wait for last will to be sent

            subcriber.kill()
            time.sleep(0.2)
            subscriber_outputfile.flush()
            os.fsync(subscriber_outputfile.fileno())

        # Verify that the taxi sign emits the start MQTT messages, and does respond
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'r') as subscriber_outputfile:
            text = ' '.join(subscriber_outputfile.readlines())
            self.assertIn("resourceavailable/taxisignservice/presence True", text)
            self.assertIn("commandavailable/taxisignservice/state True", text)
            self.assertIn("dataavailable/taxisignservice/state True", text)
            self.assertIn("data/taxisignservice/state False", text)
            self.assertIn("data/taxisignservice/state True", text)


if __name__ == '__main__':

            # Run all tests #
    unittest.main(verbosity=2)

            # Run a single test #
    # suite = unittest.TestSuite()
    # suite.addTest(TestTaxisignService("testHelpText"))
    # unittest.TextTestRunner(verbosity=2).run(suite)
