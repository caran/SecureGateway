import time
import measurement_utilities

runtime = 30  # seconds
framerates = list(range(40, 280, 20))
delays = [1000/x for x in framerates]

starttime_string = time.strftime("%Y%m%d-%H%M%S")
for cangen_delay in delays:
    measurement_utilities.run_measurement(starttime_string, cangen_delay, runtime)
