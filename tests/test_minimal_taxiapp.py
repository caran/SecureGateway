#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_minimal_taxiapp
----------------------------------

Tests for the minimal app example


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
MQTT_TOPICS_TO_DELETE = [
                         "data/taxisignservice/state",
                         ]


class TestMinimalTaxiapp(unittest.TestCase):

    OUTPUT_FILE_APP = 'temporary-app.txt'
    OUTPUT_FILE_SUBSCRIBER = 'temporary-sub.txt'

    def setUp(self):
        self.environment = os.environ.copy()
        self.environment["COVERAGE_PROCESS_START"] = os.path.join(THIS_DIRECTORY, "coveragerc")

    def tearDown(self):

        # Remove temporary files
        os.remove(self.OUTPUT_FILE_APP)
        os.remove(self.OUTPUT_FILE_SUBSCRIBER)

        # Delete persistent MQTT messages
        for topic in MQTT_TOPICS_TO_DELETE:
            pub = subprocess.Popen(['mosquitto_pub', '-t', topic, '-r', '-n'])
            time.sleep(0.2)
            pub.terminate()

    def testMinimalTaxiapp(self):

        with open(self.OUTPUT_FILE_SUBSCRIBER, 'w') as subscriber_outputfile, \
             open(self.OUTPUT_FILE_APP, 'w') as app_outputfile:

            subcriber = subprocess.Popen(['mosquitto_sub', '-v', '-t', 'command/taxisignservice/#'],
                                         stdout=subscriber_outputfile,
                                         stderr=subprocess.STDOUT)

            app = subprocess.Popen([sys.executable, 'examples/minimal/minimaltaxiapp_with_signalhandler.py'],
                                   stdout=app_outputfile,
                                   stderr=subprocess.STDOUT,
                                   env=self.environment)

            time.sleep(5)

            # Verify that the app reacts to taxi sign state changes
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'data/taxisignservice/state', '-m', 'False'])
            time.sleep(3)
            pub2 = subprocess.Popen(['mosquitto_pub', '-t', 'data/taxisignservice/state', '-m', 'True'])
            time.sleep(1)
            pub1.terminate()
            pub2.terminate()

            # Terminate app and flush files
            time.sleep(4)
            app.send_signal(signal.SIGINT)
            time.sleep(1)
            app.terminate()
            subcriber.kill()
            time.sleep(0.1)
            app_outputfile.flush()
            os.fsync(app_outputfile.fileno())
            subscriber_outputfile.flush()
            os.fsync(subscriber_outputfile.fileno())

        # Verify that the app has sent a command to the taxi sign
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'r') as subscriber_outputfile:
            lines = subscriber_outputfile.readlines()
            self.assertEqual(len(lines), 1)
            self.assertIn("command/taxisignservice/state True", lines[0])

        # Verify that the app has reacted to incoming taxi sign state changes
        with open(self.OUTPUT_FILE_APP, 'r') as app_outputfile:
            text = ' '.join(app_outputfile.readlines())
            self.assertIn("The taxi sign is now off.", text)
            self.assertIn("The taxi sign is now on.", text)


if __name__ == '__main__':

            # Run all tests #
    unittest.main(verbosity=2)

            # Run a single test #
    # suite = unittest.TestSuite()
    # suite.addTest(TestCanBus("testReceiveNoData"))
    # unittest.TextTestRunner(verbosity=2).run(suite)
