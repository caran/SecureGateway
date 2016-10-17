#
# CAN vehicle simulator
#
# Author: Jonas Berg
# Copyright (c) 2015, Semcon Sweden AB
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the Semcon Sweden AB nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
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
# 

import argparse
import logging
import time
import sys

import can4python as can
import vehiclesimulationutilities

# Settings #
CYCLE_TIME = 0.1  # seconds


def init_vehiclesimulator():
    """Initialize the vehicle simulator.
    
    Returns the tuple (temperature_simulator, speed_simulator, canbus)
    
    """  
    # Define CAN messages #
    # Example on how to define CAN signals in source code
    CAN_EGO_NODE_ID = "2"
    FRAMEDEF1 = can.CanFrameDefinition(8, name='vehiclesimulationdata')
    FRAMEDEF1.producer_ids = [CAN_EGO_NODE_ID]
    FRAMEDEF1.signaldefinitions.append(can.CanSignalDefinition('vehiclespeed', startbit=8, numberofbits=16,
                                                               scalingfactor=0.01, endianness='big'))
    FRAMEDEF1.signaldefinitions.append(can.CanSignalDefinition('enginespeed', startbit=26, numberofbits=14,
                                                               endianness='big'))
    FRAMEDEF2 = can.CanFrameDefinition(9, name='climatesimulationdata')
    FRAMEDEF2.producer_ids = [CAN_EGO_NODE_ID]
    FRAMEDEF2.signaldefinitions.append(can.CanSignalDefinition('indoortemperature', startbit=8, numberofbits=11,
                                                               valueoffset=-50, scalingfactor=0.1,
                                                               endianness='big'))
    FRAMEDEF3 = can.CanFrameDefinition(7, name='climatecontrolsignals')
    FRAMEDEF3.signaldefinitions.append(can.CanSignalDefinition('acstatus', startbit=7, numberofbits=1,
                                                               endianness='big'))
    CONFIG = can.Configuration(ego_node_ids=[CAN_EGO_NODE_ID])
    CONFIG.add_framedefinition(FRAMEDEF1)
    CONFIG.add_framedefinition(FRAMEDEF2)
    CONFIG.add_framedefinition(FRAMEDEF3)

    # Parse command line and set output verbosity #
    commandlineparser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter)
    commandlineparser.add_argument('-v', action='count', default=0, help="Increase verbosity level. Can be repeated.")
    commandlineparser.add_argument('-i', dest="interface", default="vcan0",
                                   help="CAN interface name. Defaults to %(default)s.")
    commandline = commandlineparser.parse_args()
    if commandline.v == 1:
        loglevel = logging.INFO
    elif commandline.v >= 2:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.WARNING
    logging.basicConfig(level=loglevel)  

    # Set up CAN bus #
    logging.info(" ")
    logging.info(" ")
    logging.info("Starting vehicle simulator, using CAN interface {!r} with timeout {} s.".format(
                 commandline.interface, CYCLE_TIME))

    canbus = can.CanBus(CONFIG, commandline.interface, timeout=CYCLE_TIME)
    logging.debug(canbus.get_descriptive_ascii_art())

    # Set up simulators #
    speed_simulator = vehiclesimulationutilities.VehicleSpeedSimulator()
    temperature_simulator = vehiclesimulationutilities.CabinTemperatureSimulator()

    return temperature_simulator, speed_simulator, canbus


def loop_vehiclesimulator(temperature_simulator, speed_simulator, canbus):

        # Run simulators #
        temperature = temperature_simulator.get_new_temperature()
        vehiclespeed = speed_simulator.get_new_randomized_speed()
        enginespeed = vehiclesimulationutilities.calculate_engine_speed(vehiclespeed)
        
        logging.info(" {0:5.1f} km/h,   {1:4.0f} RPM,   {2:4.1f} deg C.   Air condition state: {3}".format(
                     vehiclespeed, enginespeed, temperature, temperature_simulator.aircondition_state))
        
        # Send CAN data #
        signals_to_send = {'indoortemperature': temperature, 
                           'vehiclespeed': vehiclespeed,
                           'enginespeed': enginespeed}
        canbus.send_signals(signals_to_send)
        
        # Receive CAN data, if available #
        readstart = time.time()
        try:
            received = canbus.recv_next_signals()
        except KeyboardInterrupt:
            logging.warning("Keyboard interrupt. Quitting.")
            raise
        except can.CanTimeoutException:
            received = {}
        except can.CanException as err:            
            logging.warning('Failed to receive CAN frame. Error: {}'.format(err))
            received = {}
            
        readtime = time.time() - readstart
        time.sleep(max(0, CYCLE_TIME-readtime))
        
        # Set air condition state #
        if 'acstatus' in received:
            temperature_simulator.aircondition_state = bool(received['acstatus'])


######################
## Main application ##
######################

def main():
    temperature_simulator, speed_simulator, canbus = init_vehiclesimulator()
    
    ## Main loop ##
    while True:
        try:
            loop_vehiclesimulator(temperature_simulator, speed_simulator, canbus)
        except KeyboardInterrupt:
            sys.exit()
            

if __name__ == '__main__':
    main()
