#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_taxisignapp
----------------------------------

Tests for the app controlling the taxi sign.


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
SOURCE_DIRECTORY = os.path.join(PARENT_DIRECTORY, 'examples/taxisignapp/')
sys.path.append(SOURCE_DIRECTORY)

import taxisignapp

MQTT_TOPICS_TO_DELETE = [
                         'commandavailable/taxisignservice/state',
                         'dataavailable/taxisignservice/state',
                         'data/taxisignservice/state',
                         'resourceavailable/taxisignservice/presence',
                         ]


class TestTaxisignApp(unittest.TestCase):

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
            with unittest.mock.patch('builtins.input', return_value=''):
                taxisignapp.init_taxisignapp()
        time.sleep(0.5)

    def testConstructorCommandLine(self):
        with unittest.mock.patch('sys.argv', ['scriptname', '-mode', 'commandline']):
            with unittest.mock.patch('builtins.input', return_value=''):
                taxisignapp.init_taxisignapp()
        time.sleep(0.5)

    def testConstructorGraphical(self):
        with unittest.mock.patch('sys.argv', ['scriptname', '-mode', 'graphical']):
            app = taxisignapp.init_taxisignapp()
        time.sleep(0.5)
        displ = app.userdata
        displ.close()

    def testHelpText(self):
        original_stdout = sys.stdout
        try:
            temporary_stdout = io.StringIO()  # Redirect stdout
            sys.stdout = temporary_stdout
            with unittest.mock.patch('sys.argv', ['scriptname', '-h']):
                with self.assertRaises(SystemExit) as context_manager:
                    taxisignapp.init_taxisignapp()
                self.assertEqual(context_manager.exception.code, 0)  # 'OK exit'
            result = temporary_stdout.getvalue()
        finally:
            sys.stdout = original_stdout
        self.assertIn("usage:", result)
        self.assertIn("{commandline,graphical}", result)

    def testConstructorWrongArguments(self):
        wrong_arguments = [['-mode', 'wrongargument'],
                           ]

        for arguments in wrong_arguments:
            with unittest.mock.patch('sys.argv', arguments):
                with self.assertRaises(SystemExit) as context_manager:
                    taxisignapp.init_taxisignapp()
                self.assertEqual(context_manager.exception.code, 2)  # 'Incorrect usage'

    def testLoop(self):
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'w') as subscriber_outputfile:

            subcriber = subprocess.Popen(['mosquitto_sub', '-v', '-t', '+/#'],
                                         stdout=subscriber_outputfile,
                                         stderr=subprocess.STDOUT)

            with unittest.mock.patch('sys.argv', ['scriptname', '-mode', 'graphical']):
                app = taxisignapp.init_taxisignapp()
            displ = app.userdata

            for i in range(5):
                taxisignapp.loop_taxisignapp(app)
                time.sleep(0.2)

            # Fake an online taxi sign
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'resourceavailable/taxisignservice/presence', '-m', 'True'])
            pub2 = subprocess.Popen(['mosquitto_pub', '-t', 'data/taxisignservice/state', '-m', 'False'])
            time.sleep(0.2)
            pub1.terminate()
            pub2.terminate()

            for i in range(5):
                taxisignapp.loop_taxisignapp(app)
                time.sleep(0.1)

            # Press the 'on' button (to send MQTT command)
            displ._button_on_handler('unknown event')
            for i in range(5):
                taxisignapp.loop_taxisignapp(app)
                time.sleep(0.1)

            # Press the 'off' button (to send MQTT command)
            displ._button_off_handler('unknown event')
            for i in range(5):
                taxisignapp.loop_taxisignapp(app)
                time.sleep(0.1)

            # Fake taxisign is sending updated state
            pub3 = subprocess.Popen(['mosquitto_pub', '-t', 'data/taxisignservice/state', '-m', 'True'])
            for i in range(5):
                taxisignapp.loop_taxisignapp(app)
                time.sleep(0.1)

            pub4 = subprocess.Popen(['mosquitto_pub', '-t', 'data/taxisignservice/state', '-m', 'False'])
            for i in range(5):
                taxisignapp.loop_taxisignapp(app)
                time.sleep(0.1)

            pub3.terminate()
            pub4.terminate()

            time.sleep(1)

            # Terminate, and flush files
            displ.close()
            subcriber.kill()
            time.sleep(0.2)
            subscriber_outputfile.flush()
            os.fsync(subscriber_outputfile.fileno())

        # Verify that the taxi sign app has emitted the MQTT commands
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'r') as subscriber_outputfile:
            text = ' '.join(subscriber_outputfile.readlines())
            self.assertIn("command/taxisignservice/state True", text)
            self.assertIn("command/taxisignservice/state False", text)


if __name__ == '__main__':

            # Run all tests #
    unittest.main(verbosity=2)

            # Run a single test #
    # suite = unittest.TestSuite()
    # suite.addTest(TestTaxisignService("testHelpText"))
    # unittest.TextTestRunner(verbosity=2).run(suite)
