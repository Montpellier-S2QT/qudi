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

from core.module import Base, ConfigOption
from interface.sc_magnet_interface import SuperConductingMagnetInterface

class SuperConductingMagnet(Base, SuperConductingMagnetInterface):
    """ Magnet positioning software for attocube's superconducting magnet.

    Enables precise positioning of the magnetic field in spherical coordinates
    with the angle theta, phi and the radius rho.
    The superconducting magnet has three coils, one in x, y and z direction respectively.
    The current through these coils is used to compute theta, phi and rho.

    Example config for copy-paste:

    sc_magnet:
        module.Class: 'sc_magnet.attocube_sc_magnet.SuperConductingMagnet'
        gpib_address_x: 'GPIB0::12::INSTR'
        gpib_address_y: 'GPIB0::12::INSTR'
        gpib_address_z: 'GPIB0::12::INSTR'
        gpib_timeout: 10
        max_field_z: 5000
        max_field_x: 5000
        max_field_y: 5000
        max_current_z: 15.72
        max_current_x: 39.67
        max_current_y: 47.73

    """
    
    _modclass = 'SuperConductingMagnet'
    _modtype = 'hardware'

    # visa address of the hardware
    _address_xy = ConfigOption('gpib_address_x', missing='error')
    _address_z = ConfigOption('gpib_address_z', missing='error')
    _timeout = ConfigOption('gpib_timeout', 500, missing='warn')
    _max_field_z = ConfigOption('max_field_z', missing='error')
    _max_field_x = ConfigOption('max_field_x', missing='error')
    _max_field_y = ConfigOption('max_field_y', missing='error')
    _max_current_z = ConfigOption('max_current_z', missing='error')
    _max_current_x = ConfigOption('max_current_x', missing='error')
    _max_current_y = ConfigOption('max_current_y', missing='error')
    _current_ratio_x = ConfigOption('current_ratio_x', missing='error')
    _current_ratio_y = ConfigOption('current_ratio_y', missing='error')
    _current_ratio_z = ConfigOption('current_ratio_z', missing='error')

    # default waiting time of the pc after a message was sent to the magnet
    _waitingtime = ConfigOption('magnet_waitingtime', 0.5)
    
    _max_power = ConfigOption('max_power', None)
    
    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        # trying to load the visa connection to the module
        self._rm = pyvisa.ResourceManager()
        try:
            test = 'Could not connect to the address >>{}<<.'.format(self._address_xy)
            self.xy_magnet = self._rm.open_resource(self._address_xy,
                                                          timeout=self._timeout)
            test = 'Could not connect to the address >>{}<<.'.format(self._address_z)
            self.z_magnet = self._rm.open_resource(self._address_z,
                                                          timeout=self._timeout)
        except:
            self.log.error(test)
            raise

        self.ch = {"x":1, "y":2}

        self._model = self.query_device(self.xy_magnet, '*IDN?\n')
        self.log.info('Superconducting magnet {} initialised and connected.'.format(self._model))
        self.xy_magnet.write('*CLS;*RST\n')
        self.xy_magnet.read()
        
        self._model = self.query_device(self.z_magnet,'*IDN?\n')
        self.log.info('Superconducting magnet {} initialised and connected.'.format(self._model))
        self.z_magnet.write('*CLS;*RST\n')
        self.z_magnet.read()
        return
    
    def on_deactivate(self):
        """ Cleanup performed during deactivation of the module. """
        temp = 0
        self.channel_select(self.xy_magnet, 2)
        temp += self.query_device(self.xy_magnet, 'PSHTR?\n')
        self.channel_select(self.xy_magnet, 1)
        temp += self.query_device(self.xy_magnet, 'PSHTR?\n')
        temp += self.query_device(self.z_magnet, 'PSHTR?\n')
        if temp > 0:
            self.log.warning('Switch heater still ON !')
            
        temp = 0
        self.channel_select(self.xy_magnet, 2)
        temp += self.query_device(self.xy_magnet, 'IMAG?\n')
        self.channel_select(self.xy_magnet, 1)
        temp += self.query_device(self.xy_magnet, 'IMAG?\n')
        temp += self.query_device(self.z_magnet, 'IMAG?\n')
        if temp != 0:
            self.log.warning('Magnetic field still applied !')
            
        temp = 0
        self.channel_select(self.xy_magnet, 2)
        temp += self.query_device(self.xy_magnet, 'IOUT?\n')
        self.channel_select(self.xy_magnet, 1)
        temp += self.query_device(self.xy_magnet, 'IOUT?\n')
        temp += self.query_device(self.z_magnet, 'IOUT?\n')
        if temp != 0:
            self.log.warning('Power supply output current not at zero !')
        
        self._rm.close()
        return

    ###################################################################################
    #####                            USEFULL FUNCTIONS                            #####
    ###################################################################################

    def get_axis(self, coil):
        """ Return the axis with which we want to communicate.
        """
        if coil == "z":
           axis = self._magnet.z_magnet
        else:
           axis = self._magnet.xy_magnet
           n = self.channel_select(axis, self.ch[coil])
        return axis
    
    def get_limits(self, axis):
        """
        Read lower/upped sweep limit and voltage limit (5 for z, 1 for x and y)
        @param adress of the desired magnet
        
        @return str [llim, ulim, vlim]
        """
        self.ll = self.query_device(axis, 'LLIM?\n')[:-2]
        self.ul = self.query_device(axis, 'ULIM?\n')[:-2]
        self.vl = self.query_device(axis, 'VLIM?\n')[:-2]
        
        return [self.ll, self.ul, self.vl]
    
    def start_remote_mode(self, axis):
        """
        Select remote operation
        """
        axis.write('*CLS;REMOTE;ERROR 0\n')
        time.sleep(0.5)
        axis.read()

        return
    
    def channel_select(self, axis, n_channel):
        """
        Select module for subsequent commands
        @param int: wanted channel
        
        @return int: selected channel
        """
        axis.write('CHAN {}\n'.format(n_channel))
        time.sleep(0.5)
        axis.read()
        self.current_channel = n_channel
        
        return n_channel

    def get_powersupply_current(self, axis):
        self.iout = self.query_device(axis, 'IOUT?\n')[:-2]

    def get_coil_current(self, axis):
        self.imag = self.query_device(axis, 'IMAG?\n')[:-2]

        return self.iout, self.imag

    def get_powersupply_voltage(self, axis):
        self.vout = self.query_device(axis,'VOUT?\n')[:-2]

    def get_coil_voltage(self, axis):
        self.vmag = self.query_device(axis, 'VMAG?\n')[:-2]

        return self.vout, self.vmag

    def get_heater_status(self, axis):
        self.pshtr = self.query_device(axis,'PSHTR?\n')
        if int(self.pshtr) == 0:
            self.pshtr = 'OFF'
        else:
            self.pshtr = 'ON'

        return self.pshtr
    
    def read_sweep_mode(self, axis):
        """
        Query sweep mode
        
        @return str
        """
        self.sweep_mode = self.query_device(axis, 'SWEEP?\n')
        
        return self.sweep_mode

    def sweeping_status(self, coil):

        axis = self.get_axis(coil)
        status = self.read_sweep_mode(axis)

        if status=="sweep":
            check_sweep_ended=False
        else:
            check_sweep_ended=True

        return check_sweep_ended
    
    def get_units(self, axis):
        """
        Query selected units
        
        @return str
        """
        self.units = self.query_device(axis, 'UNITS?\n')
        
        return self.units
    
    def set_switch_heater(self, axis, mode='OFF'):
        """
        Control persistent switch heater
        @param USB adress
        @param string: ON or OFF to set the switch heater on or off
        """
        axis.write('PSHTR {}\n'.format(mode))
        time.sleep(0.5)
        axis.read()
        self.sh_mode = mode
        
        return mode
    
    def set_units(self, axis, units='A'):
        """
        Select Units
        @param string: A or G
        
        @return string: selected units
        """
        axis.write('UNITS {}\n'.format(units))
        time.sleep(0.5)
        axis.read()
        self.current_units = units
        
        return units

    def set_sweep_mode(self, axis, mode):
        """
        Start output current sweep
        @param str: sweep mode
        
        @return str
        """
        axis.write('SWEEP ' + mode + '\n')
        time.sleep(0.5)
        axis.read()
        self.sweep_mode = mode
        
        return mode
    
    def set_limits(self, axis, ll=None, ul=None, vl=None):
        """
        Set current and voltage sweep limits
        @param float: lower current sweep limit
        @param float: upper current sweep limit
        @param float: voltage sweep limit
        
        @return array
        """
        order = ''
        if ll is not None:
            order += 'LLIM {};'.format(ll)
        if ul is not None:
            order += 'ULIM {};'.format(ul)
        if vl is not None:
            order += 'VLIM {};'.format(vl)
        order = order[:-1]
        order += '\n'
        
        axis.write(order)
        time.sleep(0.5)
        axis.read()
        [self.ll, self.ul, self.vl] = [ll, ul, vl]
        
        return [ll, ul, vl]
    
    def query_device(self, axis, message, discarded_line_nb=1):
        """
        query from rm does not work for us, we need to read several lines.
        """
        axis.write(message)
        time.sleep(0.5)
        for i in range(discarded_line_nb):
            axis.read()
            time.sleep(0.5)
        answer = axis.read()
        if answer[:-4]==message[:-1]:
            answer = axis.read()
        return answer

    def get_mode(self, axis):
        """
        Query selected operating mode
        
        @return str
        """
        self.current_mode = self.query_device(axis, 'MODE?\n')
        
        return self.current_mode

    def sweep_until_target(self, axis, target, coil):
        """ Checks every 2s if the sweep is over. When it is the case, pause.
        """
        cur_stat = self.get_powersupply_current(axis)
        while np.abs(target-float(cur_stat)) > 1e-3:
            self.log.info(target)
            self.log.info(float(cur_stat))
            # check every 2s if the value is reached
            time.sleep(2)
            cur_stat = self.get_powersupply_current(axis)
        time.sleep(5)
        self.set_sweep_mode(axis, "PAUSE")
        return
        
    
    def set_field_coil(self, Amps, coil):
        """ Bring a coil to field Amps and the power supply back to zero.
        """

        # we do not do anything if a heater is ON or a magnet sweeping
        for test_coil in ["x", "y", "z"]:
            axis = self.get_axis(test_coil) 
            mode = self.read_sweep_mode(axis)[:-2]
            
            if not mode in ["Pause", "Standby"]:
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
        coilA = float(self.get_coil_current(axis))
        psA = float(self.get_powersupply_current(axis))
        self.log.info("Current amps value {}".format(coilA))
        if np.abs(coilA-Amps) < 1e-3:
            self.log.info(f"Coil {coil} already at the desired value.")
        else:
            # check if the magnet field and the power supply field are the same
            # if not, we have to change the power supply field
            if np.abs(coilA-psA) > 1e-3:
                
                if coilA > psA:
                    # imag > iout, we go up
                    l = self._magnet.set_limits(axis, ul=coilA)
                    self._magnet.set_sweep_mode(axis, "UP FAST")
                    self.log.info(f"Sweeping coil {coil} up fast")
                    self.sweep_until_target(axis, coilA, coil)
                
                else:
                    # imag < iout, we go down
                    l = self.set_limits(axis, ll=coilA)
                    self.set_sweep_mode(axis, "DOWN FAST")
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
            self.log.info(f"Heater {coil} ON, waiting 5 s")
            time.sleep(5)
            # sweep
            self.set_sweep_mode(axis, direction+" SLOW")
            self.log.info("Sweeping...")
            self.sweep_until_target(axis, Amps, coil)
            self.log.info("Sweep finished")
            # heater off
            self.set_switch_heater(axis, mode="OFF")
            self.log.info(f"Heater {coil} OFF, waiting 5 s")
            time.sleep(5)
            # zeroing
            self.set_sweep_mode(axis, "ZERO FAST")
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