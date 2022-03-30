# -*- coding: utf-8 -*-
"""
Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import os
import ctypes as ct
from operator import xor
from core.module import Base
from core.configoption import ConfigOption
from interface.switch_interface import SwitchInterface


class Main(Base, SwitchInterface):
    """ This class is implements communication with Thorlabs MFF101 flipper via Kinesis dll

    Example config for copy-paste:

    flipper:
        module.Class: 'switches.thorlabs_flipper.Main'
        dll_folder: 'C:\Program Files\Thorlabs\Kinesis'
        serial_numbers: [000000123]

    Description of the hardware provided by Thorlabs:
        These Two-Position, High-Speed Flip Mounts flip lenses, filters, and other optical components into and out of a
         free-space beam.
    """
    name = ConfigOption('name', missing="error")
    dll_folder = ConfigOption('dll_folder', default=r'C:\Program Files\Thorlabs\Kinesis')
    dll_file = ConfigOption('dll_ffile', default='Thorlabs.MotionControl.FilterFlipper.dll')
    serial_numbers = ConfigOption('serial_numbers', missing='error')
    polling_rate_ms = ConfigOption('polling_rate_ms', default=200)
    invert_axis = ConfigOption('invert_axis', default=[False])
    switch_states = ConfigOption(name='switch_states', default=['Down', 'Up'])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dll = None
        self._codes = None
        self._serial_numbers = None

    def on_activate(self):
        """ Module activation method """
        os.environ['PATH'] = str(self.dll_folder) + os.pathsep + os.environ['PATH']  # needed otherwise dll don't load
        self._dll = ct.cdll.LoadLibrary(self.dll_file)
        self._dll.TLI_BuildDeviceList()

        if len(self.serial_numbers)!=len(self.states):
            self.log.error("The number of switches configured in the switch states are not equal to length of the serial number list.")

        self._serial_numbers = []
        for serial_number in self.serial_numbers:
            serial_number = ct.c_char_p(str(serial_number).encode('utf-8'))
            self._dll.FF_Open(serial_number)
            self._dll.FF_StartPolling(serial_number, ct.c_int(200))
            self._serial_numbers.append(serial_number)

    def on_deactivate(self):
        """ Disconnect from hardware on deactivation. """
        for serial_number in self._serial_numbers:
            self._dll.FF_ClearMessageQueue(serial_number)
            self._dll.FF_StopPolling(serial_number)
            self._dll.FF_Close(serial_number)

    @property
    def name(self):
        """ Name of the hardware as string.

        @return str: The name of the hardware
        """
        return self.name

    @property
    def available_states(self):
        """ Names of the states as a dict of tuples.

        The keys contain the names for each of the switches. The values are tuples of strings
        representing the ordered names of available states for each switch.

        @return dict: Available states per switch in the form {"switch": ("state1", "state2")}
        """
        return self.switch_states.copy()

    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        assert switch in self.available_states, f'Invalid switch name: "{switch}"'
        return self._states[switch]

    def set_state(self, switch, state):
        """ Query state of single switch by name

        @param str switch: name of the switch to change
        @param str state: name of the state to set
        """
        avail_states = self.available_states
        assert switch in avail_states, f'Invalid switch name: "{switch}"'
        assert state in avail_states[switch], f'Invalid state name "{state}" for switch "{switch}"'
        self._states[switch] = state

        setpoint = 2 if not self._is_inverted() else 1
        self._dll.FF_MoveToPosition(self._serial_numbers[switchNumber], setpoint)
        return True

    # Hardware function not in switch interface

    def _is_inverted(self, axis=0):
        """ Helper function to get if axis is inverted in config """
        return self.invert_axis is not None and len(self.invert_axis) > axis and bool(self.invert_axis[axis])

    def getSwitchState(self, switchNumber):
        """ Get the state of the switch.

          @param int switchNumber: index of switch

          @return bool: True if 2, False if 1 (homed)
        """
        state = self._dll.FF_GetPosition(self._serial_numbers[switchNumber]) == 2
        return xor(state, self._is_inverted(switchNumber))

    def getCalibration(self, switchNumber, state):
        """ Get calibration parameter for switch.

        Function not used by this module
        """
        return 0

    def setCalibration(self, switchNumber, state, value):
        """ Set calibration parameter for switch.

        Function not used by this module
        """
        return True


    def switchOff(self, switchNumber):
        """ Set the state to off (channel 2)

          @param (int) switchNumber: number of switch to be switched

          @return (bool): True if suceeds, False otherwise
        """
        setpoint = 1 if not self._is_inverted() else 2
        self._dll.FF_MoveToPosition(self._serial_numbers[switchNumber], setpoint)
        return True

    def getSwitchTime(self, switchNumber):
        """ Give switching time for switch.

          @param int switchNumber: number of switch

          @return float: time needed for switch state change
        """
        return 500e-3
