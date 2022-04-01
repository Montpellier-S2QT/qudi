# -*- coding: utf-8 -*-
"""
Interface file for lasers where current and power can be set.

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

from enum import Enum
from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass

class ShutterState(Enum):
    CLOSED = 0
    OPEN = 1
    ALIGNMENT = 2

class LaserState(Enum):
    OFF = 0
    ON = 1

class Constraints:
    """ Class defining formally the hardware constraints """
    def __init__(self):
        self.tunable_power = None        # If the laser power is tunable
        self.tunable_wavelength = None   # If the laser wavelength is tunable
        self.has_shutter = None          # If the laser has shutter
        self.power_range = None          # The laser power range min and max if tunable
        self.wavelength_range = None     # The laser wavelength range min and max if tunable

class LaserInterface(metaclass=InterfaceMetaclass):
    """ This interface can be used to control a laser. It handles power control, wavelength control, control modes and
    shutter states.

    This interface is useful for a general laser that you can find in a lab.
    """

    @abstract_interface_method
    def get_constraints(self):
        """ Returns all the fixed parameters of the hardware which can be used by the logic.

        @return (Constraints): An object of class Constraints containing all fixed parameters of the hardware
        """
        pass

    @abstract_interface_method
    def set_laser_state(self, laser_state):
        """Setter method to control the laser state (ON or OFF).

        @param (LaserState) laser_state: laser state (ON or OFF).
        """
        pass

    @abstract_interface_method
    def get_laser_state(self):
        """Getter method to know the laser state (ON or OFF).

        @return (LaserState) laser_state: laser state (ON or OFF).
        """
        pass

    @abstract_interface_method
    def set_wavelength(self, wavelength):
        """Setter method to control the laser wavelength in m if tunable.

        @param (float) wavelength: laser wavelength in m.
        """
        pass

    @abstract_interface_method
    def get_wavelength(self):
        """Getter method to know the laser wavelength in m if tunable.

        @return (float) wavelength: laser wavelength in m.
        """
        pass

    @abstract_interface_method
    def set_power_setpoint(self, power):
        """Setter method to control the laser power setpoint in W if tunable.

        @param (float) power setpoint: laser power in W.
        """
        pass

    @abstract_interface_method
    def get_power_setpoint(self):
        """Getter method to know the laser power setpoint in W if tunable.

        @return (float) power setpoint: laser power setpoint in W.
        """
        pass

    @abstract_interface_method
    def get_power(self):
        """Getter method to know the laser current power in W if tunable.

        @return (float) power: laser power in W.
        """
        pass

    @abstract_interface_method
    def set_shutter_state(self, shutter_state):
        """Setter method to control the laser shutter if available.

        @param (ShutterState) shutter_state: shutter state (OPEN/CLOSED/AUTO).
        """
        pass

    @abstract_interface_method
    def get_shutter_state(self):
        """Getter method to control the laser shutter if available.

        @return (ShutterState) shutter_state: shutter state (OPEN/CLOSED/AUTO).
        """
        pass