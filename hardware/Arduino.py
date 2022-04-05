"""

Hardware module to interface a Arduino 

This file is adapted from the pi3diamond project distributed under GPL V3 licence.
Created by Helmut Fedder <helmut@fedder.net>. Adapted by someone else.

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
import visa    # ouvrire un cannal de connection entre python et l'instrument de hardware

from core.module import Base  # c'est le base  pour allumer le qudi
from core.configoption import ConfigOption  # importer les information des instruments des fichiers config

import time     #pour le calcule de temps 

class Arduino(Base):
    
    _modclass = 'Arduino'
    _modtype = 'hardware'
    
    _address = ConfigOption('address', missing='error') # dans le configoption on a l'adresse de l'instrument le qudi va pour la chercher
    _pin_list = ConfigOption('pin_list',[6,7,9,10,12,13],missing='warn')
    # _voltage_max_1 = ConfigOption('voltage_max_1', 30)
    # _current_max_1 = ConfigOption('current_max_1', 10)
    # _voltage_max_2 = ConfigOption('voltage_max_2', 30)
    # _current_max_2 = ConfigOption('current_max_2', 10)
    # _voltage_max_3 = ConfigOption('voltage_max_3', 30)
    # _current_max_3 = ConfigOption('current_max_3', 10)
    
    _model = None  # il va presenter l'identifiant
    _inst = None # instrument 
    
    
    def on_activate(self):
        """ Startup the module """

        rm = visa.ResourceManager()
        try:
            self._inst = rm.open_resource(self._address)
        except visa.VisaIOError:
            self.log.error('Could not connect to hardware. Please check the wires and the address.')
        
        self.init_all_pins()
        return
        
        
    def on_deactivate(self):
        """ Stops the module """
        
        self._inst.close()
        return
        
    def init_all_pins(self):
        """ initializes all pin in output mode """ 
        for i in range(len(self._pin_list)):
            self.set_pin_mode(self._pin_list[i], 'O')
            time.sleep(0.5)
        return     
   
            
    
        
    def set_pin_mode(self, pin_number, mode):
        """
        Performs a pinMode() operation on pin_number
        Internally sends b'M{mode}{pin_number} where mode could be:
        - I for INPUT
        - O for OUTPUT
        - P for INPUT_PULLUP MO13
        """
        command = (''.join(('M',mode,str(pin_number)))).encode()
        self._inst.write(command)
        
    def digital_read(self, pin_number):
        """
        Performs a digital read on pin_number and returns the value (1 or 0)
        Internally sends b'RD{pin_number}' over the serial connection
        """
        command = (''.join(('RD', str(pin_number)))).encode()
        self._inst.write(command)
        line_received = self._inst.readline().decode().strip()
        header, value = line_received.split(':') # e.g. D13:1
        if header == ('D'+ str(pin_number)):
            # If header matches
            return int(value)
        
    def digital_write(self, pin_number, digital_value):
        """
        Writes the digital_value on pin_number
        Internally sends b'WD{pin_number}:{digital_value}' over the serial
        connection
        """
        command = (''.join(('WD', str(pin_number), ':',
            str(digital_value)))).encode()
        self._inst.write(command) 
        
        
    def analog_read(self, pin_number):
        """
        Performs an analog read on pin_number and returns the value (0 to 1023)
        Internally sends b'RA{pin_number}' over the serial connection
        """
        command = (''.join(('RA', str(pin_number)))).encode()
        self._inst.write(command) 
        line_received = self._inst.readline().decode().strip()
        header, value = line_received.split(':') # e.g. A4:1
        if header == ('A'+ str(pin_number)):
            # If header matches
            return int(value)

    def analog_write(self, pin_number, analog_value):
        """
        Writes the analog value (0 to 255) on pin_number
        Internally sends b'WA{pin_number}:{analog_value}' over the serial
        connection
        """
        command = (''.join(('WA', str(pin_number), ':',
            str(analog_value)))).encode()
        self._inst.write(command) 

    # def close(self):
    #      """
    #     To ensure we are properly closing our connection to the
    #     Arduino device. 
    #     """
    #      self.conn.close()
    #      print('Connection to Arduino closed')
         
    
     

    def switch_coil(self, polarity,coil):
       if coil == 'x' :
           if polarity == 'neg':
               self.digital_write(self._pin_list[0],1)
               time.sleep(0.1)
               self.digital_write(self._pin_list[1],1)
           else:
              self.digital_write(self._pin_list[0],0)
              time.sleep(0.1)
              self.digital_write(self._pin_list[1],0)
       elif coil == 'y'     :
           if polarity == 'neg':
              self.digital_write(self._pin_list[2],0)
              time.sleep(0.1)
              self.digital_write(self._pin_list[3],0)
           else:
               self.digital_write(self._pin_list[2],1)
               time.sleep(0.1)
               self.digital_write(self._pin_list[3],1)
       elif coil == 'z'  :
            if polarity == 'neg':
                self.digital_write(self._pin_list[4],1)
                time.sleep(0.1)
                self.digital_write(self._pin_list[5],1)
            else:
                self.digital_write(self._pin_list[4],0)
                time.sleep(0.1)
                self.digital_write(self._pin_list[5],0)
       return
                     
                 