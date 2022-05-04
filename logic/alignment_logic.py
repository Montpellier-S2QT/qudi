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
from logic.generic_logic import GenericLogic
from core.statusvariable import StatusVar
from core.util.mutex import RecursiveMutex

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
    _optimization_method = StatusVar("optimization_method", 'raster')
    _alignment = StatusVar("alignment", None)
    _last_alignment = StatusVar("last_alignment", {})
    _scan = StatusVar("scan", None)
    _scan_pos = StatusVar("scan_pos", None)

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

        self._axis_list = [axis for axis in self._constraints.keys()]

        if not self._optimized_axis:
            self._optimized_axis = self._axis_list
        
        if not self._alignment:
            self._alignment = []

        if not self._axis_range:
            self._axis_range = {}
            for axis, constraint in self._constraints.items():
                self._axis_range[axis] = np.arange(constraint["pos_min"], constraint["pos_max"], constraint["pos_step"])

        self._loop_timer = QtCore.QTimer()
        self._loop_timer.setSingleShot(True)

    def on_deactivate(self):
        self._scanner_signal.disconnect()
        return 0

    def set_axis_range(self, axis, ax_min, ax_max, ax_step):

        ax_min = float(ax_min)
        ax_max = float(ax_max)
        ax_step = float(ax_step)

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

    def set_optimized_axis(self, axis_list):

        if any(axis in self._axis_list for axis in axis_list):
            self._optimized_axis = axis_list

    def start_optimization(self, alignement_name=None):
        """

        :param algorithm:
        :param algorithm_params:
        :return:
        """

        self.point_index = 0
        if self._optimization_method == "raster":
            self._scanner_signal.connect(self.raster_scan, QtCore.Qt.QueuedConnection)
            self.raster_scan()
    def stop_optimization(self):
        """

        :param algorithm:
        :param algorithm_params:
        :return:
        """
        self._scanner_signal.disconnect()

    def scan_point(self, point_index):
        """

        :param point_index:
        :return:
        """
        if self.point_index >= self._points.shape[0]:
            self.log.info("Point index is larger than the positions length.")
            return
        param_dict = {}
        for j, axis in enumerate(self._optimized_axis):
            param_dict[axis] = self._points[point_index, j]
        self.motor().move_abs(param_dict)
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

            self.scan_point(self.point_index)
            self.point_index += 1

            if self.point_index >= self._points.shape[0]:

                self._scan_pos = np.array(self._scan_pos)
                self._scan = np.nan_to_num(np.array(self._scan))

                max_pos = self._scan_pos[np.argmax(self._scan)]

                params = lmfit.Parameters()
                params.add("A", min=self._scan.min(), max=10*self._scan.max(), value=self._scan.max())
                params.add("B", min=self._scan.min(), max=self._scan.max(), value=self._scan.min())
                for j, axis in enumerate(self._optimized_axis):
                    params.add("x{}".format(j), min=self._scan_pos[:,j].min(), max=self._scan_pos[:,j].max(), value=max_pos[j])
                    params.add("w{}".format(j), min=(self._scan_pos[1::2,j]-self._scan_pos[::2,j]).min(),
                               max=self._scan_pos[0,j]-self._scan_pos[-1,j], value=(self._scan_pos[0,j]-self._scan_pos[-1,j])/10)

                fit_result = lmfit.minimize(self.gaussian_multi, params, kws={"axis": self._optimized_axis})
                print(fit_result.params)
                return fit_result.params

        self._scanner_signal.emit()

    def gaussian_multi(self, params, axis):

        res = params["A"]
        for i, ax in enumerate(axis):
            res *= np.exp(-(self._scan_pos[:,i] - float(params["x{}".format(i)])) ** 2 / (2 * params["w{}".format(i)] ** 2))
        res += params["B"]
        res -= self._scan
        return res


