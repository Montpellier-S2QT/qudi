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
    _counter_channels = ConfigOption('counter_channels', [])  # the counter number i is linked to digital pulses source number i
    _max_counts = ConfigOption('max_counts', default=3e7)  # info requested by the NI card
    _counting_edge_rising = ConfigOption('counting_edge_rising', default=True)
    # For analog input :
    _ai_channels = ConfigOption('ai_channels', [])
    _min_voltage = ConfigOption('min_voltage', -10)  # The NI doc states this can help  PYDAQmx choose better settings
    _max_voltage = ConfigOption('max_votlage', 10)
    # Advanced analog feature:
    _use_max_sample_rate = ConfigOption('use_max_sample_rate', False) # Use an internal clock to measure analog input at max frequency
    _fast_clock_channel = ConfigOption('fast_clock_channel', None)  # If previous is true, specify a clock channel

    _buffer_size = ConfigOption('buffer_size_margin', int(1e3))  # size of buffer for counter and AI
    _timeout = ConfigOption('timeout', default=30)

    def on_activate(self):
        """ Starts up the NI Card at activation. """
        self._clock_task = None # Can not create clock task before knowing the frequency, this is done later
        self._counter_tasks = []
        self._ai_tasks = []
        self._clock_frequency = None
        self._fast_clock_task = None
        self._oversampling_ai = 1
        self._last_counts = []

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

        for i, channel in enumerate(self._ai_channels):
            task = daq.TaskHandle()
            daq.DAQmxCreateTask(f'slow counter ai {i}', daq.byref(task))
            daq.DAQmxCreateAIVoltageChan(task, self._ai_channels[i], f'slow counter ai channel {i}',
                                         daq.DAQmx_Val_RSE, self._min_voltage, self._max_voltage, daq.DAQmx_Val_Volts, '')
            daq.DAQmxCfgSampClkTiming(task, self._clock_channel + 'InternalOutput', 6666,daq.DAQmx_Val_Rising, daq.DAQmx_Val_ContSamps, 0)
            self._ai_tasks.append(task)

        # # If this feature is on, we create a second clock at the AI max sampling rate
        # if self._use_max_sample_rate and len(self._ai_tasks) > 0:
        #     max_sampling_rate = daq.c_double()
        #     daq.DAQmxGetAIConvMaxRate(self._ai_tasks[0], daq.byref(max_sampling_rate))
        #     self.ai_max_sampling_rate = max_sampling_rate.value
        #     self._fast_clock_task = daq.TaskHandle()
        #     daq.DAQmxCreateTask('slow_fast_clock', daq.byref(self._fast_clock_task))
        #     daq.DAQmxCreateCOPulseChanFreq(self._fast_clock_task, self._fast_clock_channel, 'slow counter fast clock',
        #                                    daq.DAQmx_Val_Hz, daq.DAQmx_Val_Low, 0, self.ai_max_sampling_rate, 0.5)
        #     daq.DAQmxCfgDigEdgeStartTrig(self._fast_clock_task, self._clock_channel + 'InternalOutput', daq.DAQmx_Val_Rising)  # Synchronize the second clock with the first one
        #     daq.SetStartTrigRetriggerable(self._fast_clock_task, True)

    def on_deactivate(self):
        """ Shut down the NI card.  """
        self.close_clock()
        self.close_counter()
        for task in self._counter_tasks + self._ai_tasks:
            try:
                daq.DAQmxClearTask(task)
            except:
                self.log.warning('Could not close one counter / ai task.')
        # if self._use_max_sample_rate:
        #     try:
        #         daq.DAQmxStopTask(self._fast_clock_task)
        #         daq.DAQmxClearTask(self._fast_clock_task)
        #         self._fast_clock_task = None
        #     except:
        #         pass
        self._counter_tasks = []
        self._ai_tasks = []

    def get_constraints(self):
        """ Get hardware limits of NI device.  """
        constraints = SlowCounterConstraints()
        constraints.max_detectors = len(self._counter_channels) + len(self._ai_channels)
        constraints.min_count_frequency = 1e-3
        constraints.max_count_frequency = 1e6
        constraints.counting_mode = [CountingMode.CONTINUOUS]
        return constraints

    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.
        @param float clock_frequency: if defined, this sets the frequency of  the clock in Hz
        @pram str clock_channel: deprecated, the logic should not handle this

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

        # if self._use_max_sample_rate:
        #     oversampling = int(self.ai_max_sampling_rate / self._clock_frequency * 0.95)  # 5% margin for safety
        #     daq.DAQmxCfgImplicitTiming(self._fast_clock_task, daq.DAQmx_Val_ContSamps, oversampling)
        #     self._oversampling_ai = oversampling
        #
        #     # set the AI buffer length otherwise we have an error
        #     for i, task in enumerate(self._ai_tasks):
        #         daq.DAQmxCfgSampClkTiming(task, self._fast_clock_channel + 'InternalOutput', 6666, daq.DAQmx_Val_Rising,
        #                                   daq.DAQmx_Val_ContSamps, 1)
        return 0

    def close_clock(self):
        """ Closes the clock and cleans up afterward. """
        if self._clock_task is not None:
            daq.DAQmxStopTask(self._clock_task)
            daq.DAQmxClearTask(self._clock_task)
            self._clock_task = None
        # if self._use_max_sample_rate:
        #     daq.DAQmxStopTask(self._fast_clock_task)
        return 0

    def close_counter(self):
        task_list = self._counter_tasks + self._ai_tasks
        for task in task_list:
            daq.DAQmxStopTask(task)
        return 0

    def set_up_counter(self, counter_channels=None, sources=None, clock_channel=None, counter_buffer=None):
        """ """
        task_list = self._counter_tasks + self._ai_tasks + [self._clock_task]
        # task_list = [self._fast_clock_task] + task_list if self._fast_clock_task is not None else task_list
        for task in task_list:
            daq.DAQmxStartTask(task)
        self._last_counts = np.zeros(len(self._counter_tasks))
        return 0

    def get_counter_channels(self):
        return self._counter_channels + self._ai_channels

    def get_counter(self, samples=None):
        """ Returns the counts.
        @return float[]: the photon counts per second
        """
        if len(self._counter_tasks) > 0:
            # 1. Get data from hardware
            raw_count_data = []
            for i, task in enumerate(self._counter_tasks):
                raw_data = np.zeros(self._buffer_size, dtype=np.uint32)
                n_read_samples = daq.int32()  # number of samples which were actually read, will be stored here
                daq.DAQmxReadCounterU32(task, -1, self._timeout, raw_data, raw_data.size, daq.byref(n_read_samples), None)
                raw_count_data.append(raw_data[:n_read_samples.value])
            # 2. Deal with data length if multiple counters
            min_length_di = min(arr.size for arr in raw_count_data)
            if not all(arr.size == min_length_di for arr in raw_count_data):
                self.log.warning("Not all arrays have the same size. Arrays will be truncated to the smallest size.")
                raw_count_data = [arr[:min_length_di] for arr in raw_count_data]
            raw_count_data = np.vstack(raw_count_data)
            # 3. Deal with counter overflows
            if min_length_di > 0:
                overflow_indices = np.where(raw_count_data[:, 0] < self._last_counts)
                self._last_counts[overflow_indices] -= 2 ** 32
                count_data = raw_count_data - self._last_counts
                diff_data = np.diff(count_data, axis=1)
                count_data = np.hstack((count_data[:, [0]], diff_data)).astype(np.float64) * self._clock_frequency
                self._last_counts = raw_count_data[:, -1]
            else:
                count_data = raw_count_data

        if len(self._ai_tasks) > 0:
            # 1. Get data from hardware
            raw_ai_data = []
            for i, task in enumerate(self._ai_tasks):
                raw_data = np.zeros(self._buffer_size, dtype=np.float64)
                n_read_samples = daq.int32()
                daq.DAQmxReadAnalogF64(task, -1, self._timeout, daq.DAQmx_Val_GroupByChannel, raw_data, raw_data.size,
                                       daq.byref(n_read_samples), None)
                raw_ai_data.append(raw_data[:n_read_samples.value])
            # 2. Deal with data length if multiple analog inputs
            min_length_ai = min(arr.size for arr in raw_ai_data)
            if not all(arr.size == min_length_ai for arr in raw_ai_data):
                self.log.warning("Not all AI arrays have the same size. Arrays will be truncated to the smallest size.")
                raw_ai_data = [arr[:min_length_ai] for arr in raw_ai_data]
            ai_data = np.vstack(raw_ai_data)

            # if self._use_max_sample_rate:
            #     oversamples_length = (length+1)*self._oversampling_ai
            #     raw_data = raw_data[:oversamples_length]
            #     if n_read_samples.value != oversamples_length:
            #         self.log.warning(f'In ADC {i}, {n_read_samples.value} were read instead of {oversamples_length}')
            #     ai_data[i] = raw_data.reshape((length+1, self._oversampling_ai)).mean(axis=1)
            # else:
            #     if n_read_samples.value != length+1:
            #         self.log.warning(f'In ADC {i}, {n_read_samples.value} were read instead of {length+1}')
            #     ai_data[i] = raw_data[:length+1]
            # ai_data = ai_data[:, :-1]  # drop last point

        if len(self._counter_tasks) == 0 or len(self._ai_tasks) == 0:
            all_data = count_data if len(self._ai_tasks) == 0 else ai_data
        else:
            if min_length_di != min_length_ai:
                self.log.warning('Digital an analog input have different sizes.')
                s = min((min_length_di, min_length_ai))
                count_data, ai_data = count_data[:, :s], ai_data[:, :s]
            all_data = np.vstack((count_data, ai_data))
        return all_data
