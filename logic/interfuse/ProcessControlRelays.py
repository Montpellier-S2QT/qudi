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

class ProcessControlRelays(GenericLogic, ProcessControlInterface):
    """ This interfuse can be used to combin the work of Powersuplly and the Arduino.
    How check the  value of the polarity and switch the coil 
    """
    
    _powerSupply = Connector(interface='ProcessControlInterface')
    _arduino_Relays = Connector(interface = 'Interface_control_arduino')
    
    

    def on_activate(self):
        """ Activate module.
        """
        self._powerSupply()
        self._arduino_Relays()

        

    def on_deactivate(self):
        """ Deactivate module.
        """
        return   
        
# interface functions (arduino )   
    def init_all_pins(self):
        """ initializes all pin in output mode """ 
        
        
        self.Arduino_Relays.init_all_pins()
        return

    def set_pin_mode(self, pin_number, mode):
         """
        Performs a pinMode() operation on pin_number
        Internally sends b'M{mode}{pin_number} where mode could be:
        - I for INPUT
        - O for OUTPUT
        - P for INPUT_PULLUP MO13
        """
        
         self.Arduino_Relays.set_pin_mode(self, pin_number, mode)
         return
     
    def digital_read(self, pin_number):   
        """
        Performs a digital read on pin_number and returns the value (1 or 0)
        Internally sends b'RD{pin_number}' over the serial connection
        """
        
        self.Arduino_Relays.digital_read(self, pin_number)
        return
    
    def digital_write(self, pin_number, digital_value):
         """
        Writes the digital_value on pin_number
        Internally sends b'WD{pin_number}:{digital_value}' over the serial
        connection
        """
         self.Arduino_Relays.digital_write(self, pin_number,digital_value)
         return 
        
    def analog_read(self, pin_number):
         """
        Performs an analog read on pin_number and returns the value (0 to 1023)
        Internally sends b'RA{pin_number}' over the serial connection
        """
         self.Arduino_Relays.analog_read(self, pin_number)
         return 
    
    
    def analog_write(self, pin_number, analog_value):
        """
        Writes the analog value (0 to 255) on pin_number
        Internally sends b'WA{pin_number}:{analog_value}' over the serial
        connection
        """   
        self.Arduino_Relays.analog_write(self, pin_number,analog_value)
        return 

    def switch_coil(self, polarity,coil):
       """
       Switch the coil from off to on depends on the coil and the sign of the polarity 
       x,z (coils) are off when polarity positive and on when it's negative, y coil works in inverse sense 
        """
       if coil == 1 :  # x coil
           if polarity == 'neg':
               self.digital_write(self._pin_list[0],1)
               time.sleep(0.5)
               self.digital_write(self._pin_list[1],1)
           else:
              self.digital_write(self._pin_list[0],0)
              time.sleep(0.5)
              self.digital_write(self._pin_list[1],0)
       elif coil == 2     :  # y coil 
           if polarity == 'neg':
              self.digital_write(self._pin_list[2],0)
              time.sleep(0.5)
              self.digital_write(self._pin_list[3],0)
           else:
               self.digital_write(self._pin_list[2],1)
               time.sleep(0.5)
               self.digital_write(self._pin_list[3],1)
       elif coil == 3  :  #  z coil 
            if polarity == 'neg':
                self.digital_write(self._pin_list[4],1)
                time.sleep(0.5)
                self.digital_write(self._pin_list[5],1)
            else:
                self.digital_write(self._pin_list[4],0)
                time.sleep(0.5)
                self.digital_write(self._pin_list[5],0)
       return



# interface functions (arduino )      
    
    def set_control_value(self, value, channel=1,ctrparam="VOLT"):
        """ Set the value of the controlled process variable

        @param (float) value: The value to set
        @param (int) channel: (Optional) The number of the channel
          Check sign of the value and call the Arduino 
        """
        if value < 0 :
            self.switch_coil('neg',channel)
        else :
            self.switch_coil('pos',channel)
        time.sleep(5)   
        self.PowerSupply.set_control_value(self, value, channel=1, ctrparam="VOLT")
        pass

   
    def get_control_value(self, ctrparam="VOLT"):
        """ Get the value of the controlled process variable

        @param (int) channel: (Optional) The number of the channel

        @return (float): The current control value
        """
        self.PowerSupply.get_control_value(self, channel=None, ctrparam="VOLT")
        pass

    
    def get_control_unit(self, ctrparam="VOLT"):
        """ Return the unit that the value is set in as a tuple of ('abbreviation', 'full unit name')

        @param (int) channel: (Optional) The number of the channel

        @return: The unit as a tuple of ('abbreviation', 'full unit name')
        """
        self.PowerSupply.get_control_unit(self, ctrparam="VOLT")
        pass

    
    def get_control_limit(self, channel=None, ctrparam="VOLT"):
        """ Return limits within which the controlled value can be set as a tuple of (low limit, high limit)

        @param (int) channel: (Optional) The number of the channel

        @return (tuple): The limits as (low limit, high limit)
        """
        self.PowerSupply.get_control_limit(self, channel=None, ctrparam="VOLT")
        pass

    def process_control_supports_multiple_channels(self):
        """ Function to test if hardware support multiple channels

        @return (bool): Whether the hardware supports multiple channels

        This function is not abstract - Thus it is optional and if a hardware do not implement it, the answer is False.
        """
        self.PowerSupply.process_control_supports_multiple_channels()
        return False

    def process_control_get_number_channels(self):
        """ Function to get the number of channels available for control

        @return (int): The number of controllable channel(s)

        This function is not abstract - Thus it is optional and if a hardware do not implement it, the answer is 1.
        """
        self.PowerSupply.process_control_get_number_channels()
        return 1
    
    
    
    
    
    
    