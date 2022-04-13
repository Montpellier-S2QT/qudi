# -*- coding: utf-8 -*-
"""
This file contains the Qudi interfuse between a PowerSupply and a Arduino_Relays.
---

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

from core.connector import Connector
from logic.generic_logic import GenericLogic
from interface.process_control_interface import ProcessControlInterface
import time
import numpy as np 

class ProcessControlRelays(GenericLogic, ProcessControlInterface):
    """ This interfuse can be used to combin the work of Powersuplly and the Arduino.
    How check the  value of the polarity and switch the coil 
    """
    
    powersupply = Connector(interface='ProcessControlInterface')
    arduinorelays = Connector(interface = 'Interface_control_arduino')
    
    

    def on_activate(self):
        """ Activate module.
        """

        

    def on_deactivate(self):
        """ Deactivate module.
        """
        return   
        
# interface functions (arduino )   

    def switch_coil(self, polarity,coil):
       """
       Switch the coil from off to on depends on the coil and the sign of the polarity 
       x,z (coils) are off when polarity positive and on when it's negative, y coil works in inverse sense 
        """
       if coil == 1 :  # x coil
           if polarity == 'neg':
               self.arduinorelays().digital_write(self.arduinorelays()._pin_list[0],1)
               time.sleep(0.5)
               self.arduinorelays().digital_write(self.arduinorelays()._pin_list[1],1)
           else:
              self.arduinorelays().digital_write(self.arduinorelays()._pin_list[0],0)
              time.sleep(0.5)
              self.arduinorelays().digital_write(self.arduinorelays()._pin_list[1],0)
       elif coil == 2     :  # y coil 
           if polarity == 'neg':
              self.arduinorelays().digital_write(self.arduinorelays()._pin_list[2],0)
              time.sleep(0.5)
              self.arduinorelays().digital_write(self.arduinorelays()._pin_list[3],0)
           else:
               self.arduinorelays().digital_write(self.arduinorelays()._pin_list[2],1)
               time.sleep(0.5)
               self.arduinorelays.digital_write(self.arduinorelays()._pin_list[3],1)
       elif coil == 3  :  #  z coil 
            if polarity == 'neg':
                self.arduinorelays.digital_write(self.arduinorelays()._pin_list[4],1)
                time.sleep(0.5)
                self.arduinorelays.digital_write(self.arduinorelays()._pin_list[5],1)
            else:
                self.arduinorelays.digital_write(self.arduinorelays()._pin_list[4],0)
                time.sleep(0.5)
                self.arduinorelays.digital_write(self.arduinorelays()._pin_list[5],0)
       return



# interface functions       
    
    def set_control_value(self, value, channel=1,ctrparam="VOLT"):
        """ Set the value of the controlled process variable

        @param (float) value: The value to set
        @param (int) channel: (Optional) The number of the channel
          Check sign of the value and call the Arduino 
        """
        if np.abs(value) < 1e-4 :
            self.powersupply()._set_all_off()
        else :
            self.powersupply()._set_on(channel)
            
    
        if value < 0 :
            self.switch_coil('neg',channel)
        else :
            self.switch_coil('pos',channel)
        time.sleep(5)   
        self.powersupply().set_control_value( np.abs(value), channel= channel, ctrparam = ctrparam)
        return

   
    def get_control_value(self,channel =None ,ctrparam="VOLT"):
        """ Get the value of the controlled process variable

        @param (int) channel: (Optional) The number of the channel

        @return (float): The current control value
        """
        value = self.powersupply().get_control_value(channel = channel ,ctrparam = ctrparam)
        return value

    
    def get_control_unit(self, ctrparam="VOLT"):
        """ Return the unit that the value is set in as a tuple of ('abbreviation', 'full unit name')

        @param (int) channel: (Optional) The number of the channel

        @return: The unit as a tuple of ('abbreviation', 'full unit name')
        """
        unit  = self.powersupply().get_control_unit( ctrparam = ctrparam)
        return unit

    
    def get_control_limit(self, channel=None, ctrparam="VOLT"):
        """ Return limits within which the controlled value can be set as a tuple of (low limit, high limit)

        @param (int) channel: (Optional) The number of the channel

        @return (tuple): The limits as (low limit, high limit)
        """
        limit =self.PowerSupply().get_control_limit(ctrparam = ctrparam)
        return limit

    def process_control_supports_multiple_channels(self):
        """ Function to test if hardware support multiple channels

        @return (bool): Whether the hardware supports multiple channels

        This function is not abstract - Thus it is optional and if a hardware do not implement it, the answer is False.
        """
        mutiple = self.powersupply().process_control_supports_multiple_channels()
        return mutiple

    def process_control_get_number_channels(self):
        """ Function to get the number of channels available for control

        @return (int): The number of controllable channel(s)

        This function is not abstract - Thus it is optional and if a hardware do not implement it, the answer is 1.
        """
        ch_nb = self.powersupply().process_control_get_number_channels()
        return ch_nb
    
    
    
    
    
    
    