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

import numpy as np
import nidaqmx

from core.module import Base
from core.configoption import ConfigOption
from interface.pulser_interface import PulserInterface, PulserConstraints
from collections import OrderedDict


class NationalInstrumentsPulser(Base, PulserInterface):
    """ Pulse generator using NI-DAQmx

    Example config for copy-paste:

    ni_pulser:
        module.Class: 'national_instruments_pulser.NationalInstrumentsPulser'
        device: 'Dev1'
        digital_outputs: ['PFI1', 'PFI2', 'PFI3', 'PFI4']
    """

    # digital_outputs = ConfigOption('digital_outputs', missing='error')
    # analog_outputs = ConfigOption('analog_outputs', missing='error')
    device = ConfigOption('Device', missing='error')

    def on_activate(self):
        """ Activate module """
        self._task = nidaqmx.Task()
        self._task.do_channels.add_do_chan(
            lines=f'{self.device}/port0/line0:7',
            line_grouping=nidaqmx.constants.LineGrouping.CHAN_FOR_ALL_LINES)

        self._build_constraints()

        self._current_waveform = None
        self._current_waveform_name = None

    def on_deactivate(self):
        """ Deactivate module """
        self._task.close()

    def init_constraints(self):
        """ Build a pulser constraints dictionary with information from the NI card. """

        constraints = PulserConstraints()

        constraints.sample_rate.min = 0
        constraints.sample_rate.max = self._task.timing.samp_clk_max_rate
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
        constraints.waveform_length.min = 1
        constraints.waveform_length.max = 2 ** 30  # here the computer memory is the limit
        constraints.waveform_length.step = 1
        constraints.waveform_length.default = 128

        activation_config = OrderedDict()
        activation_config['port0/line0:7'] = frozenset([f'/port0/line{i}' for i in range(8)])
        constraints.activation_config = activation_config

        self._constraints = constraints

    def get_constraints(self):
        """ Retrieve the hardware constrains from the Pulsing device. """
        return self._constraints

    def pulser_on(self):
        """ Switches the pulsing device on. """
        self._task.start()

    def pulser_off(self):
        """ Switches the pulsing device off. """
        self._task.stop()

    def load_waveform(self, load_dict):
        """ Loads a waveform to the specified channel of the pulsing device."""
        pass

    def load_sequence(self, sequence_name):
        """ Loads a sequence to the channels of the device in order to be ready for playback. """
        self.log.warning('NI card has no sequencing capabilities, load_sequence call ignored.')
        return {}

    def get_loaded_assets(self):
        """ Retrieve the currently loaded asset names for each active channel of the device."""
        asset_type = 'waveform' if self._current_waveform else None
        asset_dict = {}
        for index, entry in enumerate(self._constraints.activation_config):
            asset_dict[index+1] = self._current_waveform_name
        return asset_dict, asset_type


    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM/workspace. """
        pass

    def get_status(pulser_task):
        """Retrieves the status of the pulsing hardware."""
        status_dict = {
            -1: 'Failed Request or Communication',
            0: 'Device has stopped, but can receive commands.',
            1: 'Device is active and running.'
        }

        try:
            task_done = pulser_task.is_task_done()
            current_status = 0 if task_done else 1
        except nidaqmx.errors.DaqError as e:
            print(f"Error while getting pulser state: {e}")
            current_status = -1

        return current_status, status_dict[current_status]

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware """
        return self._task.timing.samp_clk_rate

    def set_sample_rate(self, sample_rate):
        """Set the sample rate of the pulse generator hardware."""
        self._task.timing.cfg_samp_clk_timing(rate=sample_rate, source='OnboardClock',
                                              active_edge=nidaqmx.constants.Edge.RISING,
                                              sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
                                              samps_per_chan=1000)

        return self.get_sample_rate()


    def get_analog_level(self, amplitude=None, offset=None):
        """ Retrieve the analog amplitude and offset of the provided channels. """
        return dict(), dict()

    def set_analog_level(self, amplitude=None, offset=None):
        """ Set amplitude and/or offset value of the provided analog channel(s). """
        return dict(), dict()

    def get_digital_level(self, low=None, high=None):
        """ Retrieve the digital low and high level of the provided/all channels. """
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
        ni_ch = [channel.name for channel in self._task.do_channels]
        return {k:True for k in ni_ch}

    def set_active_channels(self, ch=None):
        """ Set the active/inactive channels for the pulse generator hardware. """
        return self.get_active_channels()

    def get_interleave(self):
        """ Check whether Interleave is ON or OFF in AWG."""
        return False  # always return False for pulse generator hardware without interleave.

    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off. """
        return False  # Unused for pulse generator hardware other than an AWG.

    def reset(self):
        """ Reset the device. """
        pass

    def write_sequence(self, name, sequence_parameters):
        """ Write a new sequence on the device memory. """
        self.log.warning('No card has no sequencing capabilities write_sequence call ignored.')
        return -1

    def get_waveform_names(self):
        """ Retrieve the names of all uploaded waveforms on the device. """

        return [self._current_waveform_name]

    def get_sequence_names(self):
        """ Retrieve the names of all uploaded sequence on the device. """
        return list()

    def delete_waveform(self, waveform_name):
        """Delete the waveform with name "waveform_name" from the device memory ."""
        return list()

    def delete_sequence(self, sequence_name):
        """ Delete the sequence with name "sequence_name" from the device memory. """
        return list()



    def write_waveform(self, name, analog_samples, digital_samples, is_first_chunk, is_last_chunk, total_number_of_samples):
        """ Write a new waveform or append samples to an already existing waveform on the device memory.   """


        self._current_waveform_name = name

        if is_first_chunk:
            self._current_waveform = []




            pb_waveform_temp = self._convert_sample_to_pb_sequence(digital_samples)

            # check if last of existing waveform is the same as the first one of
            # the coming one, then combine them,
            if self._current_pb_waveform_theoretical[-1]['active_channels'] == pb_waveform_temp[0]['active_channels']:
                self._current_pb_waveform_theoretical[-1]['length'] += pb_waveform_temp[0]['length']
                pb_waveform_temp.pop(0)

            self._current_pb_waveform_theoretical.extend(pb_waveform_temp)

        # convert at first the separate waveforms for each channel to a matrix

        if is_last_chunk:
            self._current_pb_waveform = self._correct_sequence_for_delays(self._current_pb_waveform_theoretical)
            self.write_pulse_form(self._current_pb_waveform)
            self.log.debug('Waveform written in PulseBlaster with name "{0}" '
                           'and a total length of {1} sequence '
                           'entries.'.format(self._current_pb_waveform_name,
                                              len(self._current_pb_waveform) ))

        return chunk_length, [self._current_pb_waveform_name]
