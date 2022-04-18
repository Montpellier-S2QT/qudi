# -*- coding: utf-8 -*-
"""
This file contains the Qudi interfuse between a PowerSupply and an Arduino.

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
import numpy as np
import time

from core.connector import Connector
from logic.generic_logic import GenericLogic
from interface.process_control_interface import ProcessControlInterface

class ProcessControlRelays(GenericLogic, ProcessControlInterface):
    """ This interfuse can be used to combin the work of Powersuplly and the Arduino.
    How check the  value of the polarity and switch the coil 
    """

    _modclass = 'ProcessControlRelays'
    _modtype = 'logic'
    
    # connectors
    powersupply = Connector(interface='ProcessControlInterface')
    arduinorelays = Connector(interface = 'ArduinoSerialInterface')
    
    # options
     _pin_list = ConfigOption('pin_list',[6,7,9,10,12,13],missing='warn')

    def on_activate(self):
        """ Activate module.
        """
        self.arduinorelays().init_all_pins(self._pin_list)
        return
    

    def on_deactivate(self):
        """ Deactivate module.
        """
        return   
        
    # Interfuse specific function
    def switch_coil(self, polarity, coil):
       """
       Switch the relays on or off depending on the coil and desired the polarity. 
       The x and z coils are off when the polarity is positive and on when it is negative,
       while the y coil works in the opposite way. 
       """
       
       if coil == 1 :  # x coil
           if polarity == 'neg':
               self.arduinorelays().digital_write(self._pin_list[0],1)
               time.sleep(0.5)
               self.arduinorelays().digital_write(self._pin_list[1],1)
           else:
              self.arduinorelays().digital_write(self._pin_list[0],0)
              time.sleep(0.5)
              self.arduinorelays().digital_write(self._pin_list[1],0)
              
       elif coil == 2     :  # y coil 
           if polarity == 'neg':
              self.arduinorelays().digital_write(self._pin_list[2],0)
              time.sleep(0.5)
              self.arduinorelays().digital_write(self._pin_list[3],0)
           else:
               self.arduinorelays().digital_write(self._pin_list[2],1)
               time.sleep(0.5)
               self.arduinorelays().digital_write(self._pin_list[3],1)
               
       elif coil == 3  :  #  z coil 
            if polarity == 'neg':
                self.arduinorelays().digital_write(self._pin_list[4],1)
                time.sleep(0.5)
                self.arduinorelays().digital_write(self._pin_list[5],1)
            else:
                self.arduinorelays().digital_write(self._pin_list[4],0)
                time.sleep(0.5)
                self.arduinorelays().digital_write(self._pin_list[5],0)
       return



    # Interface functions        
    def set_control_value(self, value, channel=1, ctrparam="VOLT"):
        """ Set the value of the controlled process variable, after checking 
        that the sign is appropriate.

        @param float value: The value to set
        @param int channel: (Optional) The number of the channel
        @param str ctrparam: specify current or voltage control
        """
        # TODO these functions are not in ProcessControlInterface, can we not use them?
        if np.abs(value) < 1e-4 :
            self.powersupply()._set_all_off()
        else :
            self.powersupply()._set_on(channel)
            
    
        if value < 0 :
            self.switch_coil('neg', channel)
        else :
            self.switch_coil('pos', channel)
        time.sleep(1)
        
        self.powersupply().set_control_value(np.abs(value), channel=channel, ctrparam=ctrparam)
        return

   
    def get_control_value(self, channel=None, ctrparam="VOLT"):
        """ Get the value of the controlled process variable

        @param int channel: (Optional) The number of the channel
        @param str ctrparam: specify current or voltage control

        @return float: The current control value
        """
        value = self.powersupply().get_control_value(channel=channel, ctrparam=ctrparam)
        return value

    
    def get_control_unit(self, channel=None, ctrparam="VOLT"):
        """ Return the unit that the value is set in as a tuple of ('abbreviation', 'full unit name')
        for the currently active channel.

        @param int channel: (Optional) The number of the channel
        @param str ctrparam: specify current or voltage control

        @return: The unit as a tuple of ('abbreviation', 'full unit name')
        """
        unit = self.powersupply().get_control_unit(ctrparam=ctrparam)
        return unit

    
    def get_control_limit(self, channel=None, ctrparam="VOLT"):
        """ Return limits within which the controlled value can be set as a tuple of
        (low limit, high limit).

        @param int channel: (Optional) The number of the channel
        @param str ctrparam: specify current or voltage control

        @return tuple: The limits as (low limit, high limit)
        """
        limit = self.powersupply().get_control_limit(ctrparam=ctrparam)
        return limit
    

    def process_control_supports_multiple_channels(self):
        """ Function to test if hardware support multiple channels

        @return bool: Whether the hardware supports multiple channels.
        """
        mutiple = self.powersupply().process_control_supports_multiple_channels()
        return mutiple

    
    def process_control_get_number_channels(self):
        """ Function to get the number of channels available for control

        @return int: The number of controllable channel(s)
        """
        ch_nb = self.powersupply().process_control_get_number_channels()
        return ch_nb
    
    
    
    
    
    
    
