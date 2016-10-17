#
# Beaglebone taxi sign driver
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
#
#
# For Python 2.7 and up (incl. 3.x)
# The script must be executed with root permissions
#
# Connect a relay driver from Beaglebone port8 pin3.
# The voltage is 3.3 V on the pin.
# The output is gpmc_ad6 = GPIO1_6
# This is GPIO 38 (1*32 + 6)
#
# +5 V is available on port9 pin7 and pin8.
# GND is available on port9 pin1 and pin2.
#
# If the relay and its driver circuit are connected such
# that the taxi sign turns off for GPIO=high,
# then use IS_INVERTED = True
#
# If using a LED instead, connect it to ground via 470 Ohm.
#

import output_pin_driver

# Hardware-describing constants
GPIO_NUMBER = 60
IS_INVERTED = True


class Taxisign(object):
    """Taxi sign representation.

    For controlling a Taxi sign from a Beaglebone. This is basically the
    Beaglebone output_pin_driver, together with hardware-describing constants.

    Module constants describing the hardware:
     * GPIO_NUMBER (int): GPIO number for pin connected to relay driver circuit.
     * IS_INVERTED (bool): Set to True if the relay and its driver circuit
       are connected such that the taxi sign turns off for GPIO=high.

    Attributes:
     * state (bool): Set to True to turn on the taxi sign.

    """

    def __init__(self):
        self._pin = output_pin_driver.Outputpin(GPIO_NUMBER)
        self._is_inverted = IS_INVERTED

        self.state = False

    @property
    def state(self):
        return self._pin.state ^ self._is_inverted  # XOR: Apply inversion if required

    @state.setter
    def state(self, value):
        self._pin.state = value ^ self._is_inverted  # XOR: Apply inversion if required

    def loop(self):
        # Graphical taxi sign simulators must update the GUI frequently. Not required here.
        pass

#########################
## Testing the module  ##
#########################

if __name__ == '__main__':
    import time

    sign = Taxisign()

    sign.state = True
    time.sleep(1)

    sign.state = False
    time.sleep(1)

    sign.state = True
    time.sleep(1)

    sign.state = False
