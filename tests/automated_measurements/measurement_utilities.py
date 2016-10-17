import math
import os
import signal
import subprocess
import time
import paramiko

import measurement_settings as settings

MILLISECONDS_PER_SECOND = 1000
THIS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))


def run_measurement(starttime_string, cangen_delay, runtime):
    print("\n" + "*"*100)
    print("\nStarting the measurement for cangen delay {} milliseconds (runtime {} s).".format(cangen_delay, runtime))

    number_of_frames = int(runtime * MILLISECONDS_PER_SECOND / cangen_delay)

    top_monitoring_time = max(runtime - 2 * settings.DELAY_MONITOR_START, 0)  # Finish monitoring before runtime ends
    top_number_of_samples = math.floor(min(settings.TOP_WANTED_NUMBER_OF_SAMPLES,
                                           (top_monitoring_time/settings.TOP_MINIMUM_DELAY)+1))

    if not top_number_of_samples:
        raise ValueError("Wrong settings for the top command, monitor start delay and runtime (no top samples will be used)")

    if top_number_of_samples == 1:
        top_delay = 1  # Whatever
    else:
        top_delay = math.floor(top_monitoring_time/(top_number_of_samples - 1))  # seconds. Might be 1 s shorter than TOP_MINIMUM_DELAY

    ## Create output directory ##
    measurementdata_dir = os.path.join(THIS_DIRECTORY, "_measurementdata")
    os.makedirs(measurementdata_dir, exist_ok=True)

    subdir1name = "md-{}".format(starttime_string)
    subdir1 = os.path.join(measurementdata_dir, subdir1name)
    os.makedirs(subdir1, exist_ok=True)

    subdir2name = "md-{}-g{:.3f}-n{}".format(starttime_string, cangen_delay, number_of_frames).replace('.', '_')
    outputdir = os.path.join(subdir1, subdir2name)
    os.makedirs(outputdir)
    os.chdir(outputdir)
    print("Output directory:", outputdir)

    ## Generate commands ##
    command_cansetup_sender = settings.COMMAND_TEMPLATE_CANSETUP_REAL.format(
            caninterface=settings.CAN_SENDER_INTERFACE_NAME,
            bitrate=settings.CAN_BITRATE)

    command_cansetup_receiver = settings.COMMAND_TEMPLATE_CANSETUP_REAL.format(
            caninterface=settings.CAN_RECEIVER_INTERFACE_NAME,
            bitrate=settings.CAN_BITRATE)

    command_cangen = settings.COMMAND_TEMPLATE_CANGEN.format(caninterface=settings.CAN_SENDER_INTERFACE_NAME,
                                                             delay=cangen_delay,
                                                             frame_id=settings.CAN_FRAME_ID,
                                                             number_of_frames=number_of_frames)

    command_candump = settings.COMMAND_TEMPLATE_CANDUMP.format(caninterface=settings.CAN_RECEIVER_INTERFACE_NAME)

    command_canbusload = settings.COMMAND_TEMPLATE_CANBUSLOAD.format(caninterface=settings.CAN_RECEIVER_INTERFACE_NAME,
                                                                     bitrate=settings.CAN_BITRATE,
                                                                     filename=settings.FILENAME_CANBUSLOAD)

    command_canadapter = settings.COMMAND_TEMPLATE_CANADAPTER.format(caninterface=settings.CAN_RECEIVER_INTERFACE_NAME)

    command_mosquitto_sub = settings.COMMAND_TEMPLATE_MOSQUITTO_SUB.format(topic=settings.MQTT_SUBSCRIPTION_TOPIC,
                                                                           filename=settings.FILENAME_MOSQUITTO_SUB)

    command_mqtt_log_length = settings.COMMAND_TEMPLATE_MQTT_LOG_LENTH.format(
                                inputfilename=settings.FILENAME_MOSQUITTO_SUB,
                                outputfilename=settings.FILENAME_MQTT_LOG_LENGTH,
                                sleeptime=settings.MQTT_FILELENGTH_SAMPLE_INTERVAL)

    command_top = settings.COMMAND_TEMPLATE_TOP.format(numberofsamples=top_number_of_samples,
                                                       delay=top_delay,
                                                       filename=settings.FILENAME_TOP)

    command_cpufreq = settings.COMMAND_TEMPLATE_CPUFREQ.format(filename=settings.FILENAME_CPUFREQ)
    command_ifconfig = settings.COMMAND_TEMPLATE_IFCONFIG.format(filename=settings.FILENAME_IFCONFIG)
    command_ps = settings.COMMAND_TEMPLATE_PS.format(filename=settings.FILENAME_PS)
    command_uname = settings.COMMAND_TEMPLATE_UNAME.format(filename=settings.FILENAME_UNAME)
    command_linuxdistribution = settings.COMMAND_TEMPLATE_LINUXDISTRIBUTION.format(
            filename=settings.FILENAME_LINUXDISTRIBUTION)

    ## Write commands to logfile ##
    command_variable_names = sorted([x for x in list(locals()) if x.startswith("command_")])
    all_commands_string = ""
    for name in command_variable_names:
        all_commands_string += "{} {}\n".format(name, locals()[name])
    with open(settings.FILENAME_COMMANDS, 'w') as commandfile:
        commandfile.write(all_commands_string)
    
    #### Start up CAN receiving #####
    processes = {}
    print("\n\n  ** Start CAN receiver setup ** ")

    #process_cansetup_receiver = subprocess.Popen([command_cansetup_receiver], shell=True)  check return code! TODO
    #process_cansetup_sender = subprocess.Popen([command_cansetup_sender], shell=True) check return code! TODO

    print("    --> Running:", command_cpufreq)
    pr = subprocess.Popen([command_cpufreq], shell=True, preexec_fn=os.setsid)
    pr.wait()

    print("    --> Running:", command_ps)
    pr = subprocess.Popen([command_ps], shell=True, preexec_fn=os.setsid)
    pr.wait()

    print("    --> Running:", command_uname)
    pr = subprocess.Popen([command_uname], shell=True, preexec_fn=os.setsid)
    pr.wait()

    print("    --> Running:", command_linuxdistribution)
    pr = subprocess.Popen([command_linuxdistribution], shell=True, preexec_fn=os.setsid)
    pr.wait()

    time.sleep(settings.DELAY_CAN_SETUP)

    print("    --> Running:", command_ifconfig)
    pr = subprocess.Popen([command_ifconfig], shell=True, preexec_fn=os.setsid)
    pr.wait()

    print("    --> Running:", command_candump)
    processes['candump'] = subprocess.Popen([command_candump], shell=True, preexec_fn=os.setsid, stderr=subprocess.PIPE)  # Suppress stderr

    print("    --> Running:", command_mosquitto_sub)
    processes['mosquitto_sub'] = subprocess.Popen([command_mosquitto_sub], shell=True, preexec_fn=os.setsid)
    time.sleep(settings.DELAY_MQTT_LOG_LENGTH_START)

    print("    --> Running:", command_mqtt_log_length)
    processes['mqtt_log_length'] = subprocess.Popen([command_mqtt_log_length], shell=True, preexec_fn=os.setsid)

    print("    --> Running:", command_canadapter)
    processes['canadapter'] = subprocess.Popen([command_canadapter], shell=True, preexec_fn=os.setsid)

    #### Start up CAN sending #####
    time.sleep(settings.DELAY_CAN_SENDER_START)
    print("\n\n  ** Start CAN sender ** ")
    if settings.USE_REMOTE_CAN_SENDER:
        print("    --> Running on remote machine:", command_cangen)
        can_sender_machine = paramiko.SSHClient()
        can_sender_machine.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        can_sender_machine.connect(settings.CAN_SENDER_HOST,
                                   username=settings.CAN_SENDER_USERNAME,
                                   password=settings.CAN_SENDER_PASSWORD)
        _, cangen_stdout, cangen_stderr = can_sender_machine.exec_command(command_cangen)
    else:
        print("    --> Running on local machine:", command_cangen)
        processes['cangen'] = subprocess.Popen([command_cangen], shell=True, preexec_fn=os.setsid)

    #### Run, and monitor ####
    time.sleep(settings.DELAY_MONITOR_START)
    print(" \n\n ** Start monitoring **")
    print(" Top monitoring time: {} s".format(top_monitoring_time))

    print("    --> Running:", command_top)
    processes['top'] = subprocess.Popen([command_top], shell=True, preexec_fn=os.setsid)

    print("    --> Running:", command_canbusload)
    processes['canbusload'] = subprocess.Popen([command_canbusload], shell=True, preexec_fn=os.setsid)

    ## Wait for completion ##
    print("\n\n ** Waiting for completion. Runtime: {} s **".format(runtime))
    try:
        time.sleep(runtime - settings.DELAY_MONITOR_START)
    except KeyboardInterrupt:
        print("KeyboardInterrupt. Stopping early ...")
        pass
    if settings.USE_REMOTE_CAN_SENDER:
        print(" Wait for remote sender ...")
        try:
            cangen_stdout.readlines()  # Blocks until the command is finished
        except KeyboardInterrupt:
            print("KeyboardInterrupt. Remote sender is still running!")
            pass

    #### Shutdown ####
    print("\n\n ** Waiting for shutdown. Shutdown delay: {} s **".format(settings.DELAY_SHUTDOWN))
    time.sleep(settings.DELAY_SHUTDOWN)

    for proc in processes.values():
        os.killpg(proc.pid, signal.SIGINT)
        proc.terminate()

    print("\n\nThe measurement for cangen delay {} milliseconds (runtime {} s) is now finished.\n".format(cangen_delay, runtime))

