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
import ctypes as ct

from core.module import Base
from core.configoption import ConfigOption

from interface.slow_counter_interface import SlowCounterInterface, SlowCounterConstraints, CountingMode


class Photomultiplier(Base, SlowCounterInterface):
    """ Define the controls for a slow counter.

    A slow counter is a measuring device that measures with a precise frequency one or multiple physical quantities.

    An example is a device that counts photons in real time with a given frequency.

    The main idea of such a device is that the hardware handles the timing, and measurement of one or multiple
    time varying quantities. The logic will periodically (but with imprecise timing) poll the hardware for the new
    reading, not knowing if there is one, multiple or none.
    """

    _max_detectors = ConfigOption('max_detectors', 1)
    _min_count_frequency = ConfigOption('min_count_frequency', 5e-5)  # Temperature in °C (not Kelvin !)
    _max_count_frequency = ConfigOption('max_count_frequency',5e5)
    _counting_mode = ConfigOption('counting_mode', CountingMode.CONTINUOUS)

    def on_activate(self):

        self._constraints = SlowCounterConstraints()
        self._constraints._max_detectors = self._max_detectors
        self._constraints.min_count_frequency = self._min_count_frequency
        self._constraints._max_count_frequency = self._max_count_frequency
        self._constraints._counting_mode = self._counting_mode
        pass

    def on_deactivate(self):
        pass

    def get_constraints(self):
        """ Retrieve the hardware constrains from the counter device.

        @return (SlowCounterConstraints): object with constraints for the counter

        The constrains are defined as a SlowCounterConstraints object, defined at  the end of this file
        """
        return self._constraints

    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        """ Set the frequency of the counter by configuring the hardware clock

        @param (float) clock_frequency: if defined, this sets the frequency of the clock
        @param (string) clock_channel: if defined, this is the physical channel of the clock
        @return int: error code (0:OK, -1:error)

        TODO: Should the logic know about the different clock channels ?
        """
        pass

    def set_up_counter(self,
                       counter_channels=None,
                       sources=None,
                       clock_channel=None,
                       counter_buffer=None):
        """ Configures the actual counter with a given clock.

        @param list(str) counter_channels: optional, physical channel of the counter
        @param list(str) sources: optional, physical channel where the photons
                                   photons are to count from
        @param str clock_channel: optional, specifies the clock channel for the
                                  counter
        @param int counter_buffer: optional, a buffer of specified integer
                                   length, where in each bin the count numbers
                                   are saved.

        @return int: error code (0:OK, -1:error)

        There need to be exactly the same number sof sources and counter channels and
        they need to be given in the same order.
        All counter channels share the same clock.
        """
        pass

    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go

        @return numpy.array((n, uint32)): the measured quantity of each channel
        """
        pass

    def get_counter_channels(self):
        """ Returns the list of counter channel names.

        @return list(str): channel names

        Most methods calling this might just care about the number of channels, though.
        """
        pass

    def close_counter(self):
        """ Closes the counter and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass

    def close_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)

        TODO: This method is very hardware specific, it should be deprecated
        """
        pass