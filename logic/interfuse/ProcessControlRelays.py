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


class ProcessControlRelays(GenericLogic, ProcessControlInterface):
    """ This interfuse can be used to combin the work of Powersuplly and the Arduino.
    How check the  value of the polarity and switch the coil 
    """
    
    _powerSupply = Connector(interface='ProcessControlInterface')
    _arduino_Relays = Connector()
    
    

    def on_activate(self):
        """ Activate module.
        """
        self._powerSupply()
        self._arduino_Relays()

        

    def on_deactivate(self):
        """ Deactivate module.
        """
        return   
        
# interface functions    
    
    
    def set_control_value(self, value, channel=1,ctrparam="VOLT"):
        """ Set the value of the controlled process variable

        @param (float) value: The value to set
        @param (int) channel: (Optional) The number of the channel
          Check sign of the value and call the Arduino 
        """
        if value < 0 :
            self.Arduino_Relays.switch_coil('neg',channel)
        else :
            self.Arduino_Relays.switch_coil('pos',channel)
            
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
    
    
    
    
    
    
    