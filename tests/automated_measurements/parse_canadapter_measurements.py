import argparse
import collections
import copy
import glob
import json
import os
import time

import measurement_settings as settings

MILLISECONDS_PER_SECOND = 1000


def analyze_cangen(directory):
    """Extract info encoded in directory name.

    Args:
        directory (str): full path to the measurement directory.

    For example:
    'md-20160406-095339-g0_500-n120000

    """
    subdir_name = os.path.basename(directory)
    parts = subdir_name.split("-")

    date_string = parts[1]
    time_string = parts[2]
    unix_time = time.mktime(time.strptime(date_string+time_string, "%Y%m%d%H%M%S"))
    delay = float(parts[3].strip("g").replace("_", "."))
    number_of_can_frames = int(parts[4].strip("n"))

    result = {}
    result['time_sequence_start'] = unix_time
    result['number_of_can_frames'] = number_of_can_frames
    result['delay'] = delay

    return result


def analyze_mqtt_filelength(directory):
    result = {}

    full_path = os.path.join(directory, settings.FILENAME_MQTT_LOG_LENGTH)
    with open(full_path, 'r') as f:
        lines = f.readlines()

    timestamps = []
    message_counts = []
    for linenumber, line in enumerate(lines):
        if not line.strip():
            continue

        splitted = line.split()

        timestamp = float(splitted[0].strip("()"))
        timestamps.append(timestamp)

        number_of_messages = int(splitted[1])
        message_counts.append(number_of_messages)

    number_of_readings = len(timestamps)
    if not number_of_readings:
        raise ValueError("There should be at least one datapoint in the file {}".format(full_path))
    result['number_of_readings'] = number_of_readings

    timestamps_relative = [x-timestamps[0] for x in timestamps]

    if message_counts[0]:
        raise ValueError("The first measurement should show zero MQTT messages received. It is {} in file {}".format(
                message_counts[0], full_path))

    result['number_of_mqtt_messages'] = message_counts[-1]
    result['time_measurement_start'] = timestamps[0]
    result['time_measurement_stop'] = timestamps[-1]
    result['duration_time_measurement'] = result['time_measurement_stop'] - result['time_measurement_start']

    if number_of_readings == 1:
        return result

    # Note: number_of_readings is > 1
    index_first_nonzero = None
    for i, count in enumerate(message_counts):
        if count:
            index_first_nonzero = i
            break

    index_last_rising = None  # Can not be the last index, as we not are sure if it actually is rising
    for i in range(number_of_readings-2, -1, -1):  # Start with the second last element
        if message_counts[i] != message_counts[-1]:
            index_last_rising = i
            break

    if index_first_nonzero >= index_last_rising:
        #TODO Too short data interval
        return result

    result['index_first_nonzero'] = index_first_nonzero
    result['index_last_rising'] = index_last_rising
    result['number_of_readings_before_data'] = index_first_nonzero
    result['number_of_readings_after_confirmed_rising_data'] = number_of_readings - index_last_rising - 1

    result['time_data_start_pre'] = timestamps[index_first_nonzero-1]
    result['time_data_start_post'] = timestamps[index_first_nonzero]
    result['time_data_stop_pre'] = timestamps[index_last_rising]
    result['time_data_stop_post'] = timestamps[index_last_rising+1]

    result['duration_time_data'] = result['time_data_stop_post'] - result['time_data_start_pre']
    result['duration_time_before_data'] = result['time_data_start_pre'] - result['time_measurement_start']
    result['duration_time_after_confirmed_rising_data'] = result['time_measurement_stop'] - result['time_data_stop_post']

    timesteps = [timestamps[i+1]-timestamps[i] for i in range(len(timestamps)-1)]
    result['timestep'] = safe_average(timesteps)
    result['timestep_median'] = safe_median(timesteps)
    result['timestep_min'] = safe_min(timesteps)
    result['timestep_max'] = safe_max(timesteps)

    message_increases = [message_counts[i+1]-message_counts[i] for i in range(len(message_counts)-1)]
    instant_message_rates = [new_messages/timestep for timestep, new_messages in zip(timesteps, message_increases)]

    result['message_rate_overall_average'] = result['number_of_mqtt_messages']/result['duration_time_data']

    valid_instant_message_rates = instant_message_rates[index_first_nonzero:index_last_rising]
    result['message_rate_instant_average'] = safe_average(valid_instant_message_rates)
    result['message_rate_instant_median'] = safe_median(valid_instant_message_rates)
    result['message_rate_instant_min'] = safe_min(valid_instant_message_rates)
    result['message_rate_instant_max'] = safe_max(valid_instant_message_rates)

    if index_last_rising - index_first_nonzero > settings.NUMBER_OF_AVERAGING_POINTS:
        assert settings.NUMBER_OF_AVERAGING_POINTS % 2
        assert settings.NUMBER_OF_AVERAGING_POINTS >= 1
        points_per_side = settings.NUMBER_OF_AVERAGING_POINTS // 2  # For example: 5 for NUMBER_OF_AVERAGING_POINTS=11

        moving_average = []
        for i in range(len(instant_message_rates)):
            if i < points_per_side or i > len(instant_message_rates) - 1 - points_per_side:
                moving_average.append(float('NaN'))
            else:
                part = instant_message_rates[i-points_per_side:i+points_per_side+1]
                average = sum(part)/settings.NUMBER_OF_AVERAGING_POINTS
                moving_average.append(average)

        valid_filtered_message_rates = moving_average[index_first_nonzero+points_per_side:index_last_rising-points_per_side]
        result['message_rate_filtered_average'] = safe_average(valid_filtered_message_rates)
        result['message_rate_filtered_median'] = safe_median(valid_filtered_message_rates)
        result['message_rate_filtered_min'] = safe_min(valid_filtered_message_rates)
        result['message_rate_filtered_max'] = safe_min(valid_filtered_message_rates)

    return result


def analyze_top(directory):
    """Analyze output data from the linux 'top' command.

    Args:
        directory (str): full path to the measurement directory.

    For example: 'md-20160406-095339-g0_500-n120000'

    """
    # Extract date from directory name
    subdir_name = os.path.basename(directory)
    parts = subdir_name.split("-")
    date_string = parts[1]

    # Load file
    full_path = os.path.join(directory, settings.FILENAME_TOP)
    with open(full_path, 'r') as f:
        toplines = f.readlines()

    # Initialize storage
    process_cpu = {}
    process_mem = {}
    cpu_user = []
    cpu_system = []
    cpu_idle = []
    mem_used = []
    mem_total = []
    mem_fraction = []
    timestamps = []

    process_types = settings.TOP_SEARCH_PATTERNS.keys()
    for process in process_types:
        process_cpu[process] = []
        process_mem[process] = []

    result = {}
    result['header'] = {}
    result['processes'] = {}
    for process in process_types:
        result['processes'][process] = {}

    # Data parsing
    for row in toplines:
        splitted_row = row.split(sep=None, maxsplit=11)
        if not splitted_row:
            continue

        if splitted_row[0].startswith("top"):
                time_string = splitted_row[2]
                unix_string = date_string + time_string
                unix_time = time.mktime(time.strptime(unix_string, "%Y%m%d%H:%M:%S"))
                timestamps.append(unix_time)
        elif splitted_row[0].startswith("%Cpu(s)"):
                cpu_system_var = float(splitted_row[3].replace(",", "."))
                cpu_idle_var = float(splitted_row[7].replace(",", "."))
                cpu_user_var = float(splitted_row[1].replace(",", "."))
                cpu_system.append(cpu_system_var)
                cpu_idle.append(cpu_idle_var)
                cpu_user.append(cpu_user_var)
        elif splitted_row[0].startswith("KiB") and splitted_row[1].startswith("Mem"):
                mem_tot = int(splitted_row[2].replace(",", "."))
                mem_used_var = int(splitted_row[4].replace(",", "."))
                mem_fraction_var = mem_used_var/mem_tot
                mem_total.append(mem_tot)
                mem_used.append(mem_used_var)
                mem_fraction.append(mem_fraction_var)
        else:
            for process in process_types:
                searchpattern = settings.TOP_SEARCH_PATTERNS[process]
                command = splitted_row[-1]
                if command.startswith(searchpattern):
                       cpu_usage = float(splitted_row[8].replace(",", "."))
                       memory_usage = float(splitted_row[9].replace(",", "."))
                       process_cpu[process].append(cpu_usage)
                       process_mem[process].append(memory_usage)

    if timestamps:
        timesteps = [timestamps[i+1]-timestamps[i] for i in range(len(timestamps)-1)]
    else:
        timesteps = []

    # Build description about header data
    result['header']['mem_total']              = safe_average(mem_total)
    result['header']['mem_total_median']       = safe_median(mem_total)
    result['header']['mem_total_min']          = safe_min(mem_total)
    result['header']['mem_total_max']          = safe_max(mem_total)

    result['header']['mem_used']               = safe_average(mem_used)
    result['header']['mem_used_median']        = safe_median(mem_used)
    result['header']['mem_used_min']           = safe_min(mem_used)
    result['header']['mem_used_max']           = safe_max(mem_used)

    result['header']['mem_fraction']           = safe_average(mem_fraction)
    result['header']['mem_fraction_median']    = safe_median(mem_fraction)
    result['header']['mem_fraction_min']       = safe_min(mem_fraction)
    result['header']['mem_fraction_max']       = safe_max(mem_fraction)

    result['header']['cpu_user']               = safe_average(cpu_user)
    result['header']['cpu_user_median']        = safe_median(cpu_user)
    result['header']['cpu_user_min']           = safe_min(cpu_user)
    result['header']['cpu_user_max']           = safe_max(cpu_user)

    result['header']['cpu_idle']               = safe_average(cpu_idle)
    result['header']['cpu_idle_median']        = safe_median(cpu_idle)
    result['header']['cpu_idle_min']           = safe_min(cpu_idle)
    result['header']['cpu_idle_max']           = safe_max(cpu_idle)

    result['header']['cpu_system']             = safe_average(cpu_system)
    result['header']['cpu_system_median']      = safe_median(cpu_system)
    result['header']['cpu_system_min']         = safe_min(cpu_system)
    result['header']['cpu_system_max']         = safe_max(cpu_system)

    result['header']['time_first_measurement'] = safe_min(timestamps)
    result['header']['time_last_measurement']  = safe_max(timestamps)
    result['header']['number_of_measurements'] = len(timestamps)
    result['header']['duration_time']          = safe_max(timestamps) - safe_min(timestamps)

    result['header']['timestep']               = safe_average(timesteps)
    result['header']['timestep_median']        = safe_median(timesteps)
    result['header']['timestep_max']           = safe_max(timesteps)
    result['header']['timestep_min']           = safe_min(timesteps)

    # Build description about each process
    for process in process_types:
        result['processes'][process]['cpu']                    = safe_average(process_cpu[process])
        result['processes'][process]['cpu_median']             = safe_median(process_cpu[process])
        result['processes'][process]['cpu_max']                = safe_max(process_cpu[process])
        result['processes'][process]['cpu_min']                = safe_min(process_cpu[process])
        result['processes'][process]['number_of_measurements'] = len(process_cpu[process])
        result['processes'][process]['mem']                    = safe_average(process_mem[process])
        result['processes'][process]['mem_median']             = safe_median(process_mem[process])
        result['processes'][process]['mem_max']                = safe_max(process_mem[process])
        result['processes'][process]['mem_min']                = safe_min(process_mem[process])

    return result


def analyze_canbusload(directory):
    full_path = os.path.join(directory, settings.FILENAME_CANBUSLOAD)

    with open(full_path, 'r') as f:
        canbuslines = f.readlines()

    raw_rows = ' '.join(canbuslines).split("canbusload")

    canframes_list = []
    canbusload_list = []
    number_of_valid_measurements = 0
    timestamps_valid_measurements = []
    timestamps_empty_measurements = []
    interface = ''
    bitrate = 0
    for row in raw_rows:
        if not row.strip():
            continue

        splitted_row = row.split()
        date_string = splitted_row[0]
        time_string = splitted_row[1]
        unix_time = time.mktime(time.strptime(date_string+time_string, "%Y-%m-%d%H:%M:%S"))
        number_of_canframes = int(splitted_row[6])
        canbusload = int(splitted_row[9].strip("%"))
        interface = splitted_row[5].split("@")[0]
        bitrate = int(splitted_row[5].split("@")[1])

        if number_of_canframes:
            number_of_valid_measurements += 1
            canframes_list.append(number_of_canframes)
            canbusload_list.append(canbusload)
            timestamps_valid_measurements.append(unix_time)
        else:
            timestamps_empty_measurements.append(unix_time)

    if not number_of_valid_measurements:
        raise ValueError("There are no valid measurements in the file {}".format(full_path))

    result = {}
    result['number_of_measurements'] = len(timestamps_valid_measurements) \
                                       + len(timestamps_empty_measurements)
    result['number_of_valid_measurements'] = len(timestamps_valid_measurements)
    result['number_of_empty_measurements'] = len(timestamps_empty_measurements)

    result['time_first_measurement'] = safe_min(timestamps_valid_measurements+timestamps_empty_measurements)
    result['time_last_measurement'] = safe_max(timestamps_valid_measurements+timestamps_empty_measurements)
    result['time_first_valid_measurement'] = safe_min(timestamps_valid_measurements)
    result['time_last_valid_measurement'] = safe_max(timestamps_valid_measurements)
    result['duration_time_valid_measurements'] = safe_max(timestamps_valid_measurements) \
                                                 - safe_min(timestamps_valid_measurements)
    result['time_first_empty_measurement'] = safe_min(timestamps_empty_measurements)
    result['time_last_empty_measurement'] = safe_max(timestamps_empty_measurements)

    result['canframes'] = safe_average(canframes_list)
    result['canframes_median'] = safe_median(canframes_list)
    result['canframes_min'] = safe_min(canframes_list)
    result['canframes_max'] = safe_max(canframes_list)

    result['busload'] = safe_average(canbusload_list)
    result['busload_median'] = safe_median(canbusload_list)
    result['busload_min'] = safe_min(canbusload_list)
    result['busload_max'] = safe_max(canbusload_list)

    result['bitrate'] = bitrate
    result['interface'] = interface

    return result

def analyze_commands(directory):
    full_path = os.path.join(directory, settings.FILENAME_COMMANDS)
    
    try:
        with open(full_path, 'r') as f:
            commandlines = f.readlines()
    except FileNotFoundError:
        return {}

    result = {}
    for commandline in commandlines:
        stripped = commandline.strip()
        filtered = ''.join([x for x in stripped if x not in '"'])
        if filtered:
            splitted = filtered.split(maxsplit=1)
            if len(splitted) > 1:
                command_name, command_value = splitted
                result[command_name] = command_value 
    
    return result


def analyze_mosquitto_sub(directory):
    full_path = os.path.join(directory, settings.FILENAME_MOSQUITTO_SUB)

    with open(full_path, 'r') as f:
        mosquittolines = f.readlines()

    result = {}
    result['number_of_mqtt_messages'] = len(mosquittolines)

    return result


def analyze_platform(directory):
    result = {}
    full_path = os.path.join(directory, settings.FILENAME_LINUXDISTRIBUTION)
    try:
        with open(full_path, 'r') as f:
            lines = f.readlines()
        result['linuxdistribution_info'] = '   '.join([x.strip() for x in lines]).replace('\t', ' ').replace('"', "'")
    except FileNotFoundError:
        result['linuxdistribution_info'] = "Unknown"

    full_path = os.path.join(directory, settings.FILENAME_UNAME)
    try:
        with open(full_path, 'r') as f:
            lines = f.readlines()
        result['uname'] = lines[0].strip()
    except FileNotFoundError:
        result['uname'] = "Unknown"

    full_path = os.path.join(directory, settings.FILENAME_CPUFREQ)
    try:
        with open(full_path, 'r') as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip().replace('"', "'")
            if line.startswith('hardware limits'):
                result['cpufreq_hardware_limits'] = line
            elif line.startswith('available frequency steps'):
                result['cpufreq_frequency_steps'] = line
            elif line.startswith('available cpufreq governors'):
                result['cpufreq_governors'] = line
            elif line.startswith('current CPU frequency is'):
                result['cpufreq_current_frequency'] = line
            elif line.startswith('The governor'):
                result['cpufreq_current_governor'] = line
    except FileNotFoundError:
        result['cpufreq_hardware_limits'] = "Unknown"
        result['cpufreq_frequency_steps'] = "Unknown"
        result['cpufreq_governors'] = "Unknown"
        result['cpufreq_current_frequency'] = "Unknown"
        result['cpufreq_current_governor'] = "Unknown"

    ip_addresses = []
    full_path = os.path.join(directory, settings.FILENAME_IFCONFIG)
    try:
        with open(full_path, 'r') as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line.startswith('inet addr'):
                ip_addresses.append(line.split()[1].split(':')[1])
        result['IP_addresses'] = '   '.join(ip_addresses)
    except FileNotFoundError:
        result['IP_addresses'] = "Unknown"

    return result


def parse_candump_line(inputstring):
    """Parse a line from a candump log.

    The input should be a string, for example
    '(1459760909.868244) vcan0 008#9D0F000000000000\n'

    Returns a 'datapoint' object with the attributes:
        * timestamp (float)
        * interface (str)
        * can_id (int)
        * data (str)

    """
    timestamp_string = inputstring.split()[0].strip('()')
    timestamp = float(timestamp_string)

    id_data_string = inputstring.split()[2].strip()
    id_data_splitted = id_data_string.split('#')
    can_id = int(id_data_splitted[0], 16)
    data = id_data_splitted[1]

    interface = inputstring.split()[1].strip()

    Candump_datapoint = collections.namedtuple('Candump_datapoint', 'timestamp interface canid data')
    datapoint = Candump_datapoint(timestamp, interface, can_id, data)

    return datapoint


def analyze_candump(directory):
    candump_files = glob.glob(os.path.join(directory, settings.FILEPATTERN_CANDUMP))
    if len(candump_files) != 1:
        raise ValueError("There should be exactly one candump file in the directory, found {}. Dir: {}".
                         format(len(candump_files), directory))

    with open(candump_files[0], 'r') as candumpfile:
        candump_lines = candumpfile.readlines()

    info_first_frame = parse_candump_line(candump_lines[0])
    info_last_frame = parse_candump_line(candump_lines[-1])

    number_of_can_frames = len(candump_lines)
    duration_time = info_last_frame.timestamp - info_first_frame.timestamp

    if number_of_can_frames > 1:
        framerate = number_of_can_frames / duration_time
        timestep = MILLISECONDS_PER_SECOND * duration_time / number_of_can_frames
    else:
        framerate = float('NaN')
        timestep = float('NaN')

    result = {}
    result['number_of_can_frames'] = number_of_can_frames
    result['duration_time'] = duration_time
    result['framerate'] = framerate
    result['timestep_overall_average'] = timestep
    result['interface'] = info_first_frame.interface

    result['time_first_frame'] = info_first_frame.timestamp
    result['id_first_frame'] = info_first_frame.canid
    result['data_first_frame'] = info_first_frame.data

    result['time_last_frame'] = info_last_frame.timestamp
    result['id_last_frame'] = info_last_frame.canid
    result['data_last_frame'] = info_last_frame.data

    return result


def update_with_can_frame_loss(inputmessage):
    message = copy.copy(inputmessage)

    sent_can_frames = message['cangen']['number_of_can_frames']
    received_can_frames = message['candump']['number_of_can_frames']
    lost_can_frames = sent_can_frames - received_can_frames

    result = {}
    result['lost_can_frames'] = lost_can_frames
    result['lost_can_frames_ratio'] = lost_can_frames/sent_can_frames

    message['can_frame_loss'] = result

    return message


def update_with_mqtt_loss(inputmessage):
    message = copy.copy(inputmessage)

    received_can_frames = message['candump']['number_of_can_frames']
    received_mqtt_messages = message['mosquitto_sub']['number_of_mqtt_messages']
    expected_mqtt_messages = settings.MQTT_MESSAGES_PER_CAN_FRAME * received_can_frames

    lost_mqtt_messages = expected_mqtt_messages - received_mqtt_messages

    result = {}
    result['mqtt_messages_per_can_frame'] = settings.MQTT_MESSAGES_PER_CAN_FRAME
    result['expected_mqtt_messages'] = expected_mqtt_messages
    result['lost_mqtt_messages'] = lost_mqtt_messages
    result['lost_mqtt_messages_ratio'] = lost_mqtt_messages/expected_mqtt_messages

    message['mqtt_message_loss'] = result
    return message


def update_with_timing(inputmessage):
    message = copy.copy(inputmessage)

    result = {}
    result['time_measurement_start'] = message['mqtt_file_length']['time_measurement_start']
    result['time_measurement_stop'] = message['mqtt_file_length']['time_measurement_stop']
    result['time_duration_to_first_can'] = message['candump']['time_first_frame'] \
                                           - message['mqtt_file_length']['time_measurement_start']
    result['time_duration_after_last_can'] = message['mqtt_file_length']['time_measurement_stop'] \
                                             - message['candump']['time_last_frame']

    result['time_duration_to_first_mqtt'] = message['mqtt_file_length']['time_data_start_post'] \
                                            - message['mqtt_file_length']['time_measurement_start']
    result['time_duration_after_last_mqtt'] = message['mqtt_file_length']['time_measurement_stop'] \
                                              - message['mqtt_file_length']['time_data_stop_post']

    result['lag_start'] = message['mqtt_file_length']['time_data_start_post'] - \
                          message['candump']['time_first_frame']
    result['lag_stop'] = message['mqtt_file_length']['time_data_stop_post'] - \
                         message['candump']['time_last_frame']

    message['timing'] = result
    return message


def analyze(directory):
    outputmessage = {}
    outputmessage['platform'] = analyze_platform(directory)
    outputmessage['commands'] = analyze_commands(directory)
    outputmessage['mqtt_file_length'] = analyze_mqtt_filelength(directory)
    outputmessage['cangen'] = analyze_cangen(directory)
    outputmessage['candump'] = analyze_candump(directory)
    outputmessage['mosquitto_sub'] = analyze_mosquitto_sub(directory)
    outputmessage['canbusload'] = analyze_canbusload(directory)
    outputmessage['top'] = analyze_top(directory)
    outputmessage = update_with_can_frame_loss(outputmessage)
    outputmessage = update_with_mqtt_loss(outputmessage)
    outputmessage = update_with_timing(outputmessage)

    # Save output file
    json_output = json.dumps(outputmessage, sort_keys=True, indent=4)
    print(json_output)
    output_file_name = os.path.basename(directory) + '.json'
    output_directory = os.path.dirname(directory)
    output_full_path = os.path.join(output_directory, output_file_name)
    with open(output_full_path, 'w') as f:
        f.write(json_output)


def analyze_multiple_directories(parent_directory):
    candidate_directories = glob.glob(os.path.join(parent_directory, settings.FILEPATTERN_SUBDIR))
    for directory in candidate_directories:
        if os.path.isdir(directory):
            print("\nAnalyzing", directory)
            analyze(directory)


def safe_min(inputlist):
    # Safe for empty inputlist
    if not inputlist:
        return float('NaN')
    return min(inputlist)


def safe_max(inputlist):
    # Safe for empty inputlist
    if not inputlist:
        return float('NaN')
    return max(inputlist)


def safe_average(inputlist):
    # Safe for empty inputlist
    if not inputlist:
        return float('NaN')
    return sum(inputlist)/len(inputlist)


def safe_median(inputlist):
    # Safe for empty inputlist
    if not inputlist:
        return float('NaN')
    sorted_list = sorted(inputlist)
    number_of_points = len(sorted_list)
    index = (number_of_points - 1) // 2
    if number_of_points % 2:
        return sorted_list[index]
    else:
        return (sorted_list[index] + sorted_list[index + 1])/2


def main():
   # Command line arguments
    parser = argparse.ArgumentParser(description='Analyze measurement data')
    parser.add_argument('parentdirectory', help='The parent directory that contains subdirectories with measurement data.')
    args = parser.parse_args()

    # Analyze data
    analyze_multiple_directories(args.parentdirectory)


if __name__ == '__main__':
    main()
