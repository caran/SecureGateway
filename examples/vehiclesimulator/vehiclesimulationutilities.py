#
# Utilites for a CAN vehicle simulator
#
# Author: Jonas Berg
# Copyright (c) 2015, Semcon Sweden AB
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted
# provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,  this list of conditions and
#    the following disclaimer in the documentation and/or other materials provided with the distribution.
# 3. Neither the name of the Semcon Sweden AB nor the names of its contributors may be used to endorse or
#    promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import random

GEARS_VEHICLESPEED_AT_GIVEN_RPM = [10, 30, 55, 80, 110]  # km/h
GIVEN_RPM = 2000  # RPM
SHIFTPOINTS = [15, 35, 70, 95]  # km/h
SPEED_IDLE = 5.0  # km/h


class VehicleSpeedSimulator:
    """Simulate the speed of a vehicle.

    The step size in the vehicle speed is calculated
    with a normalized distribution using the values:

    * SPEED_STEPSIZE (Should be >0)
    * SPEED_STEPDEVIATION (Should be >0)

    When the speed reaches SPEED_MAX, the speed will start
    to decrease instead. Similarly it starts to increase again
    at SPEED_MIN.

    This class holds no timer or timing information,
    so the average rate of speed change is dependent on
    how frequently you call getNewRandomizedSpeed().

    Attributes:
        currentspeed (float): Vehicle speed in km/h

    """
    SPEED_STEPSIZE = 0.3  # km/h
    SPEED_STEPDEVIATION = 0.9  # km/h
    SPEED_MAX = 110.0  # km/h
    SPEED_MIN = 3.0  # km/h

    def __init__(self):
        self.currentspeed = 0
        self._speed_stepsize_median = self.SPEED_STEPSIZE

    def get_new_randomized_speed(self):
        """Calculate a new vehicle speed.

        Returns the new value of currentspeed in km/h.
        """
        if self.currentspeed > self.SPEED_MAX:
            self._speed_stepsize_median = -self.SPEED_STEPSIZE
        elif self.currentspeed < self.SPEED_MIN:
            self._speed_stepsize_median = self.SPEED_STEPSIZE

        speed_stepsize = random.normalvariate(self._speed_stepsize_median, self.SPEED_STEPDEVIATION)
        self.currentspeed += speed_stepsize
        self.currentspeed = max(0, self.currentspeed)
        return self.currentspeed


class CabinTemperatureSimulator:
    """Simulate the indoor temperature of a vehicle.

    The temperature will increase to TEMPERATURE_HOT,
    but will decrease to TEMPERATURE_COLD when the air conditioner
    is turned on.

    The warming and cooling speeds are affected by GAIN_WARMING and
    GAIN_COOLING. A random temperature noise is added to the measurement.

    This class holds no timer or timing information,
    so the average rate of temperature change is dependent on
    how frequently you call getNewTemperature().

    Attributes:
        temperature (float): Indoor temperature in deg C
        aircondition_state (bool) : Boolean indicating whether the AC is on

    """
    TEMPERATURE_HOT = 32.0  # deg C
    TEMPERATURE_COLD = 18.0  # deg C
    TEMPERATURE_NOISE_DEVIATION = 0.03  # deg C
    GAIN_WARMING = 0.02
    GAIN_COOLING = 0.05

    def __init__(self):
        self.temperature = self.TEMPERATURE_COLD
        self._aircondition_state = False
        self._final_temperature = self.TEMPERATURE_HOT

    @property
    def aircondition_state(self):
        return self._aircondition_state

    @aircondition_state.setter
    def aircondition_state(self, state):
        """Set the air conditioning state of the vehicle.

        Args:
            state (bool): True will turn on the air conditioner

        """
        self._aircondition_state = bool(state)
        if self._aircondition_state:
            self._final_temperature = self.TEMPERATURE_COLD
        else:
            self._final_temperature = self.TEMPERATURE_HOT

    def get_new_temperature(self):
        """Calculate a new temperature.

        Returns the new temperature in deg C.
        """
        temperature_error = self._final_temperature - self.temperature

        if temperature_error > 0:
            temperature_step = temperature_error*self.GAIN_WARMING
        else:
            temperature_step = temperature_error*self.GAIN_COOLING

        temperature_noise = random.normalvariate(0, self.TEMPERATURE_NOISE_DEVIATION)

        self.temperature += temperature_step + temperature_noise
        return self.temperature


def calculate_engine_speed(vehiclespeed):
    """Calculate the simulated enginespeed.

    Args:
        vehiclespeed (float): Speed in km/h

    Returns: Engine speed (float) in RPM (revolutions per minute)

    """
    vehiclespeed = max(vehiclespeed, SPEED_IDLE)

    for i, shiftpoint in enumerate(SHIFTPOINTS):
        gear = i + 1
        if vehiclespeed < shiftpoint:
            break
        gear += 1

    vehiclespeed_at_given_rpm = GEARS_VEHICLESPEED_AT_GIVEN_RPM[gear-1]
    enginespeed = GIVEN_RPM * vehiclespeed / float(vehiclespeed_at_given_rpm)
    return enginespeed
