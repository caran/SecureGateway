#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_framework_resource
----------------------------------

Tests for the resource part of the sgframework.

"""
import os.path
import os
import subprocess
import sys
import time
import unittest

assert sys.version_info >= (3, 3, 0), "Python version 3.3 or later required!"
import unittest.mock

import sgframework

MQTT_TOPICS_TO_DELETE = [
                         'dataavailable/testresource/teststate',
                         'dataavailable/testresource/teststate2',
                         'dataavailable/testresource/teststate3',
                         'dataavailable/testresource/teststate4',
                         'dataavailable/testresource/teststate5',
                         'dataavailable/testresource/teststate6',
                         'dataavailable/testresource/teststate7',
                         'commandavailable/testresource/teststate',
                         'commandavailable/testresource/teststate2',
                         'commandavailable/testresource/teststate5',
                         'commandavailable/testresource/teststate6',
                         'resourceavailable/testresource/presence',
                         'data/testresource/teststate5',
                         'data/testresource/teststate7',
                         'command/remoteservice/remotestate4',
                         ]


class TestSignalInfoObject(unittest.TestCase):

    def testConstructorInput(self):
        info = sgframework.framework.Inputsignalinfo(messagetype="data",
                                                     servicename="a",
                                                     signalname="b",
                                                     callback=None,
                                                     callback_on_change_only=False,
                                                     echo=False,
                                                     send_echo_as_retained=False,
                                                     defaultvalue=None)
        self.assertEqual(info.servicename, "a")

    def testWrongConstructorInput(self):
        self.assertRaises(ValueError, sgframework.framework.Inputsignalinfo,
                          messagetype="hatt",
                          servicename="a",
                          signalname="b",
                          callback=None,
                          callback_on_change_only=False,
                          echo=False,
                          send_echo_as_retained=False,
                          defaultvalue=None)

    def testConstructorOutput(self):
        info = sgframework.framework.Outputsignalinfo(messagetype="data",
                                                      servicename="d",
                                                      signalname="e",
                                                      defaultvalue=None,
                                                      send_as_retained=False)
        self.assertEqual(info.servicename, "d")

    def testWrongConstructorOutput(self):
        self.assertRaises(ValueError, sgframework.framework.Outputsignalinfo,
                          messagetype="hatt",
                          servicename="d",
                          signalname="e",
                          defaultvalue=None,
                          send_as_retained=False)


class TestBaseFramework(unittest.TestCase):

    def testRepr(self):
        on_remoteservice_data = unittest.mock.Mock()

        base = sgframework.framework.BaseFramework('testresource', 'localhost')
        base.register_incoming_data('remoteservice',
                                    'remotestate',
                                    on_remoteservice_data)
        base.register_incoming_data('remoteservice',
                                    'remotestate2',
                                    on_remoteservice_data)
        base.register_incoming_data('remoteservice',
                                    'remotestate3',
                                    on_remoteservice_data)

        output = repr(base)
        self.assertIn("SG Base Framework: 'testresource', connecting to host 'localhost', port 1883. Has 3 incoming and 0 outgoing topics registered.",
                      output)


class TestFrameworkResource(unittest.TestCase):

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
        resource = sgframework.Resource('testresource', 'localhost')
        resource.start()
        time.sleep(0.1)
        resource.stop()

    def testRepr(self):
        on_remoteservice_data = unittest.mock.Mock()

        resource = sgframework.Resource('testresource', 'localhost')
        resource.register_outgoing_data('teststate')
        resource.register_outgoing_data('teststate2')
        resource.register_outgoing_data('teststate3')
        resource.register_outgoing_data('teststate4')
        resource.register_outgoing_data('teststate5')
        resource.register_incoming_data('remoteservice',
                                        'remotestate',
                                        on_remoteservice_data)
        resource.register_incoming_data('remoteservice',
                                        'remotestate2',
                                        on_remoteservice_data)

        output = repr(resource)
        self.assertEqual("SG Resource: 'testresource', connecting to host 'localhost', port 1883. Has 2 incoming and 5 outgoing topics registered.",
                         output)

    def testStartTwice(self):
        resource = sgframework.Resource('testresource', 'localhost')
        resource.start()
        resource.start()

    def testStopBeforeStart(self):
        resource = sgframework.Resource('testresource', 'localhost')
        self.assertRaises(ValueError, resource.stop)

    def testLoopBeforeStart(self):
        resource = sgframework.Resource('testresource', 'localhost')
        self.assertRaises(ValueError, resource.loop)

    def testSendCommandBeforeStart(self):
        resource = sgframework.Resource('testresource', 'localhost')
        with self.assertRaises(ValueError):
            resource.send_command('remoteservice', 'remotesignalname', 123)

    def testSendDataBeforeStart(self):
        resource = sgframework.Resource('testresource', 'localhost')
        resource.register_outgoing_data('teststate20')
        with self.assertRaises(ValueError):
            resource.send_data('teststate20', 123)

    def testLoop(self):
        on_testresource_command = unittest.mock.Mock(return_value=None)
        on_testresource_command_no_echo = unittest.mock.Mock(return_value=None)
        on_testresource_command_returnvalue = unittest.mock.Mock(return_value=505)
        on_connectionstatus = unittest.mock.Mock()
        on_remoteservice_data = unittest.mock.Mock()
        on_remoteservice_data_changeonly = unittest.mock.Mock()
        on_remoteservice_availability = unittest.mock.Mock()

        def faulty_callback():
            return 1/0

        with open(self.OUTPUT_FILE_SUBSCRIBER, 'w') as subscriber_outputfile:
            subcriber = subprocess.Popen(['mosquitto_sub', '-v', '-t', '+/#'],
                                         stdout=subscriber_outputfile,
                                         stderr=subprocess.STDOUT)

            resource = sgframework.Resource('testresource', 'localhost')

            resource.register_incoming_data('remoteservice',
                                            'remotestate',
                                            on_remoteservice_data)
            resource.register_incoming_data('remoteservice',
                                            'remotestate3',
                                            on_remoteservice_data_changeonly,
                                            callback_on_change_only=True)
            resource.register_incoming_data('remoteservice',
                                            'remotestate4',
                                            faulty_callback)
            resource.register_incoming_availability('commandavailable',
                                                    'remoteservice',
                                                    'remotestate',
                                                    on_remoteservice_availability)
            resource.register_incoming_command('teststate2',
                                               on_testresource_command,
                                               callback_on_change_only=True,
                                               defaultvalue=222)
            resource.register_incoming_command('teststate5',
                                               on_testresource_command_returnvalue,
                                               send_echo_as_retained=True)
            resource.register_incoming_command('teststate6',
                                               on_testresource_command_no_echo,
                                               echo=False)
            resource.register_outgoing_data('teststate3')
            resource.register_outgoing_data('teststate4',
                                            defaultvalue=101)
            resource.register_outgoing_data('teststate7',
                                            send_data_as_retained=True)
            resource.on_broker_connectionstatus_info = on_connectionstatus
            resource.start()
            for i in range(5):
                resource.loop()
                time.sleep(0.1)

            # Send data
            resource.send_data('teststate3', 31)
            for i in range(5):
                resource.loop()
                time.sleep(0.1)
            resource.send_data('teststate4', 41)
            for i in range(5):
                resource.loop()
                time.sleep(0.1)
            resource.send_data('teststate7', 77)
            for i in range(5):
                resource.loop()
                time.sleep(0.1)

            resource.send_data('teststateMissing', 51)  # Not pre-registered

            # Send commands
            resource.send_command('remoteservice', 'remotestate2', "RUN NOW!")
            for i in range(5):
                resource.loop()
                time.sleep(0.1)
            resource.send_command('remoteservice', 'remotestate4', "RUN 4!", send_command_as_retained=True)
            for i in range(5):
                resource.loop()
                time.sleep(0.1)

            # Provoke availability callback
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'commandavailable/remoteservice/remotestate', '-m', 'True'])
            for i in range(5):
                resource.loop()
                time.sleep(0.1)
            pub1.terminate()

            # Provoke data callback
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'data/remoteservice/remotestate', '-m', '61'])
            for i in range(5):
                resource.loop()
                time.sleep(0.1)
            pub1.terminate()
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'data/remoteservice/remotestate', '-m', '62'])
            for i in range(5):
                resource.loop()
                time.sleep(0.1)
            pub1.terminate()
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'data/remoteservice/remotestate3', '-m', '71'])
            for i in range(5):
                resource.loop()
                time.sleep(0.1)
            pub1.terminate()
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'data/remoteservice/remotestate3', '-m', '71'])
            for i in range(5):
                resource.loop()
                time.sleep(0.1)
            pub1.terminate()
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'data/remoteservice/remotestate3', '-m', '73'])
            for i in range(5):
                resource.loop()
                time.sleep(0.1)
            pub1.terminate()

            # Provoke command callback
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'command/testresource/teststate2', '-m', 'Run!'])
            for i in range(5):
                resource.loop()
                time.sleep(0.1)
            pub1.terminate()
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'command/testresource/teststate2', '-m', 'Run!'])
            for i in range(5):
                resource.loop()
            time.sleep(0.1)
            pub1.terminate()
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'command/testresource/teststate2', '-m', 'Run!!!!'])
            for i in range(5):
                resource.loop()
            time.sleep(0.1)
            pub1.terminate()

            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'command/testresource/teststate5', '-m', 'Run again!'])
            for i in range(5):
                resource.loop()
                time.sleep(0.1)
            pub1.terminate()

            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'command/testresource/teststate6', '-m', 'R6'])
            for i in range(5):
                resource.loop()
                time.sleep(0.1)
            pub1.terminate()

            # Provoke faulty callback
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'data/remoteservice/remotestate4', '-m', '4444'])
            for i in range(5):
                resource.loop()
                time.sleep(0.1)
            pub1.terminate()

            # Unregistered input message (is not reaching the callback, as they not are subscribed to)
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'command/testresource/nonregisteredinput', '-m', '0000'])
            for i in range(5):
                resource.loop()
                time.sleep(0.1)
            pub1.terminate()
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'command/testresource/nonregisteredinput/wrong/hierarchy', '-m', '00'])
            for i in range(5):
                resource.loop()
                time.sleep(0.1)
            pub1.terminate()

            # Terminate, and flush files
            resource.stop()
            subcriber.kill()
            time.sleep(0.2)
            subscriber_outputfile.flush()
            os.fsync(subscriber_outputfile.fileno())

        # Verify callbacks
        args = on_connectionstatus.call_args[0]
        self.assertIn(args[1], [True, False])
        self.assertGreaterEqual(on_connectionstatus.call_count, 1)

        args = on_testresource_command.call_args[0]
        self.assertEqual(args[1], "command")
        self.assertEqual(args[2], "testresource")
        self.assertEqual(args[3], "teststate2")
        self.assertEqual(args[4], "Run!!!!")
        self.assertEqual(on_testresource_command.call_count, 2)

        args = on_testresource_command_returnvalue.call_args[0]
        self.assertEqual(args[1], "command")
        self.assertEqual(args[2], "testresource")
        self.assertEqual(args[3], "teststate5")
        self.assertEqual(args[4], "Run again!")
        self.assertEqual(on_testresource_command_returnvalue.call_count, 1)

        args = on_testresource_command_no_echo.call_args[0]
        self.assertEqual(args[1], "command")
        self.assertEqual(args[2], "testresource")
        self.assertEqual(args[3], "teststate6")
        self.assertEqual(args[4], "R6")
        self.assertEqual(on_testresource_command_no_echo.call_count, 1)

        args = on_remoteservice_availability.call_args[0]
        self.assertEqual(args[1], "commandavailable")
        self.assertEqual(args[2], "remoteservice")
        self.assertEqual(args[3], "remotestate")
        self.assertEqual(args[4], "True")
        self.assertEqual(on_remoteservice_availability.call_count, 1)

        args = on_remoteservice_data.call_args[0]
        self.assertEqual(args[1], "data")
        self.assertEqual(args[2], "remoteservice")
        self.assertEqual(args[3], "remotestate")
        self.assertEqual(args[4], "62")
        self.assertEqual(on_remoteservice_data.call_count, 2)

        args = on_remoteservice_data_changeonly.call_args[0]
        self.assertEqual(args[1], "data")
        self.assertEqual(args[2], "remoteservice")
        self.assertEqual(args[3], "remotestate3")
        self.assertEqual(args[4], "73")
        self.assertEqual(on_remoteservice_data_changeonly.call_count, 2)

        # Verify that the resource has emitted the MQTT data messages, and availability info
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'r') as subscriber_outputfile:
            lines = subscriber_outputfile.readlines()
        text = ' '.join(lines)
        self.assertIn("resourceavailable/testresource/presence True", text)
        self.assertIn("commandavailable/testresource/teststate2 True", text)
        self.assertIn("dataavailable/testresource/teststate2 True", text)
        self.assertIn("dataavailable/testresource/teststate3 True", text)
        self.assertIn("dataavailable/testresource/teststate4 True", text)
        self.assertIn("data/testresource/teststate4 101", text)
        self.assertIn("data/testresource/teststate2 222", text)
        self.assertIn("data/testresource/teststate3 31", text)
        self.assertIn("data/testresource/teststate4 41", text)
        self.assertIn("data/testresource/teststate7 77", text)
        self.assertIn("data/testresource/teststate2 Run!", text)  # Echo of incoming command
        self.assertIn("data/testresource/teststate5 505", text)  # Modified echo of incoming command
        self.assertNotIn("data/testresource/teststate6", text)  # No echo for incoming command
        self.assertIn("command/remoteservice/remotestate2 RUN NOW!", text)
        self.assertIn("resourceavailable/testresource/presence False", text)

    def testLoopThreaded(self):
        on_testresource_command = unittest.mock.Mock(return_value=None)
        on_remoteservice_data = unittest.mock.Mock()

        def faulty_callback():
            return 1 / 0

        with open(self.OUTPUT_FILE_SUBSCRIBER, 'w') as subscriber_outputfile:
            subcriber = subprocess.Popen(['mosquitto_sub', '-v', '-t', '+/#'],
                                         stdout=subscriber_outputfile,
                                         stderr=subprocess.STDOUT)

            resource = sgframework.Resource('testresource', 'localhost')
            resource.register_incoming_data('remoteservice',
                                            'remotestate',
                                            on_remoteservice_data)
            resource.register_incoming_command('teststate',
                                               on_testresource_command)
            resource.register_outgoing_data('teststate2')

            resource.on_broker_connectionstatus_info = faulty_callback
            resource.start(use_threaded_networking=True)
            time.sleep(1)
            resource.loop()  # Should trigger a warning

            # Provoke command callback
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'command/testresource/teststate', '-m', 'run'])
            time.sleep(1)
            pub1.terminate()

            # Provoke data callback
            pub1 = subprocess.Popen(['mosquitto_pub', '-t', 'data/remoteservice/remotestate', '-m', 'REMOTE'])
            time.sleep(1)
            pub1.terminate()

            # Send data
            resource.send_data('teststate2', 22)
            time.sleep(1)
            resource.send_data('teststateMissing', 51)  # Not pre-registered
            time.sleep(1)

            # Send commands
            resource.send_command('remoteservice', 'remotestate2', "run remote")
            time.sleep(1)

            # Terminate, and flush files
            resource.stop()
            subcriber.kill()
            time.sleep(0.2)
            subscriber_outputfile.flush()
            os.fsync(subscriber_outputfile.fileno())

        # Verify callbacks
        args = on_testresource_command.call_args[0]
        self.assertEqual(args[1], "command")
        self.assertEqual(args[2], "testresource")
        self.assertEqual(args[3], "teststate")
        self.assertEqual(args[4], "run")
        self.assertEqual(on_testresource_command.call_count, 1)

        args = on_remoteservice_data.call_args[0]
        self.assertEqual(args[1], "data")
        self.assertEqual(args[2], "remoteservice")
        self.assertEqual(args[3], "remotestate")
        self.assertEqual(args[4], "REMOTE")
        self.assertEqual(on_remoteservice_data.call_count, 1)

        # Verify that the resource has emitted the MQTT data messages, and availability info
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'r') as subscriber_outputfile:
            lines = subscriber_outputfile.readlines()
        text = ' '.join(lines)
        self.assertIn("resourceavailable/testresource/presence True", text)
        self.assertIn("commandavailable/testresource/teststate True", text)
        self.assertIn("dataavailable/testresource/teststate True", text)
        self.assertIn("dataavailable/testresource/teststate2 True", text)
        self.assertIn("data/testresource/teststate run", text)  # Echoed command
        self.assertIn("data/testresource/teststate2 22", text)
        self.assertIn("command/remoteservice/remotestate2 run remote", text)
        self.assertIn("resourceavailable/testresource/presence False", text)

    def testLoopNoCleanSession(self):
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'w') as subscriber_outputfile:
            subcriber = subprocess.Popen(['mosquitto_sub', '-v', '-t', '+/#'],
                                         stdout=subscriber_outputfile,
                                         stderr=subprocess.STDOUT)

            resource = sgframework.Resource('testresource', 'localhost')
            resource.register_outgoing_data('teststate')

            resource.start(use_clean_session=False)
            for i in range(5):
                resource.loop()
                time.sleep(0.1)

            # Send commands
            resource.send_command('remoteservice', 'remotestate', "run remote")
            for i in range(5):
                resource.loop()
                time.sleep(0.1)

            # Terminate, and flush files
            resource.stop()
            subcriber.kill()
            time.sleep(0.2)
            subscriber_outputfile.flush()
            os.fsync(subscriber_outputfile.fileno())

        # Verify that the resource has emitted the MQTT data messages, and availability info
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'r') as subscriber_outputfile:
            lines = subscriber_outputfile.readlines()
        text = ' '.join(lines)
        self.assertIn("resourceavailable/testresource/presence True", text)
        self.assertIn("dataavailable/testresource/teststate True", text)
        self.assertIn("command/remoteservice/remotestate run remote", text)
        self.assertIn("resourceavailable/testresource/presence False", text)

    def testLoopQos2(self):

        with open(self.OUTPUT_FILE_SUBSCRIBER, 'w') as subscriber_outputfile:
            subcriber = subprocess.Popen(['mosquitto_sub', '-v', '-t', '+/#'],
                                         stdout=subscriber_outputfile,
                                         stderr=subprocess.STDOUT)

            resource = sgframework.Resource('testresource', 'localhost')
            resource.register_outgoing_data('teststate')
            resource.qos = 2
            resource.start(use_threaded_networking=True)

            # Send commands
            resource.send_command('remoteservice', 'remotestate', "run remote")
            time.sleep(2)

            # Terminate, and flush files
            resource.stop()
            subcriber.kill()
            time.sleep(0.2)
            subscriber_outputfile.flush()
            os.fsync(subscriber_outputfile.fileno())

        # Verify that the resource has emitted the MQTT data messages, and availability info
        with open(self.OUTPUT_FILE_SUBSCRIBER, 'r') as subscriber_outputfile:
            lines = subscriber_outputfile.readlines()
        text = ' '.join(lines)
        self.assertIn("resourceavailable/testresource/presence True", text)
        self.assertIn("dataavailable/testresource/teststate True", text)
        self.assertIn("command/remoteservice/remotestate run remote", text)
        self.assertIn("resourceavailable/testresource/presence False", text)


if __name__ == '__main__':

            # Run all tests #
    unittest.main(verbosity=2)

            # Run a single test #
    # suite = unittest.TestSuite()
    # suite.addTest(TestFrameworkResource("testLoopQos2"))
    # unittest.TextTestRunner(verbosity=2).run(suite)
