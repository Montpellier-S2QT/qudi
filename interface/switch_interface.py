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

from core.interface import abstract_interface_method, interface_method
from core.meta import InterfaceMetaclass


class SwitchInterface(metaclass=InterfaceMetaclass):
    """ Methods to control slow (ie. second timescale) switching devices.

    """

    @abstract_interface_method
    def get_name(self):
        """ Name of the hardware as string.

        @return str: The name of the hardware
        """
        pass

    @abstract_interface_method
    def get_available_states(self):
        """ Names of the states as a dict of tuples.

        The keys contain the names for each of the switches. The values are tuples of strings
        representing the ordered names of available states for each switch.

        @return dict: Available states per switch in the form {"switch": ("state1", "state2")}
        """
        pass

    @abstract_interface_method
    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        pass

    @abstract_interface_method
    def set_state(self, switch, state):
        """ Query state of single switch by name

        @param str switch: name of the switch to change
        @param str state: name of the state to set
        """
        pass

    # Non-abstract default implementations below
    # If the hardware can get/set multiple switch at once, and if bandwidth is limited, the two function below can
    # be redefined.

    @interface_method
    def get_states(self):
        """ The current states the hardware is in as state dictionary with switch names as keys and
        state names as values.

        @return dict: All the current states of the switches in the form {"switch": "state"}
        """
        return {switch: self.get_state(switch) for switch in self.available_states}

    @interface_method
    def set_states(self, state_dict):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict state_dict: state dict of the form {"switch": "state"}
        """
        for switch, state in state_dict.items():
            self.set_state(switch, state)

