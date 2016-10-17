import time
import measurement_utilities

runtime = 100  # seconds
framerates = [1, 2, 3, 4] + list(range(5, 205, 5))
delays = [1000/x for x in framerates]

starttime_string = time.strftime("%Y%m%d-%H%M%S")
for cangen_delay in delays:
    measurement_utilities.run_measurement(starttime_string, cangen_delay, runtime)
