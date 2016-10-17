##############################################################################
### Send MQTT data as fast as possible, using the Paho MQTT client library ###
##############################################################################

import argparse
import logging
import sys
import time

import paho.mqtt.client as mqtt

assert sys.version_info >= (3, 2, 0), "Python version 3.2 or later required!"


def goodbye():
    global starttime
    try:
        total_execution_time = time.time() - starttime
        print('Total time since first message was sent: {:.1f} seconds'.format(total_execution_time))
    except NameError:  # starttime not yet defined
        pass


import atexit
atexit.register(goodbye)


MQTT_HOST = "localhost"
MQTT_PORT = 1883
TOPIC_PLAIN = "data/pahosender/test1"
TOPIC_INDIVIDUAL = "data/pahosender/test2/"  # An integer (string) will be added to the end
SUBSCRIPTION_TOPIC = 'command/pahosender/#'
MQTT_QOS = 0


def main():
    global starttime

      ## Parse command line arguments ##
    description = "Measure the MQTT message sending speed. Implemented using the Paho client."
    commandlineparser = argparse.ArgumentParser(description=description)
    commandlineparser.add_argument('-n',
                                   help="Number of MQTT messages to send. Defaults to %(default)s messages.",
                                   type=int,
                                   default=1000)
    commandlineparser.add_argument('-i',
                                   help="Use individual topics for all MQTT messages",
                                   action='store_true')
    commandline = commandlineparser.parse_args()
    assert commandline.n > 0, "You must send at least 1 message"

      ## Set up MQTT client ##
    print("\nConnecting to MQTT broker: {}  Port: {}".format(MQTT_HOST, MQTT_PORT))
    mqtt_client = mqtt.Client(client_id="pahosender", clean_session=True)
    mqtt_client.on_message = on_mqtt_message
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_disconnect = on_mqtt_disconnect
    mqtt_client.on_subscribe = on_mqtt_subscribe

    mqtt_client.connect(MQTT_HOST, MQTT_PORT)
    mqtt_client.loop()

    mqtt_client.subscribe(SUBSCRIPTION_TOPIC, qos=MQTT_QOS)
    mqtt_client.loop_start()

      ## Send MQTT messages ##
    if not commandline.i:
        print("Sending {} MQTT messages on topic '{}' ...".format(commandline.n, TOPIC_PLAIN))
        starttime = time.time()
        for i in range(commandline.n):
            mqtt_client.publish(TOPIC_PLAIN, "message"+str(i))
        stoptime = time.time()
    else:
        print("Sending {} MQTT messages on individual topics starting with '{}' ...".format(
                commandline.n, TOPIC_INDIVIDUAL))
        starttime = time.time()
        for i in range(commandline.n):
            mqtt_client.publish(TOPIC_INDIVIDUAL+str(i), "message"+str(i))
        stoptime = time.time()

      ## Calculate statistics ##
    execution_time = stoptime - starttime
    messagerate = commandline.n / execution_time
    print("Done putting {} MQTT messages in the send queue.".format(commandline.n))
    print("It took {:.1f} seconds, corresponding to {:.1f} MQTT messages per second".
            format(execution_time, messagerate))

      ## Shutting down ##
    mqtt_client.loop_stop()
    mqtt_client.disconnect()


#### MQTT callbacks ####
# See paho documentation for interfaces

def on_mqtt_message(client, userdata, msg):
    logging.info("Received MQTT message. Topic: {}  Payload: {!s}".format(msg.topic, msg.payload))


def on_mqtt_connect(client, userdata, rc):
    logging.info("    Result of connection attempt to MQTT broker: {}".format(mqtt.connack_string(rc)))


def on_mqtt_disconnect(client, userdata, rc):
    logging.info("Disconnected from MQTT broker. Result: {}".format(mqtt.connack_string(rc)))


def on_mqtt_subscribe(client, userdata, mid, granted_qos):
    logging.info('    Subscribed to MQTT for message id: {} QOS: {}'.format(mid, granted_qos))


if __name__ == '__main__':
    main()
