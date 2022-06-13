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
from enum import Enum
import copy

from core.connector import Connector
from logic.generic_logic import GenericLogic
from core.statusvariable import StatusVar
from core.util.mutex import RecursiveMutex

class OptimizationMethod(Enum):
    """ Class defining the possible optimization method implemented in the alignment logic.
    Please add items to tjis class after you have implemented the corresponding optimization method in the logic.
     """
    raster = 1
    gradient = 2


class AlignmentLogic(GenericLogic):
    """ Logic module to control a laser.

    alignement_logic:
        module.Class: 'alignement_logic.AlignementLogic'
        connect:
            counter: 'mycounter'
            motor: 'mymotor'
    """

    counter = Connector(interface='ProcessInterface')
    motor = Connector(interface='MotorInterface')

    _axis_range = StatusVar("axis_range", None)
    _optimized_axis = StatusVar("optimized_axis", None)
    _scan_delay = StatusVar("scan_delay", 0)
    _optimization_method = StatusVar("optimization_method", 'raster')
    _alignments = StatusVar("alignments", None)
    _motor_positions = StatusVar("motor_positions", None)
    _scan = StatusVar("scan", None)
    _scan_pos = StatusVar("scan_pos", None)
    _axis_list = StatusVar("axis_list", None)

    _scanner_signal = QtCore.Signal()

    def __init__(self, config, **kwargs):
        """ Create SpectrumLogic object with connectors and status variables loaded.

          @param dict kwargs: optional parameters
        """
        super().__init__(config=config, **kwargs)
        self._thread_lock = RecursiveMutex()

    def on_activate(self):
        """ Activate module.
        """

        self._constraints = self.motor().get_constraints()

        if not self._axis_list:
            self._axis_list = [axis for axis in self._constraints.keys()]

        if not self._optimized_axis:
            self._optimized_axis = self._axis_list

        if not self._alignments:
            self._alignments = {}

        if not self._motor_positions:
            self._motor_positions = self.motor().get_pos(self._axis_list)

        if not self._axis_range:
            self._axis_range = {}
            for axis, constraint in self._constraints.items():
                self._axis_range[axis] = np.arange(constraint["pos_min"], constraint["pos_max"], constraint["pos_step"])

        self._loop_timer = QtCore.QTimer()
        self._loop_timer.setSingleShot(True)

    def on_deactivate(self):
        if self.module_state != "idle":
            self.stop_optimization()
        return 0

    @property
    def axis_range(self):
        return self._axis_range

    @axis_range.setter
    def axis_range(self, axis_dict):

        for axis, axis_range in axis_dict.items():
            ax_min = float(axis_range[0])
            ax_max = float(axis_range[1])
            ax_step = float(axis_range[2])

            if ax_min < self._constraints[axis]["pos_min"] or ax_min > self._constraints[axis]["pos_max"] or not ax_min:
                self.log.warning("Axis range minimum parameter is outside the hardware available range : "
                                 "the minimum is set to the hardware minimum.")
                ax_min = self._constraints[axis]["pos_min"]

            if ax_max > self._constraints[axis]["pos_max"] or ax_max < self._constraints[axis]["pos_min"] or not ax_max:
                self.log.warning("Axis range maximum parameter is outside the hardware available range : "
                                 "the maximum is set to the hardware maximum.")
                ax_max = self._constraints[axis]["pos_max"]

            if ax_step < self._constraints[axis]["pos_step"] \
                    or ax_step > ax_max-ax_min or not ax_step:
                self.log.warning("Axis range step parameter is smaller than the hardware minimum step or larger "
                                 "than the set range : the minimum is set to the hardware minimum step.")
                ax_step = self._constraints[axis]["pos_step"]

            self._axis_range[axis] = np.arange(ax_min, ax_max, ax_step)

    @property
    def optimized_axis(self):
        return self._optimized_axis

    @optimized_axis.setter
    def optimized_axis(self, axis_list):
        if any(axis in self._axis_list for axis in axis_list):
            self._optimized_axis = axis_list

    @property
    def axis_list(self):
        return self._axis_list

    @axis_list.setter
    def axis_list(self, axis_list):
        if any(axis in self._constraints.keys() for axis in axis_list):
            self._axis_list = axis_list

    @property
    def scan_delay(self):
        return self._scan_delay

    @scan_delay.setter
    def scan_delay(self, delay):
        delay = float(delay)
        if delay < 0:
            self.log.warning("Delay parameter should be positive.")
        self._scan_delay = delay

    @property
    def optimization_method(self):
        return self._optimization_method

    @optimization_method.setter
    def optimization_method(self, method):
        if isinstance(method, str) and method in OptimizationMethod.__members__:
            method = OptimizationMethod[method]
        if not isinstance(method, OptimizationMethod):
            self.log.error("Method parameter do not match with optimization methods available.")
            return
        self._optimization_method = method

    @property
    def motor_positions(self):
        return self._motor_positions

    @motor_positions.setter
    def motor_positions(self, position_dict):
        self.motor().move_abs(position_dict)
        self._motor_positions = self.motor().get_pos(self._axis_list)

    @property
    def alignments(self):
        return self._alignments

    def add_alignment(self, name):
        self._alignments[name] = copy.copy(self._motor_positions)

    def retrieve_alignment(self, name):

        if name not in self._alignments.keys():
            self.log.error("The input name of the alignment doesn't exists.")
            return
        self._motor_positions = self.motor().move_abs(self._alignments[name])

    def save_alignments(self, path):

        df = pd.DataFrame(self._alignments)
        df.to_csv(path)
        self.log.info("The alignments have been saved to {}.".format(path))

    def upload_alignments(self, path):

        df = pd.read_csv(path)
        df_dict = df.to_dict()
        pos_dict = {}
        for name in df_dict.keys():
            if name != 'Unnamed: 0':
                d = {}
                for key, axis in df_dict['Unnamed: 0'].items():
                    d[axis] = df_dict[name][key]
                pos_dict[name] = d
        self._alignments = pos_dict
        self.log.info("The alignments have been uploaded from {}.".format(path))

    def start_optimization(self):
        """

        :param algorithm:
        :param algorithm_params:
        :return:
        """

        self.point_index = 0
        if self._optimization_method == "raster":
            self._scanner_signal.connect(self.raster_scan, QtCore.Qt.QueuedConnection)
            self.raster_scan()
        elif self._optimization_method == "gradient":
            self._scanner_signal.connect(self.gradient_descent, QtCore.Qt.QueuedConnection)
            self.gradient_descent()

    def stop_optimization(self):
        """

        :param algorithm:
        :param algorithm_params:
        :return:
        """
        if self.point_index < self._points.shape[0]:
            self._scanner_signal.disconnect()
            self.motor().move_abs(self._motor_positions)

    def scan_point(self, point_index):
        """

        :param point_index:
        :return:
        """
        param_dict = {}
        for j, axis in enumerate(self._optimized_axis):
            param_dict[axis] = self._points[point_index, j]
        self.motor().move_abs(param_dict)
        time.sleep(self._scan_delay)
        self._scan.append(self.counter().get_process_value())
        self._scan_pos.append([pos for pos in self.motor().get_pos(self._optimized_axis).values()])

    def raster_scan(self):

        if not np.all([status for status in self.motor().get_status(self._optimized_axis).values()]):

            self.log.debug("The motors axis are still busy !")

        else:

            if self.point_index == 0:

                self._points = np.array(np.meshgrid(*[self._axis_range[axis].T for axis in self._optimized_axis])).T.reshape(-1, len(self._optimized_axis))
                self._scan_pos = []
                self._scan = []

            if self.point_index < self._points.shape[0]:
                self.scan_point(self.point_index)
                self.point_index += 1

            else:
                self._scanner_signal.disconnect()
                self._scan_pos = np.array(self._scan_pos)
                self._scan = np.nan_to_num(np.array(self._scan))

                max_pos = self._scan_pos[np.argmax(self._scan)]

                params = lmfit.Parameters()
                params.add("A", min=self._scan.min(), value=self._scan.max())
                params.add("B", min=self._scan.min(), value=self._scan.min())
                for j, axis in enumerate(self._optimized_axis):
                    params.add("x{}".format(j), min=self._scan_pos[:, j].min(), max=self._scan_pos[:, j].max(), value=max_pos[j])
                    params.add("w{}".format(j), min=(self._scan_pos[1::2, j]-self._scan_pos[::2, j]).min(),
                               max=self._scan_pos[0,j]-self._scan_pos[-1, j], value=(self._scan_pos[0, j]-self._scan_pos[-1, j])/10)

                fit_result = lmfit.minimize(self.gaussian_multi, params, kws={"axis": self._optimized_axis})
                position_dict = {}
                for j, axis in enumerate(self._optimized_axis):
                    position_dict[axis] = fit_result.params["x{}".format(j)]
                self.motor().move_abs(position_dict)
                self.motor_positions = self.motor().get_pos(self._axis_list)
                return

        self._scanner_signal.emit()

    def gaussian_multi(self, params, axis):

        res = params["A"]
        for i, ax in enumerate(axis):
            res *= np.exp(-(self._scan_pos[:, i] - float(params["x{}".format(i)])) ** 2 / (2 * params["w{}".format(i)] ** 2))
        res += params["B"]
        res -= self._scan
        return res

    def gradient_descent(self):

        if not np.all([status for status in self.motor().get_status(self._optimized_axis).values()]):

            self.log.debug("The motors axis are still busy !")

        else:

            if self.point_index == 0:

                self._points = [self._motor_positions[i] for i, axis in enumerate(self._optimized_axis)]
                self._points.append([self._motor_positions[i]+self._axis_range[axis][1]-self._axis_range[axis][0] for i, axis in enumerate(self._optimized_axis)])
                self._scan_pos = []
                self._scan = []

            self.scan_point(self.point_index)
            slopes = (self._scan[self.point_index]-self._scan[self.point_index-1])/ \
                     (self._scan_pos[self.point_index]-self._scan_pos[self.point_index-1])

            if np.all(slopes > 1e-3):
                new_points = [self._scan_pos[self.point_index][i] + slopes[i] for i, axis in enumerate(self._optimized_axis)]
                self._points.append(new_points)
                self.point_index += 1

            else:
                self._scanner_signal.disconnect()
                return

        self._scanner_signal.emit()





