import sys

assert sys.version_info >= (3, 2, 0), "Python version 3.2 or later required!"

import matplotlib.pyplot as plt
import numpy

import vehiclesimulationutilities

  ## Create graph ##
fig = plt.figure(figsize=(8, 6), dpi=72, facecolor="white")
axes = plt.axes([0.1, 0.1, 0.8, 0.8])

  ## Data ##
shift_points_etc = [vehiclesimulationutilities.SPEED_IDLE] + vehiclesimulationutilities.SHIFTPOINTS
SPEED_MAX = 130  # km/h
SPEED_STEP = 0.1  # km/h

  ## Plot resulting enginespeed ##
vehiclespeedvector = numpy.arange(0, SPEED_MAX, SPEED_STEP)
enginespeedvector = []
for vehiclespeed in vehiclespeedvector:
    enginespeedvector.append(vehiclesimulationutilities.calculate_engine_speed(vehiclespeed))
plt.plot(vehiclespeedvector,  enginespeedvector, '-k', linewidth=2)

  ## Fit lines ##
for slopespeed in vehiclesimulationutilities.GEARS_VEHICLESPEED_AT_GIVEN_RPM:
  plt.plot([0, slopespeed],  [0, vehiclesimulationutilities.GIVEN_RPM], '--k')

for shiftpoint in shift_points_etc:
    plt.plot([shiftpoint, shiftpoint], [0, vehiclesimulationutilities.GIVEN_RPM], '--b')

  ## Annotations ##
for i, slopespeed in enumerate(vehiclesimulationutilities.GEARS_VEHICLESPEED_AT_GIVEN_RPM):
    plt.text(slopespeed-3, vehiclesimulationutilities.GIVEN_RPM, str(i+1))

for shiftpoint in shift_points_etc:
    plt.text(shiftpoint+1, 80, str(shiftpoint), fontsize=8)

  ## Axis limits ##
axes.set_xlim(0, SPEED_MAX)
axes.set_ylim(0, 3200)

  ## Annotations and descriptive text ##
plt.title('Simulated gear box')
plt.xlabel('Vehicle speed (km/h)')
plt.ylabel('Engine speed (RPM)')

  ## Save graph ##
plt.savefig('EnginespeedVehiclespeed.png', dpi=150, bbox_inches='tight')
plt.show()
