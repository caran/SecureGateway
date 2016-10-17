#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_minimal_taxisign
----------------------------------

Tests for the minimal resource example


"""
import os.path
import os
import subprocess
import sys
import time
import unittest

assert sys.version_info >= (3, 3, 0), "Python version 3.3 or later required!"

THIS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MQTT_TOPICS_TO_DELETE = [
                         'commandavailable/taxisignservice/state',
                         'dataavailable/taxisignservice/state',
                         'data/taxisignservice/state',
                         'resourceavailable/taxisignservice/presence',
                         ]


class TestMinimalTaxisign(unittest.TestCase):

    OUTPUT_FILE_TAXISIGN = 'temporary-taxisign.txt'
    OUTPUT_FILE_SUBSCRIBER = 'temporary-sub.txt'

    def setUp(self):
        self.environment = os.environ.copy()
        self.environment["COVERAGE_PROCESS_START"] = os.path.join(THIS_DIRECTORY, "coveragerc")

    def tearDown(self):
        # Delete temporary filess
        os.remove(self.OUTPUT_FILE_TAXISIGN)
        os.remove(self.OUTPUT_FILE_SUBSCRIBER)

        # Delete persistent MQTT messages
        for topic in MQTT_TOPICS_TO_DELETE:
            pub = subprocess.Popen(['mosquitto_pub', '-t', topic, '-r', '-n'])
            time.sleep(0.2)
            pub.terminate()

    def testMinimalTaxisign(self):

        with open(self.OUTPUT_FILE_SUBSCRIBER, 'w') as subscriber_outputfile, \
             open(self.OUTPUT_FILE_TAXISIGN, 'w') as taxisign_outputfile:

            subcriber = subprocess.Popen(['mosquitto_sub', '-v', '-t', '+/#'],
                                         stdout=subscriber_outputfile,
                                         stderr=subprocess.STDOUT)

            taxisign = subprocess.Popen([sys.executable, 'examples/minimal/minimaltaxisign_with_signalhandler.py'],
                                        stdout=taxisign_outputfile,
                                        stderr=subprocess.STDOUT,
                                        env=self.environment)

            time.sleep(5)

            # Verify that the taxi sign reacts to commands
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'command/taxisignservice/state', '-m', 'True'])
            time.sleep(3)
            pub2 = subprocess.Popen(['mosquitto_pub', '-t', 'command/taxisignservice/state', '-m', 'False'])
            time.sleep(0.5)
            pub1.terminate()
            pub2.terminate()

            # Terminate taxisign program, and flush files
            time.sleep(4)
            taxisign.terminate()
            time.sleep(1)  # Wait for last will to be sent

            subcriber.kill()
            taxisign_outputfile.flush()
            os.fsync(taxisign_outputfile.fileno())
            subscriber_outputfile.flush()
            os.fsync(subscriber_outputfile.fileno())

        # Verify that the taxisign has sent proper MQTT messages
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'r') as subscriber_outputfile:
            text = ' '.join(subscriber_outputfile.readlines())
            self.assertIn("resourceavailable/taxisignservice/presence True", text)
            self.assertIn("commandavailable/taxisignservice/state True", text)
            self.assertIn("dataavailable/taxisignservice/state True", text)
            self.assertIn("data/taxisignservice/state False", text)
            self.assertIn("data/taxisignservice/state True", text)

        # Verify that the taxi sign has reacted to commands
        with open(self.OUTPUT_FILE_TAXISIGN, 'r') as taxisign_outputfile:
            text = ' '.join(taxisign_outputfile.readlines())
            self.assertIn("Turning on my taxi sign.", text)
            self.assertIn("Turning off my taxi sign.", text)


if __name__ == '__main__':

            # Run all tests #
    unittest.main(verbosity=2)

            # Run a single test #
    # suite = unittest.TestSuite()
    # suite.addTest(TestCanBus("testReceiveNoData"))
    # unittest.TextTestRunner(verbosity=2).run(suite)
