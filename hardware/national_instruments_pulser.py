# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware interface for pulsing devices.

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

from core.util.modules import get_home_dir
import numpy as np
import ctypes
import os

import PyDAQmx as daq

from core.module import Base
from core.configoption import ConfigOption
from interface.pulser_interface import PulserInterface, PulserConstraints
from collections import OrderedDict


class NationalInstrumentsPulser(Base, PulserInterface):
    """ Pulse generator using NI-DAQmx

    Example config for copy-paste:

    ni_pulser:
        module.Class: 'national_instruments_pulser.NationalInstrumentsPulser'
        device: '/Dev1/'
        digital_outputs: ['PFI1', 'PFI2', 'PFI3', 'PFI4']
    """

    digital_outputs = ConfigOption('digital_outputs', missing='error')
    analog_outputs = ConfigOption('analog_outputs', missing='error')
    device = ConfigOption('Device', missing='error')

    def on_activate(self):
        """ Activate module """
        self._task = daq.TaskHandle()
        daq.DAQmxCreateTask('NI Pulser', daq.byref(self._task))
        self._build_constraints()

    def on_deactivate(self):
        """ Deactivate module """

        daq.DAQmxClearTask(self.pulser_task)

    def init_constraints(self):
        """ Build a pulser constraints dictionary with information from the NI card. """

        constraints = PulserConstraints()

        do_max_freq = daq.float64()
        daq.DAQmxGetDevDOMaxRate(self.device, daq.byref(do_max_freq))
        constraints.sample_rate.min = 1
        constraints.sample_rate.max = do_max_freq.value
        constraints.step = 0.0
        constraints.unit = 'Hz'

        constraints.d_ch_low.min = 0.0
        constraints.d_ch_low.max = 0.0
        constraints.d_ch_low.step = 0.0
        constraints.d_ch_low.default = 0.0
        constraints.d_ch_low.unit = 'V'

        constraints.d_ch_high.min = 5.0
        constraints.d_ch_high.max = 5.0
        constraints.d_ch_high.step = 0.0
        constraints.d_ch_high.default = 5.0
        constraints.d_ch_high.unit = 'V'

        # Minimum instruction time in clock cycles specified in the config,
        constraints.waveform_length.min = self._min_instr_len
        constraints.waveform_length.max = 2 ** 20 - 1
        constraints.waveform_length.step = 1
        constraints.waveform_length.default = 128

        activation_config = OrderedDict()
        activation_config['4_ch'] = frozenset({'d_ch1', 'd_ch2', 'd_ch3', 'd_ch4'})
        activation_config['all'] = frozenset({'d_ch1', 'd_ch2', 'd_ch3', 'd_ch4',
                                              'd_ch5', 'd_ch6', 'd_ch7', 'd_ch8',
                                              'd_ch9', 'd_ch10', 'd_ch11', 'd_ch12',
                                              'd_ch13', 'd_ch14', 'd_ch15', 'd_ch16',
                                              'd_ch17', 'd_ch18', 'd_ch19', 'd_ch20',
                                              'd_ch21'})

        constraints.activation_config = activation_config



        constraints = {}
        ch_map = OrderedDict()

        n = 2048

        ao_min_freq = daq.float64()
        ao_physical_chans = ctypes.create_string_buffer(n)
        ao_voltage_ranges = np.zeros(16, dtype=np.float64)
        ao_clock_support = daq.bool32()
        do_max_freq = daq.float64()
        do_lines = ctypes.create_string_buffer(n)
        do_ports = ctypes.create_string_buffer(n)
        product_dev_type = ctypes.create_string_buffer(n)
        product_cat = daq.int32()
        serial_num = daq.uInt32()
        product_num = daq.uInt32()



        daq.DAQmxGetDevAOSampClkSupported(device, daq.byref(ao_clock_support))
        self.log.debug('Analog supports clock: {0}'.format(ao_clock_support.value))
        daq.DAQmxGetDevAOPhysicalChans(device, ao_physical_chans, n)
        analog_channels = str(ao_physical_chans.value, encoding='utf-8').split(', ')
        self.log.debug('Analog channels: {0}'.format(analog_channels))
        daq.DAQmxGetDevAOVoltageRngs(
            device,
            ao_voltage_ranges.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            len(ao_voltage_ranges))
        self.log.debug('Analog voltage range: {0}'.format(ao_voltage_ranges[0:2]))

        daq.DAQmxGetDevDOMaxRate(self.device, daq.byref(do_max_freq))
        self.log.debug('Digital max freq: {0}'.format(do_max_freq.value))
        daq.DAQmxGetDevDOLines(device, do_lines, n)
        digital_channels = str(do_lines.value, encoding='utf-8').split(', ')
        self.log.debug('Digital channels: {0}'.format(digital_channels))
        daq.DAQmxGetDevDOPorts(device, do_ports, n)
        digital_bundles = str(do_ports.value, encoding='utf-8').split(', ')
        self.log.debug('Digital ports: {0}'.format(digital_bundles))

        daq.DAQmxGetDevSerialNum(device, daq.byref(serial_num))
        self.log.debug('Card serial number: {0}'.format(serial_num.value))
        daq.DAQmxGetDevProductNum(device, daq.byref(product_num))
        self.log.debug('Product number: {0}'.format(product_num.value))
        daq.DAQmxGetDevProductType(device, product_dev_type, n)
        product = str(product_dev_type.value, encoding='utf-8')
        self.log.debug('Product name: {0}'.format(product))
        daq.DAQmxGetDevProductCategory(device, daq.byref(product_cat))
        self.log.debug(product_cat.value)

        for n, ch in enumerate(analog_channels):
            ch_map['a_ch{0:d}'.format(n+1)] = ch

        for n, ch in enumerate(digital_channels):
            ch_map['d_ch{0:d}'.format(n+1)] = ch

        constraints['sample_rate'] = {
            'min': ao_min_freq.value,
            'max': ao_max_freq.value,
            'step': 0.0,
            'unit': 'Samples/s'}

        # The file formats are hardware specific. The sequence_generator_logic will need this
        # information to choose the proper output format for waveform and sequence files.
        constraints['waveform_format'] = 'ndarray'
        constraints['sequence_format'] = None

        # the stepsize will be determined by the DAC in combination with the
        # maximal output amplitude (in Vpp):
        constraints['a_ch_amplitude'] = {
            'min': 0,
            'max': ao_voltage_ranges[1],
            'step': 0.0,
            'unit': 'Vpp'}
        constraints['a_ch_offset'] = {
            'min': ao_voltage_ranges[0],
            'max': ao_voltage_ranges[1],
            'step': 0.0,
            'unit': 'V'}
        constraints['d_ch_low'] = {
            'min': 0.0,
            'max': 0.0,
            'step': 0.0,
            'unit': 'V'}
        constraints['d_ch_high'] = {
            'min': 5.0,
            'max': 5.0,
            'step': 0.0,
            'unit': 'V'}
        constraints['sampled_file_length'] = {
            'min': 2,
            'max': 1e12,
            'step': 0,
            'unit': 'Samples'}
        constraints['digital_bin_num'] = {
            'min': 2,
            'max': 1e12,
            'step': 0,
            'unit': '#'}
        constraints['waveform_num'] = {
            'min': 1,
            'max': 1,
            'step': 0,
            'unit': '#'}
        constraints['sequence_num'] = {
            'min': 0,
            'max': 0,
            'step': 0,
            'unit': '#'}
        constraints['subsequence_num'] = {
            'min': 0,
            'max': 0,
            'step': 0,
            'unit': '#'}

        # If sequencer mode is enable than sequence_param should be not just an
        # empty dictionary.
        sequence_param = OrderedDict()
        constraints['sequence_param'] = sequence_param

        activation_config = OrderedDict()
        activation_config['analog_only'] = [k for k in ch_map.keys() if k.startswith('a')]
        activation_config['digital_only'] = [k for k in ch_map.keys() if k.startswith('d')]
        activation_config['stuff'] = ['a_ch4', 'd_ch1', 'd_ch2', 'd_ch3', 'd_ch4']
        constraints['activation_config'] = activation_config

        self.channel_map = ch_map
        self.constraints = constraints

    def configure_pulser_task(self):
        """ Clear pulser task and set to current settings.

        @return:
        """
        a_channels = [self.channel_map[k] for k in self.a_names]
        d_channels = [self.channel_map[k] for k in self.d_names]

        # clear task
        daq.DAQmxClearTask(self.pulser_task)

        # add channels
        if len(a_channels) > 0:
            daq.DAQmxCreateAOVoltageChan(
                self.pulser_task,
                ', '.join(a_channels),
                ', '.join(self.a_names),
                self.min_volts,
                self.max_volts,
                daq.DAQmx_Val_Volts,
                '')

        if len(d_channels) > 0:
            daq.DAQmxCreateDOChan(
                self.pulser_task,
                ', '.join(d_channels),
                ', '.join(self.d_names),
                daq.DAQmx_Val_ChanForAllLines)

        # set sampling frequency
            daq.DAQmxCfgSampClkTiming(
                self.pulser_task,
                'OnboardClock',
                self.sample_rate,
                daq.DAQmx_Val_Rising,
                daq.DAQmx_Val_ContSamps,
                10 * self.sample_rate)

        # write assets

    def get_constraints(self):
        """ Retrieve the hardware constrains from the Pulsing device. """
        return self.constraints

    def pulser_on(self):
        """ Switches the pulsing device on. """
        daq.DAQmxStartTask(self.pulser_task)

    def pulser_off(self):
        """ Switches the pulsing device off. """
        daq.DAQmxStopTask(self.pulser_task)

    def load_asset(self, asset_name, load_dict=None):
        """ Loads a sequence or waveform to the specified channel of the pulsing device. """

    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM/workspace. """
        pass

    def get_status(self):
        """ Retrieves the status of the pulsing hardware """
        status_dict = {
            -1: 'Failed Request or Communication',
            0: 'Device has stopped, but can receive commands.',
            1: 'Device is active and running.'
        }
        task_done = daq.bool32
        try:
            daq.DAQmxIsTaskDone(self.pulser_task, daq.byref(task_done))
            current_status = 0 if task_done.value else 1
        except:
            self.log.exception('Error while getting pulser state.')
            current_status = -1
        return current_status, status_dict

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware """
        rate = daq.float64()
        daq.DAQmxGetSampClkRate(self.pulser_task, daq.byref(rate))
        return rate.value

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware. """
        task = self.pulser_task
        source = 'OnboardClock'
        rate = sample_rate
        edge = daq.DAQmx_Val_Rising
        mode = daq.DAQmx_Val_ContSamps
        samples = 10000
        daq.DAQmxCfgSampClkTiming(task, source, rate, edge, mode, samples)
        self.sample_rate = self.get_sample_rate()
        return self.sample_rate

    def get_analog_level(self, amplitude=None, offset=None):
        """ Retrieve the analog amplitude and offset of the provided channels. """
        amp_dict = {}
        off_dict = {}

        return amp_dict, off_dict

    def set_analog_level(self, amplitude=None, offset=None):
        """ Set amplitude and/or offset value of the provided analog channel(s). """
        return self.get_analog_level(amplitude, offset)

    def get_digital_level(self, low=None, high=None):
        """ Retrieve the digital low and high level of the provided/all channels. """
        # all digital levels are 5V or whatever the hardware provides and is not changeable
        channels = self.get_active_channels()

        if low is None:
            low_dict = {ch: 0 for ch, v in channels.items() if v}
        else:
            low_dict = {ch: 0 for ch in low}

        if high is None:
            high_dict = {ch: 5 for ch, v in channels.items() if v}
        else:
            high_dict = {ch: 5 for ch in high}

        return low_dict, high_dict

    def set_digital_level(self, low=None, high=None):
        """ Set low and/or high value of the provided digital channel. """
        pass # digital levels not settable on NI card
        return self.get_digital_level(low, high)

    def get_active_channels(self, ch=None):
        """ Get the active channels of the pulse generator hardware. """
        buffer_size = 2048
        buf = ctypes.create_string_buffer(buffer_size)
        daq.DAQmxGetTaskChannels(self.pulser_task, buf, buffer_size)
        ni_ch = str(buf.value, encoding='utf-8').split(', ')

        if ch is None:
            return {k: k in ni_ch for k, v in self.channel_map.items()}
        else:
            return {k: k in ni_ch for k in ch}

    def set_active_channels(self, ch=None):
        """ Set the active/inactive channels for the pulse generator hardware. """
        self.a_names = [k for k, v in ch.items() if k.startswith('a') and v]
        self.a_names.sort()

        self.d_names = [k for k, v in ch.items() if k.startswith('d') and v]
        self.d_names.sort()

        self.configure_pulser_task()  # apply changed channels
        return self.get_active_channels()

    def get_interleave(self):
        """ Check whether Interleave is ON or OFF in AWG."""
        return False  # always return False for pulse generator hardware without interleave.

    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off. """
        return False  # Unused for pulse generator hardware other than an AWG.

    def reset(self):
        """ Reset the device. """
        daq.DAQmxResetDevice(self.device)
