# -*- coding: utf-8 -*-

"""
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
import PyDAQmx as daq

from core.module import Base
from core.configoption import ConfigOption
from interface.slow_counter_interface import SlowCounterInterface, SlowCounterConstraints, CountingMode


class NationalInstrumentsXSeriesSlowCounter(Base, SlowCounterInterface):
    """ A National Instruments device that can count photons and measure analog voltage

    This module can be used to measure luminescence in the photon counting regime via a counter / photon source OR via
    an APD in linear mode through the analog input OR both

    The way this module is working is by setting up a clock at the acquisition frequency.
    The counting task and analog input task measure samples at clock cycles, in continuous mode.

    Example config for copy-paste:


    """

    _clock_channel = ConfigOption('clock_channel', missing='error')
    # For photon counting regime :
    _photon_sources = ConfigOption('digital_pulses_sources', [])
    _counter_channels = ConfigOption('counter_channels', [])  # the counter #i is linked to digital pulses source #i
    _max_counts = ConfigOption('max_counts', default=3e7)  # info requested by the NI card
    _counting_edge_rising = ConfigOption('counting_edge_rising', default=True)
    # For analog input :
    _ai_channels = ConfigOption('ai_channels', [])
    _min_voltage = ConfigOption('min_voltage', -10)  # The NI doc states this can help  PYDAQmx choose better settings
    _max_voltage = ConfigOption('max_votlage', 10)

    _buffer_size = ConfigOption('buffer_size_margin', int(1e3))  # size of buffer for counter and AI
    _timeout = ConfigOption('timeout', default=30)

    def on_activate(self):
        """ Starts up the NI Card at activation. """
        self._clock_task = None  # Can not create clock task before knowing the frequency, this is done later
        self._counter_tasks = []
        self._ai_tasks = []  # we use an array but there will be 0 or 1, as 1 analog task can handle multiple channels
        self._clock_frequency = None
        self._last_counts = []  # The card just increment counters, we have to remember last values to find the diff

        for i, channel in enumerate(self._counter_channels):
            task = daq.TaskHandle()
            daq.DAQmxCreateTask(f'slower counter {i}', daq.byref(task))
            daq.DAQmxCreateCICountEdgesChan(task, channel, f'slower counter channel {i}', daq.DAQmx_Val_Rising, 0, daq.DAQmx_Val_CountUp)
            daq.DAQmxSetCICountEdgesTerm(task, channel, self._photon_sources[i])
            daq.DAQmxCfgSampClkTiming(task, self._clock_channel + 'InternalOutput', 6666, daq.DAQmx_Val_Rising, daq.DAQmx_Val_ContSamps, 0)
            daq.DAQmxSetReadRelativeTo(task, daq.DAQmx_Val_CurrReadPos)
            daq.DAQmxSetReadOffset(task, 0)
            daq.DAQmxSetReadOverWrite(task, daq.DAQmx_Val_DoNotOverwriteUnreadSamps)
            self._counter_tasks.append(task)

        if len(self._ai_channels) > 0:
            task = daq.TaskHandle()
            daq.DAQmxCreateTask(f'slow counter ai', daq.byref(task))
            for i, channel in enumerate(self._ai_channels):
                daq.DAQmxCreateAIVoltageChan(task, self._ai_channels[i], f'slow counter ai channel {i}',
                                             daq.DAQmx_Val_RSE, self._min_voltage, self._max_voltage, daq.DAQmx_Val_Volts, '')
                daq.DAQmxCfgSampClkTiming(task, self._clock_channel + 'InternalOutput', 6666,
                                          daq.DAQmx_Val_Rising, daq.DAQmx_Val_ContSamps, 0)
            self._ai_tasks.append(task)

    def on_deactivate(self):
        """ Shut down the NI card.  """
        self.close_clock()
        self.close_counter()
        for task in self._counter_tasks + self._ai_tasks:
            try:
                daq.DAQmxClearTask(task)
            except:
                self.log.warning('Could not close one counter / ai task.')
        self._counter_tasks = []
        self._ai_tasks = []

    def get_constraints(self):
        """ Get hardware limits of NI device.  """
        constraints = SlowCounterConstraints()
        constraints.max_detectors = len(self._counter_channels) + len(self._ai_channels)
        constraints.min_count_frequency = 1e-3
        constraints.max_count_frequency = self._max_counts
        constraints.counting_mode = [CountingMode.CONTINUOUS]
        return constraints

    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.
        @param (float) clock_frequency: sets the frequency of  the clock in Hz
        @pram (str) clock_channel: deprecated, the logic should not handle this

        The clock task needs to be created each time as the frequency can not be changed afterward
        """
        self._clock_frequency = clock_frequency
        if self._clock_task is not None:
            daq.DAQmxClearTask(self._clock_task)
        self._clock_task = daq.TaskHandle()
        daq.DAQmxCreateTask('slow_counter_clock', daq.byref(self._clock_task))
        daq.DAQmxCreateCOPulseChanFreq(self._clock_task, self._clock_channel, 'slower counter clock producer',
                                       daq.DAQmx_Val_Hz, daq.DAQmx_Val_Low, 0, clock_frequency, 0.5)
        daq.DAQmxCfgImplicitTiming(self._clock_task, daq.DAQmx_Val_ContSamps,  1)
        return 0

    def close_clock(self):
        """ Closes the clock and cleans up afterward. """
        if self._clock_task is not None:
            daq.DAQmxStopTask(self._clock_task)
            daq.DAQmxClearTask(self._clock_task)
            self._clock_task = None
        return 0

    def close_counter(self):
        task_list = self._counter_tasks + self._ai_tasks
        for task in task_list:
             daq.DAQmxStopTask(task)
        return 0

    def set_up_counter(self, counter_channels=None, sources=None, clock_channel=None, counter_buffer=None):
        """ The original goal is deprecated, so we just initiate the tasks here
        All parameters are ignored
        """
        task_list = self._counter_tasks + self._ai_tasks + [self._clock_task]
        for task in task_list:
            daq.DAQmxStartTask(task)
        self._last_counts = np.zeros(len(self._counter_tasks)).reshape(-1, 1)
        return 0

    def get_counter_channels(self):
        return self._counter_channels + self._ai_channels

    def get_counter(self, samples=None):
        """ Returns the counts.
        @return float[]: the photon counts per second
        """
        if len(self._counter_tasks) > 0:
            raw_count_data = np.empty((len(self._counter_tasks), samples), dtype=np.uint32)
            n_read_samples = daq.int32()  # number of samples which were actually read, will be stored here
            for i, task in enumerate(self._counter_tasks):
                # read the counter value: This function is blocking and waits for the counts to be all filled
                daq.DAQmxReadCounterU32(task, samples, self._timeout, raw_count_data[i], samples,
                                        daq.byref(n_read_samples), None)

            overflow_mask = raw_count_data[:, 0] < self._last_counts.flatten()
            self._last_counts[overflow_mask] -= 2 ** 32
            count_data = raw_count_data - self._last_counts
            diff_data = np.diff(count_data, axis=1)
            digital_data = np.hstack((count_data[:, [0]], diff_data)).astype(np.float64) * self._clock_frequency
            self._last_counts = raw_count_data[:, -1].reshape(-1, 1)

        if len(self._ai_tasks) > 0:
            analog_data = np.empty((len(self._ai_channels), samples), dtype=np.float64)
            n_read_samples = daq.int32()
            for i, task in enumerate(self._ai_tasks):
                daq.DAQmxReadAnalogF64(task, -1, self._timeout, daq.DAQmx_Val_GroupByChannel, analog_data, analog_data.size,
                                       daq.byref(n_read_samples), None)

        if len(self._counter_tasks) == 0 or len(self._ai_tasks) == 0:
            all_data = digital_data if len(self._ai_tasks) == 0 else analog_data
        else:
            all_data = np.vstack((digital_data, analog_data))
        return all_data
