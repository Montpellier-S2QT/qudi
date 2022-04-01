# -*- coding: utf-8 -*-
"""
This module controls the Coherent OBIS laser.

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
from core.configoption import ConfigOption
from interface.laser_interface import LaserInterface, LaserState, ShutterState, Constraints

import visa

class Chameleon(Base, LaserInterface):

    """ Implements the Coherent Chameleon laser.

    Example config for copy-paste:

    chameleon:
        module.Class: 'laser.coherent_chameleon.Chameleon'
        port: 'COM1'

    """

    _port = ConfigOption('port', missing='error')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_activate(self):
        """ Activate module.
        """
        self._rm = visa.ResourceManager()

        try:
            self._device = self._rm.open_resource(self._port)
        except:
            self.log.error("The device has not been found")
        self._device.read_termination = '\r\n'
        self._device.baud_rate = 19200

        self._device.query('E=0')
        self._device.query('>=0')

        self._constraints = self._build_constraints()

    def on_deactivate(self):
        """ Deactivate module.
        """

        self._device.close()

    def get_constraints(self):
        """ Returns all the fixed parameters of the hardware which can be used by the logic.

        @return (Constraints): An object of class Constraints containing all fixed parameters of the hardware
        """
        return self._constraints

    def _build_constraints(self):
        """ Internal method that build the constraints once at initialisation

         This makes multiple call to the DLL, so it will be called only once by on_activate
         """
        constraints = Constraints()
        constraints.has_shutter = True
        constraints.tunable_power = False
        constraints.tunable_wavelength = True
        constraints.wavelength_range = self._get_wavelength_range()

        return constraints
    
    def set_laser_state(self, laser_state):
        """Setter method to control the laser state (ON or OFF).

        @param (LaserState|int) laser_state: laser state (ON or OFF).
        """
        self._device.query('L={}'.format(laser_state))

    def get_laser_state(self):
        """Getter method to know the laser state (ON or OFF).

        @return (LaserState|int) laser_state: laser state (ON or OFF).
        """
        laser_state = int(self._device.query('?L'))
        return laser_state

    def set_wavelength(self, wavelength):
        """Setter method to control the laser wavelength in m if tunable.

        @param (float) wavelength: laser wavelength in m.
        """
        self._device.query('VW={}'.format(int(wavelength*1e9)))

    def get_wavelength(self):
        """Getter method to know the laser wavelength in m if tunable.

        @return (float) wavelength: laser wavelength in m.
        """
        wavelength = float(self._device.query('?VW'))*1e-9
        return wavelength

    def get_power(self):
        """Getter method to know the laser current power in W if tunable.

        @return (float) power: laser power in W.
        """
        power = float(self._device.query('?UF'))*1e-3
        return power

    def set_power_setpoint(self, power_setpoint):
        """Setter method to control the laser power setpoint in W if tunable.

        @param (float) power setpoint: laser power in W.
        """
        pass

    def get_power_setpoint(self):
        """Getter method to know the laser power setpoint in W if tunable.

        @return (float) power setpoint: laser power setpoint in W.
        """
        pass

    def set_shutter_state(self, shutter_state):
        """Setter method to control the laser shutter if available.

        @param (ShutterState) shutter_state: shutter state (OPEN/CLOSE/AUTO).
        """
        self._device.query('S={}'.format(shutter_state))

    def get_shutter_state(self):
        """Getter method to control the laser shutter if available.

        @return (ShutterState) shutter_state: shutter state (OPEN/CLOSE/AUTO).
        """
        shutter_state = int(self._device.query('?S'))
        return shutter_state

    def _get_wavelength_range(self):
        """Getter method to get the wavelength range available in the laser.

        @return (tuple) wavelength range: wavelength range (min, max)
        """
        wavelength_min = float(self._device.query('?TMIN'))*1e-9
        wavelength_max = float(self._device.query('?TMAX'))*1e-9
        return (wavelength_min, wavelength_max)