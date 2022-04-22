# -*- coding: utf-8 -*-

"""
This module controls Newport CONEX-controlled Agilis stages.

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

from collections import OrderedDict

import visa

from core.module import Base
from core.configoption import ConfigOption
from interface.motor_interface import MotorInterface


class MotorNewportConex(Base, MotorInterface):
    """
    Module for the CONEX controller for Agilis stages sold by Newport.

    The controller takes commands of the form xxAAnn over a serial connection,
    where xx is the controller address and nn can be a value to be set or a question mark
    to get the value or it can be missing.


    Example config for copy-paste:

    newport_conex:
        module.Class: 'motor.motor_newport_conex.MotorNewportConex'
        axis:
            x1:
                port: 'COM5'
                adress: '01'
                unit: 'm'
            x2:
                port: 'COM7'
                adress: '01'
                unit: 'm'
            y1:
                port: 'COM8'
                adress: '01'
                unit: 'm'
            y2:
                port: 'COM9'
                adress: '01'
                unit: 'm'

    """

    _axis = ConfigOption('axis', missing='error')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._rm = visa.ResourceManager()

        self._devices = {}
        for label, configs in self._axis.items():

            device = self._rm.open_resource(configs["port"])
            device.baud_rate = 921600
            device.read_termination = "\r\n"

            self._devices[label] = device

            self.write(label, 'OR')


        return 0

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        for i in range(len(self._com_ports)):
            self._devices[i].close()
        return 0

    def query(self, axis_label, command):
        """

        :param axis_label:
        :param command:
        :return:
        """
        device = self._devices[axis_label]
        adress = self._axis[axis_label]['adress']
        return device.query("{}{}?".format(adress, command)).split(command)[1]

    def write(self, axis_label, command):
        """

        :param axis_label:
        :param command:
        :return:
        """
        device = self._devices[axis_label]
        adress = self._axis[axis_label]['adress']
        device.write("{}{}?".format(adress, command))

    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        @return dict: dict with constraints for the sequence generation and GUI

        Provides all the constraints for the xyz stage  and rot stage (like total
        movement, velocity, ...)
        Each constraint is a tuple of the form
            (min_value, max_value, stepsize)
        """
        constraints = OrderedDict()

        for label, configs in self._axis.items():

            axis = {
                'label': label,
                'ID': configs["adress"],
                'unit': configs["unit"],
                'ramp': None,
                'pos_min': self.query(label, "SL"),
                'pos_max': self.query(label, "SR"),
                'pos_step': self.query(label, "SU"),
                'vel_min': self.query(label, "VA"),
                'vel_max': self.query(label, "VA"),
                'vel_step': None,

                'acc_min': self.query(label, "AC"),
                'acc_max': self.query(label, "AC"),
                'acc_step': None,
            }

            constraints[label] = axis

        return constraints

    def move_rel(self, param_dict):
        """Moves stage by a given angle (relative movement)

        @param dict param_dict: Dictionary with axis name and relative movement in units

        @return dict: Dictionary with axis name and final position in units
        """
        pos_dict = {}
        for label, pos in param_dict.items():
            command = "PR{}".format(param_dict[label])
            self.write(label, command)
            pos_dict[label] = float(self.query(label, "TH"))

        return pos_dict

    def move_abs(self, param_dict):
        """Moves stage to an absolute angle (absolute movement)

        @param dict param_dict: Dictionary with axis name and target position in deg

        @return dict velocity: Dictionary with axis name and final position in deg
        """
        pos_dict = {}
        for label, pos in param_dict.items():
            command = "PA{}".format(param_dict[label])
            self.write(label, command)
            pos_dict[label] = float(self.query(label, "TH"))

        return pos_dict

    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        for label in self._axis.keys():
            self.write(label, 'ST')
        return 0

    def get_pos(self, param_list=None):
        """ Gets current position of the rotation stage

        @param list param_list: List with axis name

        @return dict pos: Dictionary with axis name and pos in deg
        """
        if not param_list:
            param_list = [label for label in self._axis.keys()]
        pos_dict = {}
        for label in param_list:
            pos_dict[label] = float(self.query(label, "TP"))

        return pos_dict

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict status:
        """
        if not param_list:
            param_list = [label for label in self._axis.keys()]
        pos_dict = {}
        for label in param_list:
            pos_dict[label] = float(self.query(label, "TS"))

        return pos_dict

    def calibrate(self, param_list=None):
        """ Calibrates the rotation motor

        @param list param_list: Dictionary with axis name

        @return dict pos: Dictionary with axis name and pos in deg
        """
        if not param_list:
            param_list = [label for label in self._axis.keys()]
        pos_dict = {}
        for label in param_list:
            self.write(label, "OR")
            pos_dict[label] = float(self.query(label, "TH"))

        return pos_dict

    def get_velocity(self, param_list=None):
        """ Asks current value for velocity.

        @param list param_list: Dictionary with axis name

        @return dict velocity: Dictionary with axis name and velocity in deg/s
        """
        if not param_list:
            param_list = [label for label in self._axis.keys()]
        velocity_dict = {}
        for label in param_list:
            velocity_dict[label] = float(self.query(label, "VA"))

        return velocity_dict

    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: Dictionary with axis name and target velocity in deg/s

        @return dict velocity: Dictionary with axis name and target velocity in deg/s
        """
        velocity_dict = {}
        for label in param_dict.keys():
            velocity_dict[label] = float(self.query(label, "VA"))

        return velocity_dict

    def reset(self):
        """ Reset the controller.
            Afterwards, moving to the home position with calibrate() is necessary.
        """
        for label in self._axis.keys():
            self.write(label, 'RS')
        return 0
