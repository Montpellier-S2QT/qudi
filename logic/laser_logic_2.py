#-*- coding: utf-8 -*-
"""
Laser management.

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

import time
import numpy as np
from qtpy import QtCore

from core.connector import Connector
from core.configoption import ConfigOption
from logic.generic_logic import GenericLogic
from core.statusvariable import StatusVar
from interface.laser_interface import LaserInterface, ShutterState, LaserState


class LaserLogic(GenericLogic):
    """ Logic module to control a laser.

    laser_logic:
        module.Class: 'laser_logic.LaserLogic'
        connect:
            laser: 'mylaser'
    """

    _laser = Connector(interface='LaserInterface')
    _wavelength = StatusVar('wavelength', None)
    _power_setpoint = StatusVar('power_setpoint', None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_activate(self):
        """ Activate module.
        """
        self._constraints = self._laser().get_constraints()

        if self._wavelength == None:
            self._wavelength = self._laser().get_wavelength()
        else:
            self.wavelength = self._wavelength

        if self._power_setpoint == None:
            self._power_setpoint = self._laser().get_power_setpoint()
        else:
            self.power_setpoint = self._power_setpoint


    def on_deactivate(self):
        """ Deactivate module.
        """

    @property
    def laser_state(self):
        """Getter method to know the laser state (ON or OFF).

        @return (LaserState) laser_state: laser state (ON or OFF).
        """
        LaserState.__members__()
        laser_state = self._laser.get_laser_state()


    @laser_state.setter
    def laser_state(self, laser_state):
        """Setter method to control the laser state (ON or OFF).

        @param (LaserState) laser_state: laser state (ON or OFF).
        """
        pass

    @property
    def wavelength(self):
        """Getter method to know the laser wavelength in m if tunable.

        @return (float) wavelength: laser wavelength in m.
        """
        self._wavelength = self._laser().get_wavelength()
        return self._wavelength

    @wavelength.setter
    def wavelength(self, wavelength):
        """Setter method to control the laser wavelength in m if tunable.

        @param (float) wavelength: laser wavelength in m.
        """
        if not self._constraints.wavelength_tunable:
            self.log.warning('The laser hardware module is not wavelength tunable. The wavelength cannot be changed.')
            return
        wavelength = float(wavelength)
        wavelength_min, wavelength_max = self._constraints.wavelength_range
        if not wavelength_min <= wavelength < wavelength_max:
            self.log.error('Wavelength value is not correct : it must be in range {} to {} '
                           .format(wavelength_min, wavelength_max))
            return
        self._laser().set_wavelength(wavelength)
        self._wavelength = self._laser().get_wavelength()
        self.sigUpdateSettings.emit()

    @property
    def power(self):
        """Getter method to know the laser power in W if tunable.

        @return (float) power: laser power in W.
        """
        return self._laser().get_power()

    @property
    def power_setpoint(self):
        """Getter method to know the laser power setpoint in W if tunable.

        @return (float) power setpoint: laser power setpoint in W.
        """
        self._power_setpoint = self._laser().get_power_setpoint()
        return self._power_setpoint

    @power_setpoint.setter
    def power_setpoint(self, power_setpoint):
        """Setter method to control the laser power_setpoint in W if tunable.

        @param (float) power_setpoint: laser power_setpoint in W.
        """
        if not self._constraints.power_tunable:
            self.log.warning('The laser hardware module is not power tunable. The laser power cannot be changed.')
            return
        power_setpoint = float(power_setpoint)
        power_min, power_max = self._constraints.power_range
        if not power_min <= power_setpoint < power_max:
            self.log.error('Power value is not correct : it must be in range {} to {} '
                           .format(power_min, power_max))
            return
        self._laser().set_power_setpoint(power_setpoint)
        self._power_setpoint = self._laser().get_power_setpoint()
        self.sigUpdateSettings.emit()

    @property
    def shutter_state(self):
        """Getter method to control the laser shutter if available.

        @return (ShutterState) shutter_state: shutter state (OPEN/CLOSED/AUTO).
        """
        pass

    @shutter_state.setter
    def shutter_state(self, shutter_state):
        """Setter method to control the laser shutter if available.

        @param (ShutterState) shutter_state: shutter state (OPEN/CLOSED/AUTO).
        """
        pass