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
    _fitlogic = Connector(interface='FitLogic')

    _axis_range = StatusVar("axis_range", None)
    _scan = StatusVar("scan", np.zeros(100, 100))
    _positions = StatusVar("positions", np.zeros(100, 100, 2))
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

    def alignment_optimization(self, alignement_name=None, algorithm="raster", **params):
        """

        :param algorithm:
        :param algorithm_params:
        :return:
        """

        if algorithm == "raster":
            self.raster_scan(**params)
        elif algorithm == "spiral":
            self.spiral_scan(**params)
        elif algorithm == "hill_climber":
            self.hill_climber(**params)

        if alignement_name:
            self._alignment = pd.concat([self._alignment, pd.DataFrame(self._last_alignment, index=[alignement_name], )])

    def raster_scan(self, x_axis=None, y_axis=None, fit_max=True):

        if not x_axis:
            x_axis = self._axis[0]
        if not y_axis:
            y_axis = self._axis[1]

        x_range = self._axis_range[x_axis]
        y_range = self._axis_range[y_axis]

        self._scan = np.zeros(len(x_range), len(y_range))
        self._positions = np.zeros(len(x_range), len(y_range), 2)

        for i in range(len(x_range)):
            for j in range(len(y_range)):

                self.motor.move_abs({x_axis: x_range[i], y_axis: y_range[i]})
                self._scan[i, j] = self.counter.get_process_value()

                pos = self.motor.get_pos([x_axis, y_axis])
                self._positions[i, j, 0] = pos[x_axis]
                self._positions[i, j, 1] = pos[y_axis]

        if fit_max:
            gaussian_fit = self._fit_logic.make_twoDgaussian_fit(
                xy_axes=self._positions,
                data=self._scan,
                estimator=self._fit_logic.estimate_twoDgaussian_MLE
            )
            if gaussian_fit.success is False:
                self.log.error('Error: 2D Gaussian Fit was not successfull!.')
            else:
                if x_range.min() < gaussian_fit.best_values['center_x'] < x_range.max():
                    self._last_alignment[x_axis] = gaussian_fit.best_values['center_x']
                if y_range.min() < gaussian_fit.best_values['center_y'] < y_range.max():
                    self._last_alignment[y_axis] = gaussian_fit.best_values['center_y']
        else:
            i_max, j_max = np.argmax(self._scan)
            self._last_alignment[x_axis] = self._positions[i_max]
            self._last_alignment[y_axis] = self._positions[j_max]

    def axis_by_axis(self, axis_list=None, fit_max=True):

        if not axis_list:
            axis_list = self._axis_list

        self._scan = np.zeros(len(self._axis_range[axis_list[0]]), len(axis_list))
        self._positions = np.zeros(len(self._axis_range[axis_list[0]]), len(axis_list))

        i = 0
        for axis in axis_list:
            for j in range(len(self._axis_range[axis])):
                ax_range = self._axis_range[axis]
                self.motor.move_abs({axis: ax_range[j]})
                self._scan[i, j] = self.counter.get_process_value()

                pos = self.motor.get_pos([axis])
                self._positions[i, j] = pos[axis]

            if fit_max:
                gaussian_fit = self._fit_logic.make_gaussian_fit(
                    x_axis=ax_range,
                    data=self._positions[i, :],
                    estimator=self._fit_logic.estimate_gaussian_peak
                )
                if gaussian_fit.success is False:
                    self.log.error('Error: 1D Gaussian Fit was not successfull!.')
                else:
                    if ax_range.min() < gaussian_fit.best_values['Position'] < ax_range.max():
                        self._last_alignment[axis] = gaussian_fit.best_values['Position']["value"]
            else:
                i_max = np.argmax(self._scan)
                self._last_alignment[axis] = self._positions[i_max]
            i += 1


