# -*- coding: utf-8 -*-

"""
This hardware module interact with a Keysight EXA spectrum analyser.
It does not implement any interface yet, but it can be used via console or notebooks.

This module have been developed with model N9010B.
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

import visa
from core.module import Base
from core.configoption import ConfigOption
import numpy as np


class SpectrumAnalyser(Base):
    """ Main class for the hardware

    Example config:

    spectrum_analyser:
        module.Class: 'spectrum_analyser.Keysight_EXA.SpectrumAnalyser'
        ip_address: '192.168.0.103'
    """

    _ip_address = ConfigOption('ip_address')
    _timeout = ConfigOption('timeout', 10)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._inst = None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.open_resource()

    def open_resource(self):
        """ Open a new visa connection """
        rm = visa.ResourceManager()
        try:
            address = 'TCPIP::{}::inst0::INSTR'.format(self._ip_address)
            self._inst = rm.open_resource(address, timeout=self._timeout)
            IDN = self._inst.query("*IDN?")
            self.log.info('Connected to {}.'.format(IDN))
        except visa.VisaIOError:
            self.log.error('Could not connect to hardware. Please check the wires and the address.')
            raise visa.VisaIOError

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module. """
        try:
            self._inst.close()
        except visa.VisaIOError:
            self.log.warning('Connexion has not been closed properly.')

    def _query(self, text):
        """ Helper function to send query and deal with errors """
        try:
            response = self._inst.query(text)
        except visa.VisaIOError:
            if self.module_state() != 'idle':
                return None
            self.log.warning('Connexion lost, automatic attempt to reconnect...')
            self.open_resource()
            self._inst.query(text)
        return response

    def get_frequency_range(self):
        start = float(self._query('SENS1:FREQ:STAR?'))
        stop = float(self._query('SENS1:FREQ:STOP?'))
        return start, stop

    def set_frequency_range(self, start=None, stop=None):
        if start is not None:
            self._inst.write('SENS1:FREQ:STAR {}'.format(start))
        if stop is not None:
            self._inst.write('SENS1:FREQ:STOP {}'.format(stop))

    def get_bandwidth(self):
        return float(self._query('SENS1:BAND:Res?'))

    def set_bandwidth(self, value):
        self._inst.write('SENS1:BAND:Res {}'.format(value))

    def get_number_of_points(self):
        return float(self._query('SENS1:SWEep:POINts?'))

    def set_number_of_points(self, value):
        self._inst.write('SENS1:SWEep:POINts {}'.format(value))

    def get_data(self, channel=1):
        start, stop = self.get_frequency_range()
        self._inst.write(':FORM:DATA ASCII')
        trace_data = self._query(':TRACe:DATA? TRACE{}'.format(int(channel)))
        trace_values = np.array(list(map(float, trace_data.strip().split(','))))
        x_axis = np.linspace(start, stop, len(trace_values))
        return x_axis, trace_values

    def restart(self):
        self._inst.write(':INITiate:RESTart')

