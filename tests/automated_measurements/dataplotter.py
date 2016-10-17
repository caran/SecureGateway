import argparse
import glob
import itertools
import json
import os
import sys

assert sys.version_info >= (3, 3, 0), "Python version 3.3 or later required!"

import matplotlib.pyplot as plt


COLORS = ['b', 'g', 'r', 'c', 'm', 'y',
          'gray', 'aquamarine', 'brown', 'gold', 'maroon', 'olive', 'orange', 'pink', 'plum', 'silver', 'tan']
FILEPATTERN_DATA = "md-*.json"
FILEPATTERN_DATA_DIRECTORY = "md-*"


def load_data(directory):

    # Find subdirectories for different measurement sequences
    data_directory_paths = glob.glob(os.path.join(directory, FILEPATTERN_DATA_DIRECTORY))
    if not data_directory_paths:
        raise ValueError("No suitable subfolders found in directory '{}'".format(directory))

    # Read data from files
    measurements = {}
    for data_directory_path in data_directory_paths:
        directory_name = os.path.basename(data_directory_path)

        # Find files with individual data points
        data_file_paths = glob.glob(os.path.join(data_directory_path, FILEPATTERN_DATA))

        if not data_file_paths:
            raise ValueError("No datapoints found in directory '{}'".format(data_directory_path))

        # Load all the datapoints
        data_points = []
        for data_file_path in data_file_paths:
            with open(data_file_path) as data_file:
                datapoint = json.load(data_file)
            data_points.append(datapoint)
        data_points.sort(key=lambda x: x['candump']['framerate'])

        measurements[directory_name] = data_points

    return measurements


def plot_total_cpu(measurements, plotsettings):
    plt.figure(figsize=(8, 6), dpi=72, facecolor="white")
    axes = plt.axes([0.1, 0.1, 0.8, 0.8])

    plotnames = sorted(measurements.keys())
    for plotname in plotnames:
        data_points = measurements[plotname]
        plotcolor = plotsettings['plot_colors'][plotname]
        x = [p['candump']['framerate'] for p in data_points]
        system_cpu = [p['top']['header']['cpu_system_median'] for p in data_points]
        user_cpu = [p['top']['header']['cpu_user_median'] for p in data_points]
        idle_cpu = [p['top']['header']['cpu_idle_median'] for p in data_points]
        plt.plot(x, user_cpu, 'o-', c=plotcolor, label=plotname + " User")
        plt.plot(x, system_cpu, 'x--', c=plotcolor, label=plotname + " System")
        plt.plot(x, idle_cpu, 'x:', c=plotcolor, label=plotname + " Idle")

    axes.set_xlim(plotsettings['xlim'])
    axes.set_ylim([0, 100])
    plt.legend(loc='upper right', shadow=True, fontsize='small')
    plt.ylabel('CPU median (%)')
    plt.xlabel('CAN frame rate (frames/second)')
    plt.savefig('cpu_total.png', dpi=150, bbox_inches='tight')
    plt.close()


def plot_process_cpu(measurements, plotsettings):
    plotnames = sorted(measurements.keys())
    for plotname in plotnames:
        data_points = measurements[plotname]
        processnames = list(data_points[0]['top']['processes'].keys())
        processnames.sort()

        plt.figure(figsize=(8, 6), dpi=72, facecolor="white")
        axes = plt.axes([0.1, 0.1, 0.8, 0.8])

        x = [p['candump']['framerate'] for p in data_points]
        system_cpu = [p['top']['header']['cpu_system_median'] for p in data_points]
        user_cpu = [p['top']['header']['cpu_user_median'] for p in data_points]
        idle_cpu = [p['top']['header']['cpu_idle_median'] for p in data_points]

        color_iterator = itertools.cycle(COLORS)
        for processname in processnames:
            plotcolor = next(color_iterator)
            y = [p['top']['processes'][processname]['cpu_median'] for p in data_points]
            plt.plot(x, y, 'o-', c=plotcolor, label=processname)

        plt.plot(x, user_cpu, 'kx-', label="Total user")
        plt.plot(x, system_cpu, 'kx--', label="Total system")
        plt.plot(x, idle_cpu, 'kx:', label="Total idle")

        axes.set_xlim(plotsettings['xlim'])
        axes.set_ylim([0, 100])
        plt.legend(loc='upper left', shadow=True, fontsize='small')
        plt.ylabel('CPU median (%)')
        plt.xlabel('CAN frame rate (frames/second)')
        filename = "cpu_{}.png".format(plotname)
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()


def plot_process_mem(measurements, plotsettings):
    plotnames = sorted(measurements.keys())
    for plotname in plotnames:
        data_points = measurements[plotname]
        processnames = list(data_points[0]['top']['processes'].keys())
        processnames.sort()

        plt.figure(figsize=(8, 6), dpi=72, facecolor="white")
        axes = plt.axes([0.1, 0.1, 0.8, 0.8])

        x = [p['candump']['framerate'] for p in data_points]
        total_mem = [p['top']['header']['mem_fraction_median']*100 for p in data_points]

        color_iterator = itertools.cycle(COLORS)
        for processname in processnames:
            plotcolor = next(color_iterator)
            y = [p['top']['processes'][processname]['mem_median'] for p in data_points]
            plt.plot(x, y, 'o-', c=plotcolor, label=processname)

        plt.plot(x, total_mem, 'kx--', label="Total")

        axes.set_xlim(plotsettings['xlim'])
        axes.set_ylim([0, 100])
        plt.legend(loc='upper left', shadow=True, fontsize='small')
        plt.ylabel('Memory median (%)')
        plt.xlabel('CAN frame rate (frames/second)')
        filename = "memory_{}.png".format(plotname)
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()


def plot_total_mem(measurements, plotsettings):
    plt.figure(figsize=(8, 6), dpi=72, facecolor="white")
    axes = plt.axes([0.1, 0.1, 0.8, 0.8])

    plotnames = sorted(measurements.keys())
    for plotname in plotnames:
        data_points = measurements[plotname]
        plotcolor = plotsettings['plot_colors'][plotname]
        x = [p['candump']['framerate'] for p in data_points]
        y = [p['top']['header']['mem_fraction_median']*100 for p in data_points]
        plt.plot(x, y, 'o-', c=plotcolor, label=plotname)

    axes.set_xlim(plotsettings['xlim'])
    axes.set_ylim([0, 100])
    plt.legend(loc='lower right', shadow=True, fontsize='small')
    plt.ylabel('Total memory usage (%)')
    plt.xlabel('CAN frame rate (frames/second)')
    plt.savefig('memory_total.png', dpi=150, bbox_inches='tight')
    plt.close()


def plot_mqtt_loss(measurements, plotsettings):
    plt.figure(figsize=(8, 6), dpi=72, facecolor="white")
    axes = plt.axes([0.1, 0.1, 0.8, 0.8])

    plotnames = sorted(measurements.keys())
    for plotname in plotnames:
        data_points = measurements[plotname]
        plotcolor = plotsettings['plot_colors'][plotname]
        x = [p['candump']['framerate'] for p in data_points]
        y = [p['mqtt_message_loss']['lost_mqtt_messages_ratio']*100 for p in data_points]
        plt.plot(x, y, 'o-', c=plotcolor, label=plotname)

    axes.set_xlim(plotsettings['xlim'])
    axes.set_ylim([-1, 25])
    plt.legend(loc='upper right', shadow=True, fontsize='small')
    plt.ylabel('MQTT message loss (%)')
    plt.xlabel('CAN frame rate (frames/second)')
    plt.savefig('loss.png', dpi=150, bbox_inches='tight')
    plt.close()


def plot_lag(measurements, plotsettings):
    accuracy = plotsettings['lag_accuracy']
    plt.figure(figsize=(8, 6), dpi=72, facecolor="white")
    axes = plt.axes([0.1, 0.1, 0.8, 0.8])

    plotnames = sorted(measurements.keys())
    for plotname in plotnames:
        data_points = measurements[plotname]
        plotcolor = plotsettings['plot_colors'][plotname]
        x = [p['candump']['framerate'] for p in data_points]
        y = [p['timing']['lag_stop'] for p in data_points]
        plt.plot(x, y, 'o-', c=plotcolor, label=plotname)

    plt.fill_between(plotsettings['xlim'],  [-accuracy, -accuracy], [accuracy, accuracy],
                     edgecolor='none', facecolor='#BCB6FA')

    axes.set_xlim(plotsettings['xlim'])
    axes.set_ylim([-2*accuracy, plotsettings['lag_ymax']])
    plt.legend(loc='upper right', shadow=True, fontsize='small')
    plt.ylabel('Lag (seconds)')
    plt.xlabel('CAN frame rate (frames/second)')
    plt.savefig('lag.png', dpi=150, bbox_inches='tight')
    plt.close()


def convert_filename_to_text(inputtext):
    return inputtext.split('_', 1)[1].replace('_', ' ')


def sorting_key_throttling(inputtext):
    text = convert_filename_to_text(inputtext)
    try:
        return int(text.split(' ')[0])
    except ValueError:
        return 0


def plot_all(measurements, plotsettings):
    plot_mqtt_loss(measurements, plotsettings)
    plot_process_mem(measurements, plotsettings)
    plot_total_mem(measurements, plotsettings)
    plot_process_cpu(measurements, plotsettings)
    plot_total_cpu(measurements, plotsettings)
    plot_lag(measurements, plotsettings)


def main():
    # Command line arguments
    parser = argparse.ArgumentParser(description='Plot canadapter measurement data')
    parser.add_argument('parentdirectory', help='The parent directory that contains subdirectories with JSON files')
    args = parser.parse_args()

    # Load data
    measurements = load_data(args.parentdirectory)

    # Adjust plot settings
    plotsettings = {}
    plotsettings['xlim'] = [0, 200]
    plotsettings['lag_ymax'] = 4  # seconds
    plotsettings['lag_accuracy'] = 0.2  # seconds
    color_iterator = itertools.cycle(COLORS)
    plotsettings['plot_colors'] = {}
    plotnames = sorted(measurements.keys())
    for plotname in plotnames:
        plotsettings['plot_colors'][plotname] = next(color_iterator)

    # Do the plotting
    os.chdir(args.parentdirectory)
    plot_all(measurements, plotsettings)


if __name__ == '__main__':
    main()
