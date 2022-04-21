#-*- coding: utf-8 -*-
"""
Laser management.

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
import time
import numpy as np
from qtpy import QtCore

from core.connector import Connector
from core.configoption import ConfigOption
from logic.generic_logic import GenericLogic
from core.statusvariable import StatusVar
from interface.motor_interface import MotorInterface
from interface.slow_counter_interface import SlowCounterInterface, SlowCounterConstraints, CountingMode


class AlignementLogic(GenericLogic):
    """ Logic module to control a laser.

    alignement_logic:
        module.Class: 'alignement_logic.AlignementLogic'
        connect:
            counter: 'mycounter'
            motor: 'mymotor'
    """

    _counter = Connector(interface='SlowCounterInterface')
    _motor = Connector(interface='MotorInterface')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_activate(self):
        """ Activate module.
        """

        self.counter = self._counter()
        self.motor = self._motor()

    def alignement

    def start_raster_scan(self, axis):

        x = np.linspace(self._parameters["x_min"], self._parameters["x_min"])


    def spiral_scan(self):

        self.counter.

