# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interfuse between a laser interface and analog output of a confocal_scanner_interface
 to control an analog driven AOM (Acousto-optic modulator).

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
import numpy as np
from scipy.interpolate import interp1d

from core.connector import Connector
from core.configoption import ConfigOption
from logic.generic_logic import GenericLogic
from interface.motor_interface import MotorInterface


class FuseMotors(GenericLogic, MotorInterface):
    """ This interfuse can be used to fuse two motors, with their axis, in one.
    """

    # connector to the motors to fuse
    motor_1 = Connector(interface='MotorInterface')
    motor_2 = Connector(interface='MotorInterface')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._constraints_1 = self.motor_1().get_constraints()
        self._axis_1 = [axis for axis in self._constraints_1]

        self._constraints_2 = self.motor_2().get_constraints()
        self._axis_2 = [axis for axis in self._constraints_2]

        self._constraints = self._constraints_1.update(self._constraints_2)
        self._axis = [axis for axis in self._constraints]

        return 0

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        return 0

    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        @return dict: dict with constraints for the sequence generation and GUI

        Provides all the constraints for the xyz stage  and rot stage (like total
        movement, velocity, ...)
        Each constraint is a tuple of the form
            (min_value, max_value, stepsize)
        """
        return self._constraints

    def move_rel(self, param_dict):
        """Moves stage by a given angle (relative movement)

        @param dict param_dict: Dictionary with axis name and relative movement in units

        @return dict: Dictionary with axis name and final position in units
        """

        param_1 = dict([(key, value) for key, value in param_dict.items() if key in self._axis_1])
        pos_1 = self.motor_1().move_rel(param_1)

        param_2 = dict([(key, value) for key, value in param_dict.items() if key in self._axis_2])
        pos_2 = self.motor_2().move_rel(param_2)

        return pos_1.update(pos_2)

    def move_abs(self, param_dict):
        """Moves stage to an absolute angle (absolute movement)

        @param dict param_dict: Dictionary with axis name and target position in deg

        @return dict velocity: Dictionary with axis name and final position in deg
        """
        param_1 = dict([(key, value) for key, value in param_dict.items() if key in self._axis_1])
        pos_1 = self.motor_1().move_abs(param_1)

        param_2 = dict([(key, value) for key, value in param_dict.items() if key in self._axis_2])
        pos_2 = self.motor_2().move_abs(param_2)

        return pos_1.update(pos_2)

    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        self.motor_1().abort()
        self.motor_2().abort()
        return 0

    def get_pos(self, param_list=None):
        """ Gets current position of the rotation stage

        @param list param_list: List with axis name

        @return dict pos: Dictionary with axis name and pos in deg
        """
        param_1 = [key for key in param_list if key in self._axis_1]
        pos_1 = self.motor_1().get_pos(param_1)

        param_2 = [key for key in param_list if key in self._axis_2]
        pos_2 = self.motor_2().get_pos(param_2)

        return pos_1.update(pos_2)

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict status:
        """
        param_1 = [key for key in param_list if key in self._axis_1]
        status_1 = self.motor_1().get_status(param_1)

        param_2 = [key for key in param_list if key in self._axis_2]
        status_2 = self.motor_2().get_status(param_2)

        return status_1.update(status_2)

    def calibrate(self, param_list=None):
        """ Calibrates the rotation motor

        @param list param_list: Dictionary with axis name

        @return dict pos: Dictionary with axis name and pos in deg
        """
        param_1 = [key for key in param_list if key in self._axis_1]
        pos_1 = self.motor_1().calibrate(param_1)

        param_2 = [key for key in param_list if key in self._axis_2]
        pos_2 = self.motor_2().calibrate(param_2)

        return pos_1.update(pos_2)

    def get_velocity(self, param_list=None):
        """ Asks current value for velocity.

        @param list param_list: Dictionary with axis name

        @return dict velocity: Dictionary with axis name and velocity in deg/s
        """
        param_1 = [key for key in param_list if key in self._axis_1]
        velocity_1 = self.motor_1().get_velocity(param_1)

        param_2 = [key for key in param_list if key in self._axis_2]
        velocity_2 = self.motor_2().get_velocity(param_2)

        return velocity_1.update(velocity_2)

    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: Dictionary with axis name and target velocity in deg/s

        @return dict velocity: Dictionary with axis name and target velocity in deg/s
        """
        param_1 = dict([(key, value) for key, value in param_dict.items() if key in self._axis_1])
        velocity_1 = self.motor_1().set_velocity(param_1)

        param_2 = dict([(key, value) for key, value in param_dict.items() if key in self._axis_2])
        velocity_2 = self.motor_2().set_velocity(param_2)

        return velocity_1.update(velocity_2)

    def reset(self):
        """ Reset the controller.
            Afterwards, moving to the home position with calibrate() is necessary.
        """
        self.motor_1().reset()
        self.motor_2().reset()
        return 0

