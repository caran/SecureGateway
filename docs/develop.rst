Developer information
=====================

Measuring test coverage
-----------------------
In order to have the 'coverage' program to measure also the Python scripts that are running in subprocesses,
you need to adjust :file:`sitecustomize.py` file. That will start the 'coverage' program when the appropriate
environment variable is set.

Add this to your :file:`sitecustomize.py` file::

    try:
        import coverage
        coverage.process_startup()
    except ImportError:
        pass

For more details, see http://coverage.readthedocs.org/en/latest/subprocess.html

Note that the Python programs running in the subprocess must handle SIGTERM.
For example, to measure the test coverage for the :file:`minimaltaxisign.py` file,
insert this code::

    import signal
    import sys

    def signal_handler(signum, frame):
        print('Handled Linux signal number:', signum)
        sys.exit()

    signal.signal(signal.SIGTERM, signal_handler)

Alternatively, put it in some other code that imports your program.

It seems important to terminate the process gently::

    myprocess.send_signal(signal.SIGINT)


TODO-list
----------
Improve documentation:

* Update history release list.

Verify that the canadapter script is installed.


For next release
------------------
Implement:

* JSON schema verification of settings file
* Add support for another conversion parameter in the JSON file.
  As the "canMultiplier" is used to multiply a CAN signal when converting to
  MQTT messages, we should have a parameter to add a constant value (offset)
  when converting to MQTT messages.

Documentation and test improvements:

* Schema documentation.
* Describe logging in systemd.
* Network discovery using Avahi.
* Dynamically change access to applications.
* Test output_pin_driver using http://stackoverflow.com/questions/8166633/mocking-file-objects-or-iterables-in-python .
* Try running several canadapters on a single Beaglebone.
