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

import sys
import clr
import os
from collections import OrderedDict

from core.module import Base
from core.configoption import ConfigOption
from interface.motor_interface import MotorInterface


class MotorNewportConex(Base, MotorInterface):
    """
    Module for the CONEX-CC controller by Newport.


    Example config for copy-paste:

    newport_conex:
        module.Class: 'motor.motor_newport_conex_agp.MotorNewportConex'
        dll_path: 'Newport.CONEXCC.CommandInterface.dll'
        com_port: 'COM1'
        controller_address: 1
        axis_label: 'phi'

    """

    _com_port = ConfigOption('com_port', missing='error')
    _dll_ath = ConfigOption('dll_ath', missing='error')
    _controller_address = ConfigOption('controller_address', 1, missing='warn')

    _axis_label = ConfigOption('axis_label', 'phi', missing='warn')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        sys.path.append(self._dll_path)
        clr.AddReference(self._dll_path)
        import System

        self._serial_connection = serial.Serial(
            port=self._com_port,
            baudrate=921600,
            bytesize=8,
            parity='N',
            stopbits=1,
            xonxoff=True)

        model, pn, ud = self.query('ID').split('_')
        controller, fw_ver = self.query('VE').split()
        self.log.info('Stage {0} {1} {2} on controller {3} firmware {4}'
                      ''.format(model, pn, ud, controller, fw_ver))
        self._min_pos = float(self.query('SL'))
        self._max_pos = float(self.query('SR'))
        self._velocity = self.vel_from_model[model]
        self._axis_unit = self.unit_from_model[model]
        self._min_step = float(self.query('DB'))
        self.log.info('Limits: {0}{2} to {1}{2}'
                      ''.format(self._min_pos, self._max_pos, self._axis_unit))

        return 0

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._serial_connection.close()
        return 0



    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        @return dict: dict with constraints for the magnet hardware. These
                      constraints will be passed via the logic to the GUI so
                      that proper display elements with boundary conditions
                      could be made.
        """
        constraints = OrderedDict()

        axis = {
            'label': self._axis_label,
            'ID': None,
            'unit': self._axis_unit,
            'ramp': None,
            'pos_min': self._min_pos,
            'pos_max': self._max_pos,
            'pos_step': self._min_step,
            'vel_min': self._velocity,
            'vel_max': self._velocity,
            'vel_step': self._velocity,
            'acc_min': None,
            'acc_max': None,
            'acc_step': None,
        }

        # assign the parameter container to a name which will identify it
        constraints[axis['label']] = axis
        return constraints

    def move_rel(self,  param_dict):
        """ Moves stage in given direction (relative movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        A smart idea would be to ask the position after the movement.

        @return int: error code (0:OK, -1:error)
        """
        pass

    def move_abs(self, param_dict):
        """ Moves stage to absolute position (absolute movement)

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return int: error code (0:OK, -1:error)
        """
        pass

    def abort(self):
        """ Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        pass

    def get_pos(self, param_list=None):
        """ Gets current position of the stage arms

        @param list param_list: optional, if a specific position of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                position is asked.

        @return dict: with keys being the axis labels and item the current
                      position.
        """
        pass

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict: with the axis label as key and the status number as item.
        """
        pass

    def calibrate(self, param_list=None):
        """ Calibrates the stage.

        @param dict param_list: param_list: optional, if a specific calibration
                                of an axis is desired, then the labels of the
                                needed axis should be passed in the param_list.
                                If nothing is passed, then all connected axis
                                will be calibrated.

        @return int: error code (0:OK, -1:error)

        After calibration the stage moves to home position which will be the
        zero point for the passed axis. The calibration procedure will be
        different for each stage.
        """
        pass

    def get_velocity(self, param_list=None):
        """ Gets the current velocity for all connected axes.

        @param dict param_list: optional, if a specific velocity of an axis
                                is desired, then the labels of the needed
                                axis should be passed as the param_list.
                                If nothing is passed, then from each axis the
                                velocity is asked.

        @return dict : with the axis label as key and the velocity as item.
        """
        pass

    def set_velocity(self, param_dict):
        """ Write new value for velocity.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return int: error code (0:OK, -1:error)
        """
        pass
