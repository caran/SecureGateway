#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_vehiclesimulator
----------------------------------

Tests for the vehicle simulator


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
SOURCE_DIRECTORY = os.path.join(PARENT_DIRECTORY, 'examples/vehiclesimulator/')
sys.path.append(SOURCE_DIRECTORY)

import vehiclesimulator
import can4python as can


VIRTUAL_CAN_BUS_NAME = "vcan0"
NONEXISTING_CAN_BUS_NAME = "can25"


def enable_virtual_can_bus():
    try:
        subprocess.check_output(["modprobe", VIRTUAL_CAN_BUS_NAME])
    except:
        raise IOError("Could not modprobe vcan. Are you sure you are running as sudo?")
    try:
        subprocess.check_output(["ip", "link", "add", "dev", VIRTUAL_CAN_BUS_NAME,
                                 "type", "vcan"], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        pass
    try:
        subprocess.check_output(["ifconfig", VIRTUAL_CAN_BUS_NAME, "up"])
    except subprocess.CalledProcessError:
        raise exceptions.CanException("Could not enable {}. Are you sure you are running as sudo?".format(
            VIRTUAL_CAN_BUS_NAME))


def disable_virtual_can_bus():
    subprocess.check_output(["ifconfig", VIRTUAL_CAN_BUS_NAME, "down"])


class TestVehicleSimulator(unittest.TestCase):

    OUTPUT_FILE_CANDUMPER = 'temporary-candump.txt'

    def setUp(self):
        pass

    def tearDown(self):

        # Remove temporary files
        try:
            os.remove(self.OUTPUT_FILE_CANDUMPER)
        except FileNotFoundError:
            pass

    def testConstructor(self):
        with unittest.mock.patch('sys.argv', ['scriptname']):
            vehiclesimulator.init_vehiclesimulator()
        time.sleep(0.5)

    def testConstructorVerbose(self):
        with unittest.mock.patch('sys.argv', ['scriptname', '-v']):
            vehiclesimulator.init_vehiclesimulator()
        time.sleep(0.5)

    def testConstructorVerboser(self):
        with unittest.mock.patch('sys.argv', ['scriptname', '-i', VIRTUAL_CAN_BUS_NAME, '-vv']):
            vehiclesimulator.init_vehiclesimulator()
        time.sleep(0.5)

    def testConstructorWrongArguments(self):
        wrong_arguments = [['scriptname', '-j'],
                           ['scriptname', '-mode', 'commandline'],
                           ]

        for arguments in wrong_arguments:
            with unittest.mock.patch('sys.argv', arguments):
                with self.assertRaises(SystemExit) as context_manager:
                    vehiclesimulator.init_vehiclesimulator()
                self.assertEqual(context_manager.exception.code, 2)  # 'Incorrect usage'

    def testConstructorWrongCanInterface(self):
        with unittest.mock.patch('sys.argv', ['scriptname', '-i', NONEXISTING_CAN_BUS_NAME]):
            with self.assertRaises(can.CanException) as context_manager:
                vehiclesimulator.init_vehiclesimulator()
        time.sleep(0.5)

    def testHelpText(self):
        original_stdout = sys.stdout
        try:
            temporary_stdout = io.StringIO()  # Redirect stdout
            sys.stdout = temporary_stdout
            with unittest.mock.patch('sys.argv', ['scriptname', '-h']):
                with self.assertRaises(SystemExit) as context_manager:
                    vehiclesimulator.init_vehiclesimulator()
                self.assertEqual(context_manager.exception.code, 0)  # 'OK exit'
            result = temporary_stdout.getvalue()
        finally:
            sys.stdout = original_stdout
        self.assertIn("usage:", result)
        self.assertIn("CAN interface name. Defaults to vcan0.", result)

    def testLoop(self):
        with open(self.OUTPUT_FILE_CANDUMPER, 'w') as candumper_outputfile:
            candumper = subprocess.Popen(['candump', VIRTUAL_CAN_BUS_NAME],
                                         stdout=candumper_outputfile,
                                         stderr=subprocess.STDOUT)

            with unittest.mock.patch('sys.argv', ['scriptname', '-i', VIRTUAL_CAN_BUS_NAME, '-vv']):
                temperature_simulator, speed_simulator, canbus = vehiclesimulator.init_vehiclesimulator()

            for i in range(3):
                vehiclesimulator.loop_vehiclesimulator(temperature_simulator, speed_simulator, canbus)

            # Turn on air condition
            pub1 = subprocess.Popen(['cansend', VIRTUAL_CAN_BUS_NAME, '007#8000000000000000'])
            for i in range(3):
                vehiclesimulator.loop_vehiclesimulator(temperature_simulator, speed_simulator, canbus)
            pub1.terminate()

            # Turn off air condition
            pub1 = subprocess.Popen(['cansend', VIRTUAL_CAN_BUS_NAME, '007#0000000000000000'])
            for i in range(3):
                vehiclesimulator.loop_vehiclesimulator(temperature_simulator, speed_simulator, canbus)
            pub1.terminate()

            # Terminate, and flush files
            candumper.kill()
            time.sleep(0.2)
            candumper_outputfile.flush()
            os.fsync(candumper_outputfile.fileno())

        # Verify that the vehicle simulator has emitted CAN frames
        with open(self.OUTPUT_FILE_CANDUMPER , 'r') as candumper_outputfile:
            text = ' '.join(candumper_outputfile.readlines())
            self.assertIn(" 008   [8]  00", text)
            self.assertIn(" 009   [8]  0", text)


if __name__ == '__main__':

            # Run all tests #
    unittest.main(verbosity=2)

            # Run a single test #
    # suite = unittest.TestSuite()
    # suite.addTest(TestTaxisignService("testHelpText"))
    # unittest.TextTestRunner(verbosity=2).run(suite)
