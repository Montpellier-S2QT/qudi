# -*- coding: utf-8 -*-
"""
Hardware module to interface an Arduino Uno through serial communication.
Stolen from https://www.instructables.com/Pyduino-Interfacing-Arduino-with-Python-through-se/
It assumes that you flashed also the .ino code to Arduino beforehand.

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

import visa    
import time

from core.module import Base  
from core.configoption import ConfigOption  
from interface.ArduinoSerialInterface import ArduinoSerialInterface


class Arduino(Base, ArduinoSerialInterface):

    _modclass = 'Arduino'
    _modtype = 'hardware'
    
    _address = ConfigOption('address', missing='error') 
    
    _model = None  
    _inst = None 
    
    
    def on_activate(self):
        """ Startup the module. """

        rm = visa.ResourceManager()
        try:
            self._inst = rm.open_resource(self._address)
        except visa.VisaIOError:
            self.log.error('Could not connect to hardware. Please check the wires and the address.')
        
#        self.init_all_pins()
        return
        
        
    def on_deactivate(self):
        """ Stops the module """
        self._inst.close()
        return

    
    def init_all_pins(self, pin_list):
        """ Initializes all pins in output mode.
        
        @param list pin_list: list of the used pins.
        """
        if pin_list is not None:
            time.sleep(2)
            for i in range(len(pin_list)):
                self.set_pin_mode(pin_list[i], 'O')
                time.sleep(0.5)
        return     
   
                   
    def set_pin_mode(self, pin_number, mode):
        """
        Performs a pinMode() operation on pin_number.
        Internally sends b'M{mode}{pin_number} where mode could be:
        - I for INPUT
        - O for OUTPUT
        - P for INPUT_PULLUP MO13

        @param int pin_number
        @param str mode
        """
        command = (''.join(('M',mode,str(pin_number))))
        self._inst.write(command)
        return
    
        
    def digital_read(self, pin_number):
        """
        Performs a digital read on pin_number and returns the value (1 or 0).
        Internally sends b'RD{pin_number}' over the serial connection.

        @param int pin_number
        @return int value: digital output of the pin (0 or 1).
        """
        command = (''.join(('RD', str(pin_number))))
        self._inst.write(command)
        line_received = self._inst.readline().decode().strip()
        header, value = line_received.split(':') # e.g. D13:1
        if header == ('D'+ str(pin_number)):
            # If header matches
            return int(value)
        return
    
        
    def digital_write(self, pin_number, digital_value):
        """
        Writes the digital_value on pin_number.
        Internally sends b'WD{pin_number}:{digital_value}' over the serial
        connection.

        @param int pin_number
        @param int digital_value: 0 or 1, value to write.
        """
        command = (''.join(('WD', str(pin_number), ':',
            str(digital_value))))
        self._inst.write(command)
        return
        
        
    def analog_read(self, pin_number):
        """
        Performs an analog read on pin_number and returns the value (0 to 1023)
        Internally sends b'RA{pin_number}' over the serial connection.

        @param int pin_number
        @return float value: analog output (in V?)
        """
        command = (''.join(('RA', str(pin_number))))
        self._inst.write(command) 
        line_received = self._inst.readline().decode().strip()
        header, value = line_received.split(':') # e.g. A4:1
        if header == ('A'+ str(pin_number)):
            # If header matches
            return float(value)
        return
        

    def analog_write(self, pin_number, analog_value):
        """
        Writes the analog value (0 to 255) on pin_number
        Internally sends b'WA{pin_number}:{analog_value}' over the serial
        connection.
        
        @param int pin_number
        @param float analog value
        """
        command = (''.join(('WA', str(pin_number), ':',
            str(analog_value))))
        self._inst.write(command)
        return

    
         
    
     

    
                     
                 
