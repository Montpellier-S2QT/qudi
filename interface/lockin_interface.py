# -*- coding: utf-8 -*-
"""
Interface for a spectrometer.

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

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass

class LockinInterface(metaclass=InterfaceMetaclass):
    """ Methods to control the synchronous demodulation of a signal.
    """

    @abstract_interface_method
    def get_output_values(self):
        """Method returning the output values related to the current output mode.

        @return (tuple) output_values: output values after the demodulation.
        """
        pass

    @abstract_interface_method
    def get_time_constant(self):
        """Getter method for the long-pass filter time constant

        @return (float) time_constant: filter time constant in second.
        """
        pass

    @abstract_interface_method
    def set_time_constant(self, time_constant):
        """Setter method for the long-pass filter time constant

        @return (float) time_constant: filter time constant in second.
        """
        pass

    @abstract_interface_method
    def get_gain(self):
        """Getter method for the gain of the amplifier.

        @return (int) gain: gain of the amplifier.
        """
        pass

    @abstract_interface_method
    def set_gain(self, gain):
        """Setter method for the gain of the amplifier.

        @param (int) gain: gain of the amplifier.
        """
        pass

    @abstract_interface_method
    def get_reference_frequency(self):
        """Getter method for the reference frequency for the demodulation.

        @return (float) reference_frequency: reference frequency for the demodulation.
        """
        pass

    @abstract_interface_method
    def set_reference_frequency(self, reference_frequency):
        """Setter method for the reference frequency for the demodulation.

        @param (float) reference_frequency: reference frequency for the demodulation.
        """
        pass

    @abstract_interface_method
    def get_reference_mode(self):
        """Getter method for the reference mode for the demodulation.

        @return (str) reference_mode: reference mode for the demodulation.
        """
        pass

    @abstract_interface_method
    def set_reference_mode(self, reference_mode):
        """Setter method for the reference mode for the demodulation.

        @param (str) reference_mode: reference mode for the demodulation.
        """
        pass

    @abstract_interface_method
    def get_reference_dephasing(self):
        """Getter method for the reference dephasing for the demodulation.

        @return (float) reference_dephasing: reference dephasing for the demodulation.
        """
        pass

    @abstract_interface_method
    def set_reference_dephasing(self, reference_dephasing):
        """Setter method for the reference dephasing for the demodulation.

        @param (float) reference_dephasing: reference dephasing for the demodulation.
        """
        pass

    @abstract_interface_method
    def get_output_mode(self):
        """Getter method for the output mode.

        @return (int) output_mode: output mode.
        """
        pass

    @abstract_interface_method
    def set_output_mode(self, output_mode):
        """Setter method for the output mode.

        @param (int) output_mode: output mode.
        """
        pass