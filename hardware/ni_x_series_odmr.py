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
from interface.odmr_counter_interface import ODMRCounterInterface


class NationalInstrumentsXSeriesODMR(Base, ODMRCounterInterface):
    """ A National Instruments device that can count photons and measure analog voltage to perform ODMR

    This module can be used to measure luminescence in the photon counting regime via a counter / photon source OR via
    an APD in linear mode through the analog input OR both

    The way this module is working is by setting up a clock at the acquisition frequency and with the number of pulses
    corresponding to the number of samples to acquire.
    The counting task and analog input task measure samples at clock cycles, in continuous mode.
    At the end of the line, all the available samples are read. If number of sample available is different from theoretical
     value, there is a problem in the counting triggering.
    The clock also serve as trigger for the MW generator to switch to the next frequency.

    Example config for copy-paste:

    nicard_odmr:
        module.Class: 'ni_x_series_odmr.NationalInstrumentsXSeriesODMR'
        clock_channel: '/Dev1/Ctr2'
        trigger_channel: '/Dev1/PFI7'
        photon_sources:
            - '/Dev1/PFI8'
        counter_channels:
            - '/Dev1/Ctr3'
        max_counts: 3e7
        counting_edge_rising: True
        ai_channels:
            - '/Dev1/AI1'
        min_voltage: -10
        max_voltage: 10
        timeout: 10
    """

    _clock_channel = ConfigOption('clock_channel', missing='error')
    _trigger_channel = ConfigOption('trigger_channel', missing='error')
    # For photon counting regime :
    _photon_sources = ConfigOption('photon_sources', [])
    _counter_channels = ConfigOption('counter_channels', [])  # the counter number i is linked to photon source number i
    _max_counts = ConfigOption('max_counts', default=3e7)
    _counting_edge_rising = ConfigOption('counting_edge_rising', default=True)
    # For linear regime :
    _ai_channels = ConfigOption('ai_channels', [], missing='info')
    _min_voltage = ConfigOption('min_voltage', -10)  # The NI doc states this can help  PYDAQmx choose better settings
    _max_voltage = ConfigOption('max_votlage', 10)
    _ai_differential = ConfigOption('ai_differential', False)
    # Advanced analog feature:
    _use_max_sample_rate = ConfigOption('use_max_sample_rate', False) # Use an internal clock to measure analog input at max frequency
    _fast_clock_channel = ConfigOption('fast_clock_channel', None)  # If previous is true, specify a clock channel

    _buffer_size_margin = ConfigOption('buffer_size_margin', int(1e3))  # size of buffer for counter and AI
    _timeout = ConfigOption('timeout', default=30)

    def on_activate(self):
        """ Starts up the NI Card at activation. """
        self._clock_task = None # Can not create clock task before knowing the frequency, this is done later
        self._counter_tasks = []
        self._ai_tasks = []
        self._clock_frequency = 1  # Not None so that there is no bug if set_odmr_length is first called
        self._odmr_length = 1  # Not None so that there is no bug if set_up_odmr_clock is first called
        self._fast_clock_task = None
        self._oversampling_ai = 1

        for i, channel in enumerate(self._counter_channels):
            task = daq.TaskHandle()
            daq.DAQmxCreateTask(f'odmr counter {i}', daq.byref(task))
            daq.DAQmxCreateCICountEdgesChan(task, channel, f'odmr counter channel {i}', daq.DAQmx_Val_Rising, 0, daq.DAQmx_Val_CountUp)
            daq.DAQmxSetCICountEdgesTerm(task, channel, self._photon_sources[i])
            daq.DAQmxCfgSampClkTiming(task, self._clock_channel + 'InternalOutput', 6666, daq.DAQmx_Val_Rising, daq.DAQmx_Val_ContSamps, 0)
            daq.DAQmxSetReadRelativeTo(task, daq.DAQmx_Val_CurrReadPos)
            daq.DAQmxSetReadOffset(task, 0)
            daq.DAQmxSetReadOverWrite(task, daq.DAQmx_Val_DoNotOverwriteUnreadSamps)
            self._counter_tasks.append(task)

        for i, channel in enumerate(self._ai_channels):
            task = daq.TaskHandle()
            daq.DAQmxCreateTask(f'odmr ai {i}', daq.byref(task))
            ai_mode = daq.DAQmx_Val_Diff if self._ai_differential else daq.DAQmx_Val_RSE
            daq.DAQmxCreateAIVoltageChan(task, self._ai_channels[i], f'odmr ai channel {i}',
                                         ai_mode, self._min_voltage, self._max_voltage, daq.DAQmx_Val_Volts, '')
            daq.DAQmxCfgSampClkTiming(task, self._clock_channel + 'InternalOutput', 6666,daq.DAQmx_Val_Rising, daq.DAQmx_Val_ContSamps, 0)
            self._ai_tasks.append(task)

        # If this feature is on, we create a second clock at the AI max sampling rate
        if self._use_max_sample_rate and len(self._ai_tasks) :
            max_sampling_rate = daq.c_double()
            daq.DAQmxGetAIConvMaxRate(self._ai_tasks[0], daq.byref(max_sampling_rate))
            self.ai_max_sampling_rate = max_sampling_rate.value
            self._fast_clock_task = daq.TaskHandle()
            daq.DAQmxCreateTask('odmr_fast_clock', daq.byref(self._fast_clock_task))
            daq.DAQmxCreateCOPulseChanFreq(self._fast_clock_task, self._fast_clock_channel, 'odmr fast clock producer',
                                           daq.DAQmx_Val_Hz, daq.DAQmx_Val_Low, 0, self.ai_max_sampling_rate, 0.5)
            daq.DAQmxCfgDigEdgeStartTrig(self._fast_clock_task, self._clock_channel + 'InternalOutput', daq.DAQmx_Val_Rising)  # Synchronize the second clock with the first one
            daq.SetStartTrigRetriggerable(self._fast_clock_task, True)

    def on_deactivate(self):
        """ Shut down the NI card.  """

        self.close_odmr_clock()
        self.close_odmr()

        for task in self._counter_tasks + self._ai_tasks:
            try:
                daq.DAQmxStopTask(task)
                daq.DAQmxClearTask(task)
            except:
                self.log.warning('Could not close one odmr counter / ai task.')
        if self._use_max_sample_rate:
            try:
                daq.DAQmxStopTask(self._fast_clock_task)
                daq.DAQmxClearTask(self._fast_clock_task)
                self._fast_clock_task = None
            except:
                pass

        self._counter_tasks = []
        self._ai_tasks = []

    def set_up_odmr_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.
        @param float clock_frequency: if defined, this sets the frequency of  the clock in Hz
        @pram str clock_channel: deprecated, the logic should not handle this
        """
        self._clock_frequency = clock_frequency

        if self._clock_task is not None:
            daq.DAQmxClearTask(self._clock_task)
        self._clock_task = daq.TaskHandle()
        daq.DAQmxCreateTask('odmr_clock', daq.byref(self._clock_task))
        daq.DAQmxCreateCOPulseChanFreq(self._clock_task, self._clock_channel, 'odmr clock producer',
                                       daq.DAQmx_Val_Hz, daq.DAQmx_Val_Low, 0, clock_frequency, 0.5)
        daq.DAQmxCfgImplicitTiming(self._clock_task, daq.DAQmx_Val_FiniteSamps,  self._odmr_length+1)

        if self._use_max_sample_rate:
            oversampling = int(self.ai_max_sampling_rate / self._clock_frequency * 0.95)  # 5% margin for safety
            daq.DAQmxCfgImplicitTiming(self._fast_clock_task, daq.DAQmx_Val_FiniteSamps, oversampling)
            self._oversampling_ai = oversampling

        # set the AI buffer length otherwise we have an error
        for i, task in enumerate(self._ai_tasks):
            daq.DAQmxCfgSampClkTiming(task, self._fast_clock_channel + 'InternalOutput', 6666, daq.DAQmx_Val_Rising,
                                      daq.DAQmx_Val_ContSamps, (self._odmr_length+1)*self._oversampling_ai+self._buffer_size_margin)
        return 0

    def close_odmr_clock(self):
        """ Closes the clock and cleans up afterward. """
        if self._clock_task is not None:
            daq.DAQmxStopTask(self._clock_task)
            daq.DAQmxClearTask(self._clock_task)
            self._clock_task = None
        if self._use_max_sample_rate:
            daq.DAQmxStopTask(self._fast_clock_task)
        return 0

    def set_up_odmr(self, counter_channel=None, photon_source=None, clock_channel=None, odmr_trigger_channel=None):
        """ Configures the counter task
        All the parameters are deprecated, the logic should not handle this. This method is called with no parameters.
        """
        daq.DAQmxConnectTerms(self._clock_channel + 'InternalOutput', self._trigger_channel,  daq.DAQmx_Val_DoNotInvertPolarity)
        return 0

    def close_odmr(self):
        """ Closes the odmr and cleans up afterward. """
        daq.DAQmxDisconnectTerms(self._clock_channel + 'InternalOutput', self._trigger_channel)
        return 0

    def set_odmr_length(self, length=100):
        """ Sets up the trigger sequence for the ODMR and the triggered microwave. """

        self._odmr_length = length
        self.set_up_odmr_clock(self._clock_frequency)

    def get_odmr_channels(self):
        return self._counter_channels + self._ai_channels

    def count_odmr(self, length=100):
        """ Sweeps the microwave and returns the counts on that sweep.

        @param int length: length of microwave sweep in pixel
        @return float[]: the photon counts per second
        """
        self.set_odmr_length(length)
        task_list = self._counter_tasks + self._ai_tasks + [self._clock_task]
        task_list = [self._fast_clock_task] + task_list if self._fast_clock_task is not None else task_list
        for task in task_list:
            try:
                daq.DAQmxStartTask(task)
            except daq.DAQmxFunctions.PALResourceReservedError:
                self.log.error('Can not start odmr, ni resource already busy.')
                return True, []

        daq.DAQmxWaitUntilTaskDone(self._clock_task, self._timeout)

        count_data = np.zeros((len(self._counter_tasks), length+1))
        for i, task in enumerate(self._counter_tasks):
            raw_data = np.zeros(length+1+self._buffer_size_margin, dtype=np.uint32)
            n_read_samples = daq.int32()  # number of samples which were actually read, will be stored here
            daq.DAQmxReadCounterU32(task, -1, self._timeout, raw_data, raw_data.size, daq.byref(n_read_samples), None)
            count_data[i] = raw_data[:length+1]
            if n_read_samples.value != length+1:
                self.log.warning(f'In counter {i}, {n_read_samples.value} were read instead of {length+1}')
        count_data = np.diff(count_data, axis=1).astype(np.float64) * self._clock_frequency  # drop first value

        ai_data = np.zeros((len(self._ai_tasks), length+1))
        for i, task in enumerate(self._ai_tasks):
            raw_data = np.zeros((length+1)*self._oversampling_ai+self._buffer_size_margin, dtype=np.float64)
            n_read_samples = daq.int32()
            daq.DAQmxReadAnalogF64(task, -1, self._timeout, daq.DAQmx_Val_GroupByChannel, raw_data, raw_data.size, daq.byref(n_read_samples), None)

            if self._use_max_sample_rate:
                oversamples_length = (length+1)*self._oversampling_ai
                raw_data = raw_data[:oversamples_length]
                if n_read_samples.value != oversamples_length:
                    self.log.warning(f'In ADC {i}, {n_read_samples.value} were read instead of {oversamples_length}')
                ai_data[i] = raw_data.reshape((length+1, self._oversampling_ai)).mean(axis=1)
            else:
                if n_read_samples.value != length+1:
                    self.log.warning(f'In ADC {i}, {n_read_samples.value} were read instead of {length+1}')
                ai_data[i] = raw_data[:length+1]
            ai_data = ai_data[:, :-1]  # drop last point

        if len(ai_data) == 0 or len(count_data) == 0:
            all_data = count_data if len(ai_data) == 0 else ai_data
        else:
            all_data = np.vstack((count_data, ai_data))

        for task in task_list:
            daq.DAQmxStopTask(task)
        return False, all_data


# Below are deprecated features that are ignored by this hardware

    @property
    def oversampling(self):
        return self._oversampling

    @oversampling.setter
    def oversampling(self, val):
        self._oversampling = int(val)
    @property
    def lock_in_active(self):
        return self._lock_in_active

    @lock_in_active.setter
    def lock_in_active(self, val):
        self._lock_in_active = bool(val)
