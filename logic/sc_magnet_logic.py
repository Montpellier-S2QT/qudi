# -*- coding: utf-8 -*-
""" 
This module operates a 3D coil magnet using a HMP3020 power supply.

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

from qtpy import QtCore
from collections import OrderedDict
from copy import copy
from threading import Thread
import time
import datetime
import numpy as np

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from core.connector import Connector
from core.configoption import ConfigOption
from core.statusvariable import StatusVar

class CoilMagnetLogic(GenericLogic):
    
    _modclass = 'coilmagnetlogic'
    _modtype = 'logic'

    # Config options
    _coeff_x = ConfigOption('coeff_x', 10.50) #G/A
    _coeff_y = ConfigOption('coeff_y', 10.50) #G/A
    _coeff_z = ConfigOption('coeff_z', 42.00) #G/A

    # Declare connectors
    powersupply = Connector(interface='ProcessControlInterface')
    
    # Internal signals
    sigContinueSweeping = QtCore.Signal()

    # Update signals, e.g. for GUI module
    sigFieldSet = QtCore.Signal()
    sigSweeping = QtCore.Signal()
    sigCurrentsValuesUpdated = QtCore.Signal(str, float, float)
    sigNewFieldValues = QtCore.Signal(float, float, float)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self):
       """ Initialisation performed during activation of the module. """
       # Redefine connectors
       self._power_supply = self.powersupply()

       # Constraints method
       self.limits = self._power_supply.get_limits()
       
       # Connect internal signals
       self.sigContinueSweeping.connect(self._wait_sweep_and_pause, QtCore.Qt.QueuedConnection)

       self.check_sweep_ended = False
       self.coeff = {'x': self.coeff_x, 'y': self.coeff_y, 'z': self.coeff_z}
       
       return 0

    def on_deactivate(self):
       """ Cleanup performed during deactivation of the module. """

       return

    def _set_field_coil(self, B, coil):
        """ Set the field for one coil. 
        B in G, coil is a str, "x", "y" or "z" .
        """
        if B > self.limits.max_B[coil]:
            B = self.limits.max_B[coil]
            self.log.warning("Max current value in {} exceeded. Applying max value instead.".format(coil))
        if B < self.limits.min_B[coil]:
            B = self.limits.min_B[coil]
            self.log.warning("Max current value in {} exceeded. Applying max value instead.".format(coil))
        current = B/self.coeff[coil]
        
        sweep_thread = Thread(target=self._power_supply.sweep_coil, args=(current, coil))
        sweep_thread.start()
        self.sigContinueSweeping.emit()

        return B

    def _wait_sweep_and_pause(self, coil):
        """ Checks every 0.5s if the sweep is over. When it is the case, pause.
            @param dict
            @param float 
            @param str "x", "y" or "z"
        """
        if self.check_sweep_ended:
            self.check_sweep_ended = False
            [ps_current, magnet_current] = self.get_currents(coil)
            self.sigCurrentsValuesUpdated.emit(coil, ps_current, magnet_current)
            return
        
        # check every 0.5s if the value is reached
        time.sleep(0.5)
        self.check_sweep_ended = self._power_supply.sweeping_status(coil)
        [ps_current, magnet_current] = self.get_currents(coil)
        self.sigCurrentsValuesUpdated.emit(coil, ps_current, magnet_current)
        self.sigContinueSweeping.emit()

        return
    
    def get_currents(self, coil):
        """ Read currents. """
        [ps_current, magnet_current] = self._power_supply._get_current(coil)

        return [ps_current, magnet_current]
    
    
    def go_to_field(self, Bx, By, Bz):
       """ Routine doing the full work to set a field value, B in G.
       """
       Bx = self._set_field_coil(Bx, "x")
       time.sleep(0.5)
       By = self._set_field_coil(By, "y")
       time.sleep(0.5)
       Bz = self._set_field_coil(Bz, "z")
       time.sleep(0.5)
       self.sigFieldSet.emit()
       self.sigNewFieldValues.emit(Bx, By, Bz)

       return Bx, By, Bz
