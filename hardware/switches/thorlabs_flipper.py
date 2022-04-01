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
from core.statusvariable import StatusVar


class Main(Base, SwitchInterface):
    """ This class is implements communication with Thorlabs MFF101 flipper via Kinesis dll

    Example config for copy-paste:

    flipper:
        module.Class: 'switches.thorlabs_flipper.Main'
        name: 'my_switch'
        dll_folder: 'C:\Program Files\Thorlabs\Kinesis'
        dll_file: 'Thorlabs.MotionControl.FilterFlipper.dll'
        serial_numbers:
            one: 37002739
            two: 37002821
            three: 37002710
        switches:
            one: ['down', 'up']
            two: ['down', 'up']
            three: ['low', 'middle', 'high']

    Description of the hardware provided by Thorlabs:
        These Two-Position, High-Speed Flip Mounts flip lenses, filters, and other optical components into and out of a
         free-space beam.
    """
    name = ConfigOption('name', missing="error")
    dll_folder = ConfigOption('dll_folder', default=r'C:\Program Files\Thorlabs\Kinesis')
    dll_file = ConfigOption('dll_ffile', default='Thorlabs.MotionControl.FilterFlipper.dll')
    serial_numbers = ConfigOption('serial_numbers', missing='error')
    polling_rate_ms = ConfigOption('polling_rate_ms', default=200)
    switches = ConfigOption(name='switches', default={"switch": ("state1", "state2")})

    _states = StatusVar(name='states', default=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dll = None
        self._codes = None
        self._serial_numbers = None

    def on_activate(self):
        """ Module activation method """

        self.switches = self._chk_refine_available_switches(self.switches)

        os.environ['PATH'] = str(self.dll_folder) + os.pathsep + os.environ['PATH']  # needed otherwise dll don't load
        self._dll = ct.cdll.LoadLibrary(self.dll_file)
        self._dll.TLI_BuildDeviceList()

        if len(self.serial_numbers)!=len(self.switches):
            self.log.error("The number of switches configured in the switch states are not equal to length of the serial number list.")

        self._serial_numbers = {}
        for switch, serial_number in self.serial_numbers.items():
            serial_number = ct.c_char_p(str(serial_number).encode('utf-8'))
            self._dll.FF_Open(serial_number)
            self._dll.FF_StartPolling(serial_number, ct.c_int(200))
            self._serial_numbers[switch] = serial_number

        if not self._states:
            self._states = {switch: states[0] for switch, states in self.switches.items()}

    def on_deactivate(self):
        """ Disconnect from hardware on deactivation. """
        for switch, serial_number in self._serial_numbers.items():
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
        return self.switches.copy()

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
        assert switch in self.available_states, f'Invalid switch name: "{switch}"'
        assert state in self.available_states[switch], f'Invalid state name "{state}" for switch "{switch}"'

        if self.available_states[switch][0] == state:
            state_number = 1
        else:
            state_number = 2
        self._dll.FF_MoveToPosition(self._serial_numbers[switch], state_number)
        self._states[switch] = state

    # Hardware function not in switch interface

    def getSwitchState(self, switch):
        """ Get the state of the switch.

          @param int switch: name of the switch

          @return bool: True if 2, False if 1 (homed)
        """
        state = self._dll.FF_GetPosition(self._serial_numbers[switch]) == 2
        return state

    def getCalibration(self, switch, state):
        """ Get calibration parameter for switch.

        Function not used by this module
        """
        return 0

    def setCalibration(self, switch, state, value):
        """ Set calibration parameter for switch.

        Function not used by this module
        """
        return True


    def switchOff(self, switch):
        """ Set the state to off (channel 2)

          @param (int) switch: name of the switch to be switched

          @return (bool): True if suceeds, False otherwise
        """
        setpoint = 1 if not self._is_inverted() else 2
        self._dll.FF_MoveToPosition(self._serial_numbers[switch], setpoint)
        return True

    def getSwitchTime(self, switch):
        """ Give switching time for switch.

          @param int switch: name of the switch

          @return float: time needed for switch state change
        """
        return 500e-3
