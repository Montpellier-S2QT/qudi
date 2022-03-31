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

import serial
import time

class Chameleon(Base, LaserInterface):

    """ Implements the Coherent OBIS laser.

    Example config for copy-paste:

    chameleon:
        module.Class: 'laser.coherent_chameleon.Chameleon'
        com_port: 'COM3'

    """

    _com_port = ConfigOption('com_port', missing='error')

    def on_activate(self):
        """ Activate module.
        """
        self.obis = serial.Serial(self._com_port, timeout=1)

        connected = self.connect_laser()

        if not connected:
            self.log.error('Laser does not seem to be connected.')
            return -1
        else:
            self._model_name = self._communicate('SYST:INF:MOD?')
            return 0

    def on_deactivate(self):
        """ Deactivate module.
        """

        self.disconnect_laser()
    
    def get_power_range(self):
        """ Return laser power
        @return tuple(p1, p2): Laser power range in watts
        """
        pass
    
    def get_power(self):
        """ Return laser power
        @return float: Actual laser power in watts
        """
        pass
    
    def set_power(self, power):
        """ Set laer power ins watts
          @param float power: laser power setpoint in watts
    
        """
        pass
    
    def get_power_setpoint(self):
        """ Return laser power setpoint
        @return float: Laser power setpoint in watts
        """
        pass
    
    
    def get_wavelength(self):
        """ Return laser wavelength in m
        @return float: Actual laser wavelength in m
        """
        pass
    
    
    def set_wavelength(self, wavelength):
        """ Set laser wavelength in m
          @param float wavelength: laser wavelength in m
    
        """
        pass
    
    
    def get_current_unit(self):
        """ Return laser current unit
        @return str: unit
        """
        pass
    
    
    def get_current(self):
        """ Return laser current
        @return float: actual laser current as ampere or percentage of maximum current
        """
        pass
    
    
    def get_current_range(self):
        """ Return laser current range
        @return tuple(c1, c2): Laser current range in current units
        """
        pass
    
    def get_current_setpoint(self):
        """ Return laser current
        @return float: Laser current setpoint in amperes
        """
        pass
    
    def set_current(self, current):
        """ Set laser current
        @param float current: Laser current setpoint in amperes
        @return float: Laser current setpoint in amperes
        """
        pass
    
    def allowed_control_modes(self):
        """ Get available control mode of laser
          @return list: list with enum control modes
        """
        pass
    
    def get_control_mode(self):
        """ Get control mode of laser
          @return enum ControlMode: control mode
        """
        pass
    
    def set_control_mode(self, control_mode):
        """ Set laser control mode.
          @param enum control_mode: desired control mode
          @return enum ControlMode: actual control mode
        """
        pass
    
    def on(self):
        """ Turn on laser. Does not open shutter if one is present.
          @return enum LaserState: actual laser state
        """
        pass
    
    def off(self):
        """ Turn ooff laser. Does not close shutter if one is present.
          @return enum LaserState: actual laser state
        """
        pass
    
    def get_laser_state(self):
        """ Get laser state.
          @return enum LaserState: laser state
        """
        pass
    
    def set_laser_state(self, state):
        """ Set laser state.
          @param enum state: desired laser state
          @return enum LaserState: actual laser state
        """
        pass
    
    def get_shutter_state(self):
        """ Get shutter state. Has a state for no shutter present.
          @return enum ShutterState: actual shutter state
        """
        pass
    

    def set_shutter_state(self, state):
        """ Set shutter state.
          @param enum state: desired shutter state
          @return enum ShutterState: actual shutter state
        """
        pass
    

    def get_temperatures(self):
        """ Get all available temperatures from laser.
          @return dict: dict of name, value for temperatures
        """
        pass
    

    def get_temperature_setpoints(self):
        """ Get all available temperature setpoints from laser.
          @return dict: dict of name, value for temperature setpoints
        """
        pass
    

    def set_temperatures(self, temps):
        """ Set laser temperatures.
          @param temps: dict of name, value to be set
          @return dict: dict of name, value of temperatures that were set
        """
        pass
    

    def get_extra_info(self):
        """ Show dianostic information about lasers.
          @return str: diagnostic info as a string
        """
        pass
