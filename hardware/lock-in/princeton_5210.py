# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface for a camera.


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
from enum import Enum
import numpy as np
import pyvisa

from core.module import Base
from core.configoption import ConfigOption

from interface.lockin_interface import ScienceCameraInterface, ReadMode

class Princeton(Base, ScienceCameraInterface):

    _port = ConfigOption("port", "ASRL4::INSTR")

    def on_activate(self):
        rm = pyvisa.ResourceManager()
        self._device = rm.open_resource(self._port)
        self._device.baudrate = 19200
        self._device.data_bits = 7
        self._device.parity = 0

    def on_deactivate(self):
        pass

    ##############################################################################
    #                                     Constraints functions
    ##############################################################################
    def _build_constraints(self):
        """ Internal method that build the constraints once at initialisation

         This makes multiple call to the DLL, so it will be called only once by on_activate
         """
        constraints = Constraints()
        constraints.name = self._get_name()
        constraints.width, constraints.height = self._get_image_size()
        constraints.pixel_size_width, constraints.pixel_size_height = self._get_pixel_size()
        constraints.internal_gains = 1
        constraints.readout_speeds = 1
        constraints.trigger_modes = 'INTERNAL'
        constraints.has_shutter = False
        constraints.read_modes = ReadMode.FVB
        constraints.has_cooler = False  # All Andor camera have one
        constraints.temperature.min, constraints.temperature.max = [298.15, 298.15]
        constraints.temperature.step = 1  # Andor cameras use integer for control

        return constraints

    def get_constraints(self):
        """ Returns all the fixed parameters of the hardware which can be used by the logic.

        @return (Constraints): An object of class Constraints containing all fixed parameters of the hardware
        """
        return self._constraints

    ##############################################################################
    #                                     Basic functions
    ##############################################################################
    def start_acquisition(self):
        """ Starts the acquisition """
        pass

    def abort_acquisition(self):
        """ Aborts the acquisition """
        pass

    def get_ready_state(self):
        """ Get the status of the camera, to know if the acquisition is finished or still ongoing.

        @return (bool): True if the camera is ready, False if an acquisition is ongoing

        As there is no synchronous acquisition in the interface, the logic needs a way to check the acquisition state.
        """
        return True

    def get_acquired_data(self):
        """ Return an array of last acquired data.

               @return: Data in the format depending on the read mode.

               Depending on the read mode, the format is :
               'FVB' : 1d array
               'MULTIPLE_TRACKS' : list of 1d arrays
               'IMAGE' 2d array of shape (width, height)
               'IMAGE_ADVANCED' 2d array of shape (width, height)

               Each value might be a float or an integer.
               """
        return self._device.query('M')

    ##############################################################################
    #                           Read mode functions
    ##############################################################################
    def get_read_mode(self):
        """ Getter method returning the current read mode used by the camera.

        @return (ReadMode): Current read mode
        """
        return ReadMode.FVB

    def set_read_mode(self, value):
        """ Setter method setting the read mode used by the camera.

         @param (ReadMode) value: read mode to set
         """
        pass

    def get_readout_speed(self):
        """  Get the current readout speed (in Hz)

        @return (float): the readout_speed (Horizontal shift) in Hz
        """
        return 1

    def set_readout_speed(self, value):
        """ Set the readout speed (in Hz)

        @param (float) value: horizontal readout speed in Hz
        """
        pass

    def get_active_tracks(self):
        """ Getter method returning the read mode tracks parameters of the camera.

        @return (list):  active tracks positions [(start_1, end_1), (start_2, end_2), ... ]
        """
        return []

    def set_active_tracks(self, value):
        """ Setter method for the active tracks of the camera.

        @param (ndarray) value: active tracks positions  as [start_1, end_1, start_2, end_2, ... ]
        """
        pass

    def get_image_advanced_parameters(self):
        """ Getter method returning the image parameters of the camera.

        @return (ImageAdvancedParameters): Current image advanced parameters

        Can be used in any mode
        """
        return 

    def set_image_advanced_parameters(self, value):
        """ Setter method setting the read mode image parameters of the camera.

        @param (ImageAdvancedParameters) value: Parameters to set

        Can be used in any mode
        """
        pass

    ##############################################################################
    #                           Acquisition mode functions
    ##############################################################################

    def get_exposure_time(self):
        """ Get the exposure time in seconds

        @return (float) : exposure time in s
        """
        return 1

    def set_exposure_time(self, value):
        """ Set the exposure time in seconds

        @param (float) value: desired new exposure time
        """
        pass

    def get_gain(self):
        """ Get the gain

        @return (float): exposure gain
        """
        return 1

    def set_gain(self, value):
        """ Set the gain

        @param (float) value: New gain, value should be one in the constraints internal_gains list.
        """
        pass

    ##############################################################################
    #                           Trigger mode functions
    ##############################################################################
    def get_trigger_mode(self):
        """ Getter method returning the current trigger mode used by the camera.

        @return (str): current trigger mode
        """
        return 'Internal'

    def set_trigger_mode(self, value):
        """ Setter method for the trigger mode used by the camera.

        @param (str) value: trigger mode (must be compared to a dict)
        """
        pass
    
    ##############################################################################
    #                           Shutter mode functions
    ##############################################################################
    def get_shutter_state(self):
        """ Getter method returning the shutter state.

        @return (ShutterState): The current shutter state
        """
        return 'OPEN'

    def set_shutter_state(self, value):
        """ Setter method setting the shutter state.

        @param (ShutterState) value: the shutter state to set
        """
        pass

    ##############################################################################
    #                           Temperature functions
    ##############################################################################
    def get_cooler_on(self):
        """ Getter method returning the cooler status

        @return (bool): True if the cooler is on
        """
        return False  # No getter in the DLL

    def set_cooler_on(self, value):
        """ Setter method for the the cooler status

        @param (bool) value: True to turn it on, False to turn it off
        """
        pass

    def get_temperature(self):
        """ Getter method returning the temperature of the camera.

        @return (float): temperature (in Kelvin)
        """
        return 298.15

    def get_temperature_setpoint(self):
        """ Getter method for the temperature setpoint of the camera.

        @return (float): Current setpoint in Kelvin
        """
        return 298.15

    def set_temperature_setpoint(self, value):
        """ Setter method for the the temperature setpoint of the camera.

        @param (float) value: New setpoint in Kelvin
        """
        pass