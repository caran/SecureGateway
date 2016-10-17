# Register a SIGTERM signal handler in order for 'coverage' tool
# to function properly

import signal
import sys


def signal_handler(signum, frame):
    print('Handled Linux signal number:', signum)
    sys.exit()
signal.signal(signal.SIGTERM, signal_handler)


# Run the example
import minimaltaxisign
