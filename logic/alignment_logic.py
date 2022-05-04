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

import lmfit
import numpy as np
import pandas as pd
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

    _counter = Connector(interface='ProcessInterface')
    _motor = Connector(interface='MotorInterface')

    _axis_range = StatusVar("axis_range", None)
    _scan = StatusVar("scan", np.zeros(100, 100))
    _alignment = StatusVar("alignment", None)
    _last_alignment = StatusVar("last_alignment", None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_activate(self):
        """ Activate module.
        """

        self.counter = self._counter()
        self.motor = self._motor()
        self._fit_logic = self._fitlogic()

        self._constraints = self.motor.get_constraints()

        self._axis_list = [axis for axis in self._constraints.keys()]
        
        if not self._alignment:
            self._alignment = pd.DataFrame(columns=self._axis_list)

        if not self._last_alignment:
            self._last_alignment = {}

        if not self._axis_range:
            for axis, constraint in self._constraints.items():
                self._axis_range[axis] = np.arange(constraint["pos_min"], constraint["pos_max"], constraint["pos_step"])

    def set_axis_range(self, axis, ax_min, ax_max, ax_step):

        ax_min = float(ax_min)
        ax_max = float(ax_max)
        ax_step = float(ax_step)

        if ax_min < self._constraints[axis]["pos_min"] or ax_min > self._constraints[axis]["pos_max"] or not ax_min:
            self.log.warning("Axis range minimum parameter is outside the hardware available range : "
                             "the minimum is set to the hardware minimum.")
            ax_min = self._constraints[axis]["pos_min"]

        if ax_max < self._constraints[axis]["pos_max"] or ax_max < self._constraints[axis]["pos_min"] or not ax_max:
            self.log.warning("Axis range maximum parameter is outside the hardware available range : "
                             "the maximum is set to the hardware maximum.")
            ax_max = self._constraints[axis]["pos_max"]

        if ax_step < self._constraints[axis]["pos_step"] \
                or ax_step > ax_max-ax_min or not ax_step:
            self.log.warning("Axis range step parameter is smaller than the hardware minimum step or larger "
                             "than the set range : the minimum is set to the hardware minimum step.")
            ax_step = self._constraints[axis]["pos_step"]

        self._axis_range[axis] = np.arange(ax_min, ax_max, ax_step)

    def alignment_optimization(self, alignement_name=None, algorithm="raster", axis_list=None):
        """

        :param algorithm:
        :param algorithm_params:
        :return:
        """

        if not axis_list:
            axis_list = self._axis_list

        if algorithm == "raster":
            self.raster_scan(axis_list)
        elif algorithm == "spiral":
            self.spiral_scan(axis_list)
        elif algorithm == "hill_climber":
            self.hill_climber(axis_list)

        if alignement_name:
            self._alignment = pd.concat([self._alignment, pd.DataFrame(self._last_alignment, index=[alignement_name], )])

    def raster_scan(self, axis_list):

        pos_space = np.array(np.meshgrid(*[self._axis_range[axis].T for axis in axis_list])).T.reshape(-1, len(axis_list))
        scan = np.zeros(pos_space.shape)
        self._scan_pos = []

        for i, pos in enumerate(pos_space):
            for j, axis in enumerate(axis_list):
                self.motor().move_abs({axis: pos[j]})
                scan[i, j] = self.counter().get_process_value()
            self._scan_pos.append(self.motor().get_pos(axis_list).values())
        self._scan_pos = np.array(self._scan_pos)

        params = lmfit.Parameters()
        params.add("A", min=scan.min(), max=10*scan.max(), value=scan.max())
        params.add("B", min=scan.min(), max=scan.max(), value=scan.min())
        for j, axis in enumerate(axis_list):
            params.add("x{}".format(j), min=pos_space[:,j].min(), max=pos_space[:,j].max(), value=pos_space[:,j].mean())
            params.add("w{}".format(j), min=(pos_space[2::2,j]-pos_space[::2,j]).min(),
                       max=pos_space[0,j]-pos_space[-1,j], value=(pos_space[0,j]-pos_space[-1,j])/10)

        fit_result = lmfit.minimize(self.gaussian_multi, params, args={"axis": axis_list})
        return fit_result.params

    def gaussian_multi(self, params, axis):

        res = params["A"]
        for i, ax in enumerate(axis):
            res *= np.exp(-(self._scan_pos[i] - params["x{}".format(i)]) ** 2 / (2 * params["w{}".format(i)] ** 2))
        res += params["B"]
        res -= self._scan
        return res


