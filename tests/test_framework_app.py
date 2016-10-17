#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_framework_app
----------------------------------

Tests for the app part of the sgframework.

"""
import os.path
import os
import subprocess
import sys
import time

assert sys.version_info >= (3, 3, 0), "Python version 3.3 or later required!"
import unittest.mock


import sgframework


def on_testservice_state_data(app, messagetype, servicename, signalname, payload):
    print("PAYLOAD", payload, flush=True)


def on_testservice_command_availability(app, messagetype, servicename, signalname, payload):
    print("PAYLOAD AVAIL", payload, flush=True)


class TestFrameworkApp(unittest.TestCase):

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

    def testConstructor(self):
        app = sgframework.App('testapp', 'localhost')
        app.start()
        time.sleep(0.1)
        app.stop()

    def testRepr(self):
        app = sgframework.App('testapp', 'localhost')
        app.register_incoming_data('testservice',
                                   'teststate',
                                   on_testservice_state_data)
        output = repr(app)
        self.assertEqual("SG App: 'testapp', connecting to host 'localhost', port 1883. Has 1 input signals registered.",
                         output)

    def testLoop(self):
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'w') as subscriber_outputfile:
            subcriber = subprocess.Popen(['mosquitto_sub', '-v', '-t', '+/#'],
                                         stdout=subscriber_outputfile,
                                         stderr=subprocess.STDOUT)

            app = sgframework.App('testapp', 'localhost')
            app.register_incoming_data('testservice',
                                       'teststate',
                                       on_testservice_state_data)
            app.register_incoming_availability('commandavailable',
                                               'testservice',
                                               'teststate',
                                               on_testservice_command_availability)
            app.start()
            for i in range(5):
                app.loop()
                time.sleep(0.1)

            app.send_command('testservice', 'teststate', 8)
            for i in range(5):
                app.loop()
                time.sleep(0.1)

            app.send_command('testservice', 'teststate', 4)
            for i in range(5):
                app.loop()
                time.sleep(0.1)

            # Provoke availability callback
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'commandavailable/testservice/teststate', '-m', 'True'])
            for i in range(5):
                app.loop()
                time.sleep(0.1)
            pub1.terminate()

            # Provoke data callback
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'data/testservice/teststate', '-m', '47'])
            for i in range(5):
                app.loop()
                time.sleep(0.1)
            pub1.terminate()

            # Terminate, and flush files
            app.stop()
            subcriber.kill()
            time.sleep(0.2)
            subscriber_outputfile.flush()
            os.fsync(subscriber_outputfile.fileno())

        # Verify that the app has emitted the MQTT commands
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'r') as subscriber_outputfile:
            text = ' '.join(subscriber_outputfile.readlines())
            self.assertIn("command/testservice/teststate 8", text)
            self.assertIn("command/testservice/teststate 4", text)


if __name__ == '__main__':

            # Run all tests #
    unittest.main(verbosity=2)

            # Run a single test #
    #suite = unittest.TestSuite()
    # suite.addTest(TestTaxisignService("testHelpText"))
    # unittest.TextTestRunner(verbosity=2).run(suite)
