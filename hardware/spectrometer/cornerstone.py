# -*- coding: utf-8 -*-
"""
This module interface Shamrock spectrometer from Andor.

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
na=not applicable
"""
import os
import numpy as np
import sys
import clr

from core.module import Base
from core.configoption import ConfigOption

from interface.grating_spectrometer_interface import GratingSpectrometerInterface
from interface.grating_spectrometer_interface import Grating, PortType, Port, Constraints


class Cornerstone(Base, GratingSpectrometerInterface):
    """ Hardware module that interface a Cornerstone spectrometer from Newport

    Tested with :
    - Cornerstone 130

    Example config for copy-paste:

    cornerstone:
        module.Class: 'spectrometer.cornerstone.Cornerstone'
        dll_path : 'path to your dll file'
        shutter_auto : True
        grating_ruling : [1200e3, 2400e3]
        grating_blaze : [300e-9, 275e-9]
        grating_max_wavelength : [20e-6, 20e-6]
    """

    _dll_path = ConfigOption('dll_path', r'C:\Program Files\Newport\Mono Utility 5.0.4\Cornerstone DLL')
    _shutter_auto = ConfigOption('shutter_auto', True)
    _grating_ruling = ConfigOption('grating_ruling', [1200e3, 2400e3])
    _grating_blaze = ConfigOption('grating_blaze', [300e-9, 275e-9])
    _grating_max_wavelength = ConfigOption('grating_max_wavelength', [20e-6, 20e-6])


    # Declarations of attributes to make Pycharm happy
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    ##############################################################################
    #                            Basic functions
    ##############################################################################
    def on_activate(self):
        """ Activate module """

        sys.path.append(self._dll_path)
        clr.AddReference('Cornerstone')
        import CornerstoneDll

        self._device = CornerstoneDll.Cornerstone(True)
        if not self._device.connect():
            raise IOError('Monochromator not found')
        if self._shutter_auto:
            self._device.setShutter(True)

        self._constraints = self._build_constraints()

    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module. """
        if self._shutter_auto:
            self._device.setShutter(False)
        return self._device.disconnect()

    def _build_constraints(self):
        """ Internal method that build the constraints once at initialisation

         This makes multiple call to the DLL, so it will be called only once by on_activate
         """
        constraints = Constraints()

        number_of_gratings = 2
        for i in range(number_of_gratings):
            grating = Grating()
            grating.ruling = self._grating_ruling[i]
            grating.blaze = self._grating_blaze[i]
            grating.wavelength_max = self._grating_max_wavelength[i]
            constraints.gratings.append(grating)

        input_port_side = Port(PortType.INPUT_SIDE)
        input_port_side.is_motorized = False
        constraints.ports.append(input_port_side)

        output_port_side = Port(PortType.OUTPUT_SIDE)
        output_port_side.is_motorized = False
        constraints.ports.append(output_port_side)

        for port in constraints.ports:
            port.constraints.min = 10e-6
            port.constraints.max = 1000e-6

        return constraints

    def get_constraints(self):
        """ Returns all the fixed parameters of the hardware which can be used by the logic.

        @return (Constraints): An object of class Constraints containing all fixed parameters of the hardware
        """
        return self._constraints

    ##############################################################################
    #                            Gratings functions
    ##############################################################################
    def get_grating(self):
        """ Returns the current grating index

        @return (int): Current grating index
        """
        return int(self._device.getGrating()[0])-1

    def set_grating(self, value):
        """ Sets the grating by index

        @param (int) value: grating index
        """
        self._device.setGrating(value+1)

    ##############################################################################
    #                            Wavelength functions
    ##############################################################################
    def get_wavelength(self):
        """ Returns the current central wavelength in meter

        @return (float): current central wavelength (meter)
        """
        return float(self._device.getWavelength())*1.0e-9

    def set_wavelength(self, value):
        """ Sets the new central wavelength in meter

        @params (float) value: The new central wavelength (meter)
        """
        self._device.setWavelength(value*1.0e9)

    def get_spectrometer_dispersion(self, number_pixels, pixel_width):
        """ Return the spectrometer dispersion for a given center wavelength measured by the fabricant.
        This function has to be used only for fitting purpose since the dispersion spectrum must be measured inside the
        logic module. The fitting of the dispersion give better accuracy of our dispersion calculations in the
        'spectrumlogic' module.

        @return (list or ndarray): wavelength spectrum related to the spectrometer dispersion
        """
        return np.array([self.get_wavelength()])

    ##############################################################################
    #                        Ports and Slits functions
    ##############################################################################

    def get_input_port(self):
        """ Returns the current input port

        @return (PortType): current port side
        """
        return PortType.INPUT_SIDE

    def set_input_port(self, value):
        """ Set the current input port

        @param (PortType) value: The port side to set
        """
        pass

    def get_output_port(self):
        """ Returns the current output port

        @return (PortType): current port side
        """
        return PortType.OUTPUT_SIDE

    def set_output_port(self, value):
        """ Set the current output port

        @param (PortType) value: The port side to set
        """
        pass

    def get_slit_width(self, port_type):
        """ Getter for the current slit width in meter on a given port

        @param (PortType) port_type: The port to inquire

        @return (float): input slit width (in meter)
        """
        pass

    def set_slit_width(self, port_type, value):
        """ Setter for the input slit width in meter

        @param (PortType) port_type: The port to set
        @param (float) value: input slit width (in meter)
        """
        pass
