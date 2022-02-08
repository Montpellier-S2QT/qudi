# -*- coding: utf-8 -*-
"""
Hardware file for an Attocube Superconducting Magnet (SCM)

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

import pyvisa
import time
import numpy as np
from qtpy import QtCore

from core.module import Base
from core.configoption import ConfigOption
from interface.sc_magnet_interface import SuperConductingMagnetInterface
from interface.sc_magnet_interface import SCMagnetConstraints

class SuperConductingMagnet(Base, SuperConductingMagnetInterface):
    """ Magnet positioning software for attocube's superconducting magnet.

    Enables precise positioning of the magnetic field in spherical coordinates
    with the angle theta, phi and the radius rho.
    The superconducting magnet has three coils, one in x, y and z direction respectively.
    The current through these coils is used to compute theta, phi and rho.

    Example config for copy-paste:

    sc_magnet:
        module.Class: 'sc_magnet.attocube_sc_magnet.SuperConductingMagnet'

    """
    
    _modclass = 'SuperConductingMagnet'
    _modtype = 'hardware'

    # visa address of the hardware
    current_ratio_x = ConfigOption('current_ratio_x', missing='error')
    current_ratio_y = ConfigOption('current_ratio_y', missing='error')
    current_ratio_z = ConfigOption('current_ratio_z', missing='error')

    sigValuesUpdated = QtCore.Signal(str)
    
    def on_activate(self):
        """ Initialisation performed during activation of the module. """

        self.ch = {"x":1, "y":2}
        self.iout = {"x":0, "y":0, "z":0}
        self.imag = {"x":0, "y":0, "z":0}
        self.pshtr = {"x":"OFF", "y":"OFF", "z":"OFF"}
        self.sweep_mode = {"x":"pause", "y":"pause", "z":"pause"}
        self.ratio = {"x":self.current_ratio_x, "y":self.current_ratio_y, "z":self.current_ratio_z}

        return
    
    def on_deactivate(self):
        """ Cleanup performed during deactivation of the module. """
        return

    ###################################################################################
    #####                            USEFULL FUNCTIONS                            #####
    ###################################################################################

    def get_constraints(self):
        """ Constraints and parameters of SC magnet's hardware
        """
        constr = SCMagnetConstraints()

        return constr

    def get_axis(self, coil):
        """ Return the axis with which we want to communicate.
        """
        axis = coil
        
        return axis

    def get_powersupply_current(self, coil):

        return self.iout[coil]

    def get_coil_current(self, coil):

        return self.imag[coil]

    def get_heater_status(self, axis):

        return self.pshtr[axis]
    
    def read_sweep_mode(self, axis):
        """
        Query sweep mode
        
        @return str
        """

        return self.sweep_mode[axis]

    def sweeping_status(self, coil):

        axis = self.get_axis(coil)
        status = self.read_sweep_mode(axis)

        if status=="sweep":
            check_sweep_ended=False
        else:
            check_sweep_ended=True

        return check_sweep_ended
    
    def set_switch_heater(self, axis, mode='OFF'):
        """
        Control persistent switch heater
        @param USB adress
        @param string: ON or OFF to set the switch heater on or off
        """
        self.pshtr[axis] = mode
        
        return self.pshtr[axis]
    
    def set_units(self, axis, units='A'):
        """
        Select Units
        @param string: A or G
        
        @return string: selected units
        """
        return units

    def set_sweep_mode(self, axis, mode):
        """
        Start output current sweep
        @param str: sweep mode
        
        @return str
        """
        self.sweep_mode[axis] = mode
        
        return self.sweep_mode
    
    def set_limits(self, axis, ll=None, ul=None, vl=None):
        """
        Set current and voltage sweep limits
        @param float: lower current sweep limit
        @param float: upper current sweep limit
        @param float: voltage sweep limit
        
        @return array
        """
        [self.ll, self.ul, self.vl] = [ll, ul, vl]
        
        return [ll, ul, vl]

    def sweep_until_target(self, axis, target, coil):
        """ Checks every 2s if the sweep is over. When it is the case, pause.
        """
        cur_stat = self.get_powersupply_current(coil)
        while np.abs(target-float(cur_stat)) > 1e-3:
            self.log.info(target)
            self.log.info(float(cur_stat))
            # check every 0.2s if the value is reached
            time.sleep(0.2)
            self.iout[coil] += np.sign(target - self.iout[coil]) * 1 / self.ratio[axis]
            if self.pshtr[axis] == "ON":
                self.imag[coil] = self.iout[coil]
            cur_stat = self.get_powersupply_current(coil)
            self.sigValuesUpdated.emit(coil)
        time.sleep(5)
        self.set_sweep_mode(axis, "pause")
        return
        
    
    def sweep_coil(self, Amps, coil):
        """ Bring a coil to field Amps and the power supply back to zero.
        """

        # we do not do anything if a heater is ON or a magnet sweeping
        for test_coil in ["x", "y", "z"]:
            axis = self.get_axis(test_coil) 
            mode = self.read_sweep_mode(axis)
            
            if mode not in ["pause", "standby"]:
                self.log.warning("Do not try to change the field during a sweep!")
                return
            heater = self.get_heater_status(axis)
            if heater == "ON":
                self.log.warning("Do not try to change the field with a heater on!")
                return

        axis = self.get_axis(coil)
        # First check the units, we need to be in G
        self.set_units(axis, "A")
        # Then check if we are already at the desired field or not
        coilA = float(self.get_coil_current(coil))
        psA = float(self.get_powersupply_current(coil))
        self.log.info("Current amps value {}".format(coilA))
        if np.abs(coilA-Amps) < 1e-3:
            self.log.info(f"Coil {coil} already at the desired value.")
        else:
            # check if the magnet field and the power supply field are the same
            # if not, we have to change the power supply field
            if np.abs(coilA-psA) > 1e-3:
                
                if coilA > psA:
                    # imag > iout, we go up
                    l = self.set_limits(axis, ul=coilA)
                    self.set_sweep_mode(axis, "sweep")
                    self.log.info(f"Sweeping coil {coil} up fast")
                    self.sweep_until_target(axis, coilA, coil)
                
                else:
                    # imag < iout, we go down
                    l = self.set_limits(axis, ll=coilA)
                    self.set_sweep_mode(axis, "sweep")
                    self.log.info(f"Sweeping coil {coil} down fast")
                    self.sweep_until_target(axis, coilA, coil)

            # now we have imag = iout, select the sweep direction
            if coilA < Amps:
                # imag > B, we go up
                l = self.set_limits(axis, ul=Amps)
                direction = "UP"
                self.log.info("We need to sweep up")
            else:
                # imag < B, we go down
                l = self.set_limits(axis, ll=Amps)
                direction = "DOWN"
                self.log.info("We need to sweep down")
                
            time.sleep(1)   
            # heater on
            self.set_switch_heater(axis, mode="ON")
            self.log.info(f"Heater {coil} ON, waiting 0.5 s")
            time.sleep(0.5)
            # sweep
            self.set_sweep_mode(axis, "sweep")
            self.log.info("Sweeping...")
            self.sweep_until_target(axis, Amps, coil)
            self.log.info("Sweep finished")
            # heater off
            self.set_switch_heater(axis, mode="OFF")
            self.log.info(f"Heater {coil} OFF, waiting 0.5 s")
            self.imag[coil] = self.iout[coil]
            time.sleep(0.5)
            # zeroing
            self.set_sweep_mode(axis, "sweep")
            self.log.info("Zeroing...")
            self.sweep_until_target(axis, 0, coil)
            self.log.info(f"Field set for coil {coil}.")
                
        return

    ###################################################################################
    #####                            USELESS FUNCTIONS                            #####
    ###################################################################################

    def _self_test_query(self, axis):
        """
        Self test query
        
        @return bool
        """
        temp = self.query_device(axis, '*TST?\n')
        
        return temp

    def _get_rates(self, axis):
        """
        Query sweep rates for selected sweep range.
        
        @return array
        """
        self.current_rates = []
        for i in range(6):
            self.current_rates.append(self.query_device(axis, 'RATE? {}\n'.format(i))[:-2])
            
        return self.current_rates

    def _get_ranges(self, axis):
        """
        Query range limit for sweep rate boundary
        
        @return str
        """
        self.current_ranges = []
        for i in range(5):
            self.current_ranges.append(self.query_device(axis,'RANGE? {}\n'.format(i))[:-2])
            
        return self.current_ranges

    def _start_local_mode(self, axis):
        """
        Select local operation
        """
        axis.write('*CLS;LOCAL;ERROR 0\n')
        axis.read()

        return

    def _set_ranges(self, axis, ranges):
        """
        Set range limit for sweep rate boundary. Dangerous.
        @param array: range values
        
        @return array
        """
        if len(ranges) != 5:
            self.log.warning('Not enough ranges ({} instead of 5)'.format(len(ranges)))
            return
        
        order = ''
        self.current_ranges = ranges
        for i in range(5):
            order += 'RANGE {} {};'.format(i, ranges[i])
        order = order[:-1]
        order += '\n'
        
        axis.write(order)
        axis.read()
        
        return ranges
    
    def _set_rates(self, axis, rates):
        """
        Set sweep rates for selected sweep range. Dangerous.
        @param array: range values
        
        @return array
        """
        if len(rates) != 6:
            self.log.warning('not enough rates ({} instead of 6)'.format(len(rates)))
            return
        
        order = ''
        self.current_rates = rates
        for i in range(6):
            order += 'RATE {} {};'.format(i, rates[i])
        order = order[:-1]
        order += '\n'
        
        axis.write(order)
        axis.read()
        
        return rates