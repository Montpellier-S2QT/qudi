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
import time
import datetime
import numpy as np

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from core.connector import Connector

class SuperConductingMagnetLogic(GenericLogic):
    
    _modclass = 'sccoilmagnetlogic'
    _modtype = 'logic'

    # Declare connectors
    powersupply = Connector(interface='SuperConductingMagnetInterface')
    
    # Internal signals
    sigContinueSweeping = QtCore.Signal(str)

    # Update signals, e.g. for GUI module
    sigFieldSet = QtCore.Signal()
    sigSweeping = QtCore.Signal()
    sigCurrentsValuesUpdated = QtCore.Signal(str, float, float)
    sigNewFieldValues = QtCore.Signal(float, float, float)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # locking for thread safety 
        # TODO: not used for now
        self.threadlock = Mutex()

    def on_activate(self):
       """ Initialisation performed during activation of the module. """
       # Redefine connectors
       self._power_supply = self.powersupply()

       # Constraints method
       self.constr = self._power_supply.get_constraints()
       
       # Connect internal signals
    #    self.sigContinueSweeping.connect(self._wait_sweep_and_pause, QtCore.Qt.QueuedConnection)

       # Connect external signals
       self._power_supply.sigValuesUpdated.connect(self.get_currents)

       self.check_sweep_ended = False
       self.coeff = {
           'x': self._power_supply.current_ratio_x, 
           'y': self._power_supply.current_ratio_y, 
           'z': self._power_supply.current_ratio_z}
       
       return 0

    def on_deactivate(self):
       """ Cleanup performed during deactivation of the module. """

       return

    def _set_field_coil(self, B, coil):
        """ Set the field for one coil. 
        B in mT, coil is a str, "x", "y" or "z" .
        """
        # if B > self.constr.max_B[coil]:
        #     B = self.constr.max_B[coil]
        #     self.log.warning("Max current value in {} exceeded. Applying max value instead.".format(coil))
        # if B < self.constr.min_B[coil]:
        #     B = self.constr.min_B[coil]
        #     self.log.warning("Max current value in {} exceeded. Applying max value instead.".format(coil))
        B = self.constr.field_in_range(B, coil)*10
        current = B/self.coeff[coil]
        
        self._power_supply.sweep_coil(current, coil)
        # self.sigContinueSweeping.emit(coil)

        return B/10

    # def _wait_sweep_and_pause(self, coil):
    #     """ Checks every 0.5s if the sweep is over. When it is the case, pause.
    #         @param dict
    #         @param float 
    #         @param str "x", "y" or "z"
    #     """
    #     if self.check_sweep_ended:
    #         self.check_sweep_ended = False
    #         [ps_current, magnet_current] = self.get_currents(coil)
    #         self.sigCurrentsValuesUpdated.emit(coil, ps_current, magnet_current)
    #         return
        
    #     # check every 0.5s if the value is reached
    #     time.sleep(0.5)
    #     self.check_sweep_ended = self._power_supply.sweeping_status(coil)
    #     [ps_current, magnet_current] = self.get_currents(coil)
    #     self.sigCurrentsValuesUpdated.emit(coil, ps_current, magnet_current)
    #     self.sigContinueSweeping.emit(coil)

    #     return
    
    def get_currents(self, coil):
        """ Read currents. """
        ps_current = self._power_supply.get_powersupply_current(coil)
        magnet_current = self._power_supply.get_coil_current(coil)

        self.log.warning([ps_current, magnet_current])
        self.sigCurrentsValuesUpdated.emit(coil, ps_current, magnet_current)

        return [ps_current, magnet_current]

    def get_sweep_status(self, coil):

        if self._power_supply.sweeping_status(coil):
            return "Standby"
        else:
            return "Sweeping..."
    
    
    def go_to_field(self, Bx, By, Bz):
       """ Routine doing the full work to set a field value, B in mT.
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
