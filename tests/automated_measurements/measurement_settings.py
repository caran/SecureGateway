## Commands ##
COMMAND_TEMPLATE_CANSETUP_REAL = "sudo ip link set {caninterface} type can bitrate {bitrate:.0f}"
COMMAND_TEMPLATE_CANGEN = "cangen {caninterface} -g {delay} -I {frame_id} -L 8 -D i -n {number_of_frames}"
COMMAND_TEMPLATE_CANDUMP = "candump {caninterface} -ta -l"
COMMAND_TEMPLATE_CANBUSLOAD = "canbusload {caninterface}@{bitrate:.0f} -t > {filename}"
COMMAND_TEMPLATE_CANADAPTER = "python3 ../../../../../scripts/canadapter.py " + \
                              "../../../../../examples/configfilesForCanadapter/climateservice_cansignals.kcd " + \
                              "-mqttfile ../../../../../examples/configfilesForCanadapter/climateservice_mqttsignals.json " + \
                              "-mqttname climateservice -i {caninterface}"
COMMAND_TEMPLATE_MOSQUITTO_SUB = "mosquitto_sub -v -R -t {topic} > {filename}"
COMMAND_TEMPLATE_MQTT_LOG_LENTH = "while true; do echo \"(`date +%s.%N`)  `wc -l {inputfilename}`\" >> {outputfilename}; sleep {sleeptime}; done"
COMMAND_TEMPLATE_TOP = "COLUMNS=1000 top -cb -n {numberofsamples} -d {delay} > {filename}"
COMMAND_TEMPLATE_IFCONFIG = "ifconfig -a > {filename}"
COMMAND_TEMPLATE_CPUFREQ = "cpufreq-info > {filename}"
COMMAND_TEMPLATE_PS = "ps -ef > {filename}"
COMMAND_TEMPLATE_UNAME = "uname -a > {filename}"
COMMAND_TEMPLATE_LINUXDISTRIBUTION = " cat /etc/*-release > {filename} ; echo " " >> {filename}; lsb_release -a >> {filename} 2> /dev/null"

## File names ##
FILENAME_TOP = "top_data.log"
FILENAME_UNAME = "uname_data.log"
FILENAME_PS = "ps_before_measurement.log"
FILENAME_IFCONFIG = "ifconfig_data.log"
FILENAME_CPUFREQ = "cpufreq_data.log"
FILENAME_CANBUSLOAD = "canbusload_data.log"
FILENAME_MOSQUITTO_SUB = "mosquitto_sub_data.log"
FILENAME_MQTT_LOG_LENGTH = "mqtt_filelength_data.log"
FILENAME_LINUXDISTRIBUTION = "linuxdistribution.log"
FILENAME_COMMANDS = "commands.log"
FILEPATTERN_CANDUMP = "candump*.log"
FILEPATTERN_SUBDIR = "md-*"

## CAN interface and CAN sender machine ##
CAN_BITRATE = 500000
CAN_FRAME_ID = 8
CAN_RECEIVER_INTERFACE_NAME = "can0"
CAN_SENDER_INTERFACE_NAME = "can0"
USE_REMOTE_CAN_SENDER = True
CAN_SENDER_HOST = "192.168.229.129"
CAN_SENDER_USERNAME = "pi"
CAN_SENDER_PASSWORD = "raspberry"

## Delays ##
DELAY_CAN_SETUP = 1  # seconds
DELAY_MQTT_LOG_LENGTH_START = 1  # seconds
DELAY_CAN_SENDER_START = 5  # seconds
DELAY_MONITOR_START = 5  # seconds
DELAY_SHUTDOWN = 10  # seconds

## Misc ##
MQTT_SUBSCRIPTION_TOPIC = "data/climateservice/#"
MQTT_FILELENGTH_SAMPLE_INTERVAL = 0.1  # seconds
NUMBER_OF_AVERAGING_POINTS = 11  # Must be an odd number
MQTT_MESSAGES_PER_CAN_FRAME = 2

TOP_WANTED_NUMBER_OF_SAMPLES = 10
TOP_MINIMUM_DELAY = 5  # seconds
TOP_SEARCH_PATTERNS = {'canadapter': 'python3 ../../../../../scripts',  # keys: outputname, values: searchpattern
                       'candump': 'candump can',
                       'mosquitto_broker': '/usr/sbin/mosquitto',
                       'mosquitto_sub':'mosquitto_sub -v -R -t data/',
                       'mosquitto_sub_filelength_monitor': '/bin/sh -c while true; do echo',
                       'canbusload': 'canbusload can0',
                       'top': 'top -cb -n'}
