# -*- coding: utf-8 -*-
"""
This module controls the Coherent OBIS laser.

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
from collections import OrderedDict

from core.module import Base
from core.configoption import ConfigOption
from interface.motor_interface import MotorInterface

import visa

class Harmonixx(Base, MotorInterface):

    """ This hardware aim to control the harmonixx module from APE which enable SHG, THG and FHG from of fundamental
    laser beam.

    This interface is useful for a standard, fixed wavelength laser that you can find in a lab.
    It handles power control via constant power or constant current mode, a shutter state if the hardware has a shutter
    and a temperature regulation control.

    ape_harmonixx:
        module.Class: 'motor.ape_harmonixx.Harmonixx'
        port: 'COM5'

    """

    _port = ConfigOption('port', missing='error')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._rm = visa.ResourceManager()

        self._device = self._rm.open_resource(self._port)
        self._device.baud_rate = 38400
        self._device.timeout = 20000
        self._device.write_termination = ","
        self._device.read_termination = "\n"
        self._device.clear()

        self._cmd_from_axis = {
            "SHG": "SMS",
            "THG": "SMT",
            "DC": "SMD",
            "WP": "SMW",
            "WAVELENGTH": "NWL",
        }

        self._axis_index = {
            "SHG": 1,
            "THG": 2,
            "DC": 3,
            "WP": 4,
        }

        self._axis = ["SHG", "WP", "DC", "THG", "WAVELENGTH"]
        self._axis_pos = self.get_pos(["SHG", "WP", "DC", "THG", "WAVELENGTH"])

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._device.close()
        return 0

    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        @return dict: dict with constraints for the sequence generation and GUI

        Provides all the constraints for the xyz stage  and rot stage (like total
        movement, velocity, ...)
        Each constraint is a tuple of the form
            (min_value, max_value, stepsize)
        """
        constraints = OrderedDict()

        constraints["SHG"] = {
            'label': "SHG",
            'ID': None,
            'unit': "step",
            'ramp': None,
            'pos_min': 10,
            'pos_max': 3096,
            'pos_step': 1,
            'vel_min': None,
            'vel_max': None,
            'vel_step': None,

            'acc_min': None,
            'acc_max': None,
            'acc_step': None,
        }
        constraints["DC"] = {
            'label': "DC",
            'ID': None,
            'unit': "step",
            'ramp': None,
            'pos_min': 4,
            'pos_max': 138,
            'pos_step': 1,
            'vel_min': None,
            'vel_max': None,
            'vel_step': None,

            'acc_min': None,
            'acc_max': None,
            'acc_step': None,
        }
        constraints["WP"] = {
            'label': "WP",
            'ID': None,
            'unit': "step",
            'ramp': None,
            'pos_min': 204,
            'pos_max': 4190,
            'pos_step': 1,
            'vel_min': None,
            'vel_max': None,
            'vel_step': None,

            'acc_min': None,
            'acc_max': None,
            'acc_step': None,
        }
        constraints["THG"] = {
            'label': "THG",
            'ID': None,
            'unit': "step",
            'ramp': None,
            'pos_min': 32,
            'pos_max': 3106,
            'pos_step': 1,
            'vel_min': None,
            'vel_max': None,
            'vel_step': None,

            'acc_min': None,
            'acc_max': None,
            'acc_step': None,
        }
        constraints["WAVELENGTH"] = {
            'label': "SHG",
            'ID': None,
            'unit': "nm",
            'ramp': None,
            'pos_min': 700,
            'pos_max': 1000,
            'pos_step': 1,
            'vel_min': None,
            'vel_max': None,
            'vel_step': None,

            'acc_min': None,
            'acc_max': None,
            'acc_step': None,
        }

        return constraints

    def move_rel(self, param_dict):
        """Moves stage by a given angle (relative movement)

        @param dict param_dict: Dictionary with axis name and relative movement in units

        @return dict: Dictionary with axis name and final position in units
        """
        pos_dict = {}
        for label, rel_pos in param_dict.items():
            cmd = self._cmd_from_axis[label]
            if label == "WAVELENGTH":
                abs_pos = self._axis_pos["WAVELENGTH"] + rel_pos
                param = (4-len(str(int(abs_pos*1e9))))*'0'+"{}".format(int(abs_pos*1e9))
            else:
                sign = "+" if rel_pos>0 else "-"
                pos = abs(int(rel_pos))
                param = sign+(3-len(str(pos)))*'0'+"{}".format(pos)
            self._device.query("{}{}".format(cmd, param))
            pos = float(self._device.read_bytes(15)[-4:])*1e-9 if label == "WAVELENGTH" else float(self._device.read()[3:].split(" ")[self._axis_index[label]])
            pos_dict[label] = pos
            self._axis_pos[label] = pos
        return pos_dict

    def move_abs(self, param_dict):
        """Moves stage to an absolute angle (absolute movement)

        @param dict param_dict: Dictionary with axis name and target position in deg

        @return dict velocity: Dictionary with axis name and final position in deg
        """
        pos_dict = {}
        for label, abs_pos in param_dict.items():
            cmd = self._cmd_from_axis[label]
            if label == "WAVELENGTH":
                param = (4-len(str(int(abs_pos*1e9))))*'0'+"{}".format(int(abs_pos*1e9))
            else:
                rel_pos = abs_pos - self._axis_pos[label]
                sign = "+" if rel_pos>0 else "-"
                pos = abs(int(rel_pos))
                param = sign+(3-len(str(pos)))*'0'+"{}".format(pos)
            self._device.query("{}{}".format(cmd, param))
            pos = float(self._device.read_bytes(15)[-4:])*1e-9 if label == "WAVELENGTH" else float(self._device.read()[3:].split(" ")[self._axis_index[label]])
            pos_dict[label] = pos
            self._axis_pos[label] = pos
        return pos_dict

    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        self._device.query("BRK")
        return 0

    def get_pos(self, param_list=None):
        """ Gets current position of the rotation stage

        @param list param_list: List with axis name

        @return dict pos: Dictionary with axis name and pos in deg
        """
        if not param_list:
            param_list = [label for label in self._axis]
        pos_dict = {}
        for label in param_list:
            pos = float(self._device.query("GWL")[3:])*1e-9 if label == "WAVELENGTH" \
                else float(self._device.query("GPS")[3:].split(" ")[self._axis_index[label]])
            pos_dict[label] = pos
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
            param_list = [label for label in self._axis]
        status_dict = {}
        for label in param_list:
            status_dict[label] = True

        return status_dict

    def calibrate(self, param_list=None):
        """ Calibrates the rotation motor

        @param list param_list: Dictionary with axis name

        @return dict pos: Dictionary with axis name and pos in deg
        """
        if not param_list:
            param_list = [label for label in self._axis]
        pos_dict = {}
        for label in param_list:
            cmd = self._cmd_from_axis[label]
            if label == "WAVELENGTH":
                self._device.query("{}0800".format(cmd))
        else:
                self._device.query("{}+0".format(cmd))
        pos = float(self._device.read_bytes(15)[-4:])*1e-9 if label == "WAVELENGTH" else float(self._device.read()[3:].split(" ")[self._axis_index[label]])
        pos_dict[label] = pos
        self._axis_pos[label] = pos
        return pos_dict

    def get_velocity(self, param_list=None):
        """ Asks current value for velocity.

        @param list param_list: Dictionary with axis name

        @return dict velocity: Dictionary with axis name and velocity in deg/s
        """
        if not param_list:
            param_list = [label for label in self._axis]
        velocity_dict = {}
        for label in param_list:
            velocity_dict[label] = None

        return velocity_dict

    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: Dictionary with axis name and target velocity in deg/s

        @return dict velocity: Dictionary with axis name and target velocity in deg/s
        """
        velocity_dict = {}
        for label in param_dict.keys():
            velocity_dict[label] = None

        return velocity_dict

    def reset(self):
        """ Reset the controller.
            Afterwards, moving to the home position with calibrate() is necessary.
        """
        self.calibrate()
        return 0
