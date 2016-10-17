#
# Beaglebone GPIO output pin driver
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
# For Python 2.7 and up (incl. 3.x)
#

FILE_FOR_GPIO_EXPORT                    = '/sys/class/gpio/export'
TEMPLATE_FOR_GPIO_PIN_DIRECTION_FILE    = '/sys/class/gpio/gpio{}/direction'
TEMPLATE_FOR_GPIO_PIN_VALUE_FILE        = '/sys/class/gpio/gpio{}/value'

DIRECTION_OUT   = 'out'
GPIO_STATE_ON   = '1'
GPIO_STATE_OFF  = '0'
MODE_FILE_WRITE = 'w'

import errno


class Outputpin(object):
    """GPIO output pin representation.

    For controlling a GPIO output pin on a Beaglebone.
    Note that root permissions are required.

    Attributes:
     * state (bool): Turn on the GPIO output pin if the value is True.

    """

    def __init__(self, GPIO_number):
        self._state = False
        self._GPIO_number = GPIO_number

        # Export the GPIO pin to Linux userspace
        try:
            with open(FILE_FOR_GPIO_EXPORT, MODE_FILE_WRITE) as f:
                f.write(str(self._GPIO_number))
        except IOError as e:
            if e.errno != errno.EBUSY:  # EBUSY: Pin is already exported.
                raise

        # Set pin in digital output mode
        file_for_gpio_pin_direction = TEMPLATE_FOR_GPIO_PIN_DIRECTION_FILE.format(self._GPIO_number)
        with open(file_for_gpio_pin_direction, MODE_FILE_WRITE) as f:
            f.write(DIRECTION_OUT)

        # Set initial state
        self.state = False

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        if value:
            filetext = GPIO_STATE_ON
            self._state = True
        else:
            filetext = GPIO_STATE_OFF
            self._state = False

        # Write pin value to the file-like driver interface
        file_for_gpio_pin_value = TEMPLATE_FOR_GPIO_PIN_VALUE_FILE.format(self._GPIO_number)
        with open(file_for_gpio_pin_value, MODE_FILE_WRITE) as f:
            f.write(filetext)


########################################################
# Testing the module                                   #
#                                                      #
# Connect a LED from port8 pin3 to ground via 470 Ohm. #
# The voltage is 3.3 V on the pin.                     #
# The output is gpmc_ad6 = GPIO1_6                     #
# This is GPIO 38 (1*32 + 6)                           #
#                                                      #
########################################################

if __name__ == '__main__':
    import time
    pin = Outputpin(38)

    pin.state = True
    time.sleep(1)
    pin.state = False
    time.sleep(1)
    pin.state = True
    time.sleep(1)
    pin.state = False
