#################################################################
### Send MQTT data as fast as possible, using the sgframework ###
#################################################################

import argparse
import atexit
import logging
import os
import sys
import time

assert sys.version_info >= (3, 2, 0), "Python version 3.2 or later required!"

import sgframework


MQTT_HOST = "localhost"
MQTT_PORT = 1883
RESOURCE_NAME = "sgspeedsender"
DATA_SIGNAL_NAME = "abc"


def main():
    
      ## Parse command line arguments ##
    description = "Measure the MQTT message sending speed. Implemented using a 'Resource' from the SG framework."
    commandlineparser = argparse.ArgumentParser(description=description)
    commandlineparser.add_argument('-n', 
                                   help="Number of MQTT messages to send. Defaults to %(default)s messages.",
                                   type=int,
                                   default=1000)
    commandline = commandlineparser.parse_args()
    assert commandline.n > 0, "You must send at least 1 message"

      ## Set up SG resource ##
    resource = sgframework.Resource(RESOURCE_NAME, MQTT_HOST)
    resource.register_outgoing_data(DATA_SIGNAL_NAME)
    resource.start(use_threaded_networking=True)
    

      ## Send data ##
    starttime = time.time()
    for i in range(commandline.n):
        resource.send_data(DATA_SIGNAL_NAME, "message"+str(i))
    stoptime = time.time()

      ## Calculate statistics ##
    execution_time = stoptime - starttime
    messagerate = commandline.n / execution_time 
    print("Done putting {} MQTT messages in the send queue.".format(commandline.n))
    print("It took {:.1f} seconds, corresponding to {:.1f} MQTT messages per second".
            format(execution_time, messagerate))

      ## Shutting down ##
    time.sleep(10)
    resource.stop()
    

if __name__ == '__main__':
    main()
