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
from interface.laser_interface import LaserInterface
from interface.simple_laser_interface import LaserState
from interface.simple_laser_interface import ShutterState

import visa
import time

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

    def on_deactivate(self):
        """ Deactivate module.
        """

        self._device.close()
    
    def set_laser_state(self, laser_state):
        """Setter method to control the laser state (ON or OFF).

        @param (LaserState) laser_state: laser state (ON or OFF).
        """
        self._device.query('L={}'.format(laser_state))

    def get_laser_state(self):
        """Getter method to know the laser state (ON or OFF).

        @return (LaserState) laser_state: laser state (ON or OFF).
        """
        laser_state = int(self._device.query('?L'))
        return laser_state

    def set_wavelength(self, wavelength):
        """Setter method to control the laser wavelength in m if tunable.

        @param (float) wavelength: laser wavelength in m.
        """
        self._device.query('VW={}'.format(wavelength*1e9))

    def get_wavelength(self):
        """Getter method to know the laser wavelength in m if tunable.

        @return (float) wavelength: laser wavelength in m.
        """
        wavelength = float(self._device.query('?VW'))*1e-9
        return wavelength

    def set_power(self, power):
        """Setter method to control the laser power in W if tunable.

        @param (float) power: laser power in W.
        """
        pass

    def get_power(self):
        """Getter method to know the laser power in W if tunable.

        @return (float) power: laser power in W.
        """
        power = float(self._device.query('?UF'))*1e-3
        return power

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