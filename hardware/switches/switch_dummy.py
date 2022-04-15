# -*- coding: utf-8 -*-
"""
Dummy implementation for switching interface.

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

from core.module import Base
from interface.switch_interface import SwitchInterface
from core.configoption import ConfigOption


class SwitchDummy(Base, SwitchInterface):
    """ Methods to control slow switching devices.

    Example config for copy-paste:

    switch_dummy:
        module.Class: 'switches.switch_dummy.SwitchDummy'
        name: 'First'  # optional
        remember_states: True  # optional
    """

    # optional name of the hardware
    _hardware_name = ConfigOption(name='name', default='switch_dummy')
    _switches = {'one': ['down', 'up'], 'two': ['True', 'False'], 'three': ['low', 'middle', 'high']}

    def on_activate(self):
        """ Activate the module and fill status variables.
        """
        self._states = {switch: states[0] for switch, states in self._switches.items()}

    def on_deactivate(self):
        """ Deactivate the module and clean up.
        """
        pass

    def get_name(self):
        """ Name of the hardware as string.

        @return str: The name of the hardware
        """
        return self._hardware_name

    def get_available_states(self):
        """ Names of the states as a dict of tuples.

        The keys contain the names for each of the switches. The values are tuples of strings
        representing the ordered names of available states for each switch.

        @return dict: Available states per switch in the form {"switch": ("state1", "state2")}
        """
        return self._switches.copy()

    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        return self._states[switch]

    def set_state(self, switch, state):
        """ Query state of single switch by name

        @param str switch: name of the switch to change
        @param str state: name of the state to set
        """
        self._states[switch] = state
