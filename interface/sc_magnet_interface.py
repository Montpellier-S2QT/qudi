# -*- coding: utf-8 -*-
"""
This file contains the Qudi Interface file to control a superconducting magnet.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import abc
from core.meta import InterfaceMetaclass
from core.util.helpers import in_range

class SuperConductingMagnetInterface(metaclass=InterfaceMetaclass):
    """ This is the Interface class to define the controls for the devices
        controlling the magnetic field.
    """
    
    _modtype = 'SuperConductingMagnetInterface'
    _modclass = 'interface'
    
    @abc.abstractmethod
    def get_constraints(self):
        """ Constraints and parameters of SC magnet's hardware
        """
        pass
    
    @abc.abstractmethod
    def sweep_coil(self, Amps, coil):
        """ Bring a coil to field Amps and the power supply back to zero.
        """
        pass
    
    @abc.abstractmethod
    def sweeping_status(self, coil):
        pass
    
    @abc.abstractmethod
    def get_powersupply_current(self, coil):
        """
        Query current power supply
        
        @return array
        """
        pass
    
    @abc.abstractmethod
    def get_coil_current(self, coil):
        """
        Query current coil
        
        @return array
        """
        pass
    
class SCMagnetConstraints:
    """ Constraints and parameters of SC magnet's hardware
    """
    def __init__(self):
        """ Defaults parameters
        """
        # max field values
        self.max_B = {}
        self.max_B["x"] = 500
        self.max_B["y"] = 500
        self.max_B["z"] = 500

        # min field values
        self.min_B = {}
        self.min_B["x"] = -500
        self.min_B["y"] = -500
        self.min_B["z"] = -500
        
        # max current values
        self.max_A = {}
        self.max_A["x"] = 39.67
        self.max_A["y"] = 47.73
        self.max_A["z"] = 15.72

        # min current values
        self.min_A = {}
        self.min_A["x"] = -39.67
        self.min_A["y"] = -47.73
        self.min_A["z"] = -15.72

    def field_in_range(self, field, coil):
        return in_range(field, self.min_B[coil], self.max_B[coil])

    def current_in_range(self, current, coil):
        return in_range(current, self.min_A[coil], self.max_A[coil])

    def using_heater(self):
        return self.heater
