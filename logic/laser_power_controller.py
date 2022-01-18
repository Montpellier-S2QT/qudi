# -*- coding: utf-8 -*-
"""
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

from qtpy import QtCore

from logic.generic_logic import GenericLogic
from core.connector import Connector
from core.statusvariable import StatusVar
from core.configoption import ConfigOption
from core.util.network import netobtain


class LaserPowerController(GenericLogic):
    """ This is the logic for controlling the power of one laser device

    This logic handle control the laser via a general ProcessControlInterface.
    The hardware can be a voltage output fed to an AOM or an interfuse to a motor

    An optical switch interface can be used in addition to the analog control to reach zero.
    This can be useful when the device controlling the power do not have perfect extinction

    To calibrate the power routinely, a power meter can be connected via procces_interface.
    Another option is to use a notebook to perform this "by hand"

    ---

    This module control one output. The GUI can be connected to one or multiple logic module.

    Example configuration :

    green_power_controller:
        module.Class: 'laser_power_controller.LaserPowerController'
        connect:
            process_control: 'process_control'
            power_switch: 'power_switch'
            power_meter: 'power_meter'
        name: 'Green'
        color: '#00FF00'
    """

    process_control = Connector(interface='ProcessControlInterface')
    power_switch = Connector(interface='SwitchInterface', optional=True)
    power_meter = Connector(interface='ProcessInterface', optional=True)

    name = ConfigOption('name', 'Laser')
    color = ConfigOption('color', 'lightgreen')

    config_control_limits = ConfigOption('control_limits', [None, None])  # In case hardware does not fix this
    power_switch_index = ConfigOption('power_switch_index', 0)  # If hardware has multiple switches
    process_control_index = ConfigOption('process_control_index', 0)  # If hardware has multiple process

    use_minimum_as_zero = ConfigOption('use_minimum_as_zero', True)
    # At zero laser power, the power meter can read a non zero value. This config set the minimum calibration point to
    # zero by hand.

    sigNewSwitchState = QtCore.Signal()
    sigNewPower = QtCore.Signal()
    sigNewPowerRange = QtCore.Signal()

    sigModuleStateChanged = QtCore.Signal()
    sigDoNextPoint = QtCore.Signal()
    sigCalibrationFinished = QtCore.Signal()

    # Status variable containing calibration parameters
    resolution = StatusVar('resolution', 50)
    delay = StatusVar('delay', 0)

    calibration_x = StatusVar('calibration_x', [])
    calibration_y = StatusVar('calibration_y', [])

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.timer = None
        self._interpolated = None
        self._interpolated_inverse = None
        self._channel_dict = {}

    def on_activate(self):
        """ Initialisation performed during activation of the module. """

        if self.process_control().process_control_supports_multiple_channels():
            self._channel_dict = {'channel': self.process_control_index}

        self._check_calibration()
        self._compute_interpolated()

        self.sigDoNextPoint.connect(self._next_point_apply_control)
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._next_point_measure_power)

    def on_deactivate(self):
        self._check_calibration()

    def _check_calibration(self):
        """ Check calibration data for error and empty it if necessary """
        if len(self.calibration_x) != len(self.calibration_y) or np.isnan(self.calibration_y).any():
            self.calibration_x = []
            self.calibration_y = []

    def _get_control(self):
        """ Get the value of the control parameter """
        value = self.process_control().get_control_value(**self._channel_dict)
        return float(netobtain(value))

    def _set_control(self, value):
        """ Set the value of the control parameter """
        limit_low, limit_high = self._get_control_limits()
        value = float(value)
        if not (limit_low <= value <= limit_high):
            self.log.error('Value {} is out of bound : [{}, {}]'.format(value, limit_low, limit_high))
            return

        if self.process_control.is_connected:
            return self.process_control().set_control_value(value, **self._channel_dict)
        else:
            self.log.error('No connected controller anymore. Can not set control value.')

    def _get_control_limits(self):
        """ Get the control limit, either imposed by hardware or by config """
        limits = self.process_control().get_control_limit(**self._channel_dict)
        if self.config_control_limits[0] is not None:
            limit_low = max(self.config_control_limits[0], limits[0])
        else:
            limit_low = limits[0]
        if self.config_control_limits[1] is not None:
            limit_high = min(self.config_control_limits[1], limits[1])
        else:
            limit_high = limits[1]
        return float(netobtain(limit_low)), float(netobtain(limit_high))

    def get_power(self):
        """ Get the power sent to the setup. Returns zero is switch is off.

        @return (float): Power sent to setup
        """
        return self.get_power_setpoint() if self.get_switch_state() is not False else 0.

    def get_power_setpoint(self):
        """ Get the power set, whether switch state is on or off.

         @return (float): Power set in logic """
        if self._interpolated is None:
            return 0
        else:
            return self._interpolated(self._get_control())[()]

    def set_power(self, value):
        """ Set the power to a given value

        @param (float) value: The power in Watt to set
        """
        if value < self.power_min:
            self.log.warning('Can not set power less than {}. Use switch to go bellow.'.format(self.power_min))

        if value > self.power_max:
            self.log.warning('Can not set power more than {}. Increase laser power and refit.'.format(self.power_max))

        if self._interpolated_inverse is None:
            self.log.warning('Can not set power before calibration')
            return

        control = self._interpolated_inverse(value)[()]
        self._set_control(control)
        self.sigNewPower.emit()

    @property
    def power_max(self):
        """ Get the maximum possible power with current model """
        if len(self.calibration_y) == 0 or np.isnan(self.calibration_y).any():
            return 0
        return np.max(self.calibration_y)

    @property
    def power_min(self):
        """ Get the maximum possible power with current model """
        if len(self.calibration_y) == 0 or np.isnan(self.calibration_y).any():
            return 0
        return np.min(self.calibration_y)

    def get_switch_state(self):
        """ Returns the current switch state of the laser

         @return (bool|None): Boolean state if switch is connected else None
         """
        if self.power_switch.is_connected:
            return self.power_switch().getSwitchState(self.power_switch_index)
        else:
            return None

    def set_switch_state(self, value):
        """ Sets the switch state of the laser if available"""
        if self.power_switch.is_connected:
            if value:
                self.power_switch().switchOn(self.power_switch_index)
            else:
                self.power_switch().switchOff(self.power_switch_index)
        else:
            self.log.error('No switch connected.')

    def set_resolution(self, value):
        """ Setter for the resolution parameter """
        value = int(value)
        if value < 0:
            self.log.error('Cannot set {} as resolution.'.format(value))
        self.resolution = value

    def set_delay(self, value):
        """ Setter for the delay parameter """
        self.delay = value

    def start_calibration(self):
        """ Start the calibration sequence """
        if self.module_state() != 'idle':
            self.log.error('Module already running.')
            return
        self.module_state.run()
        mini, maxi = self._get_control_limits()
        self.calibration_x = np.linspace(mini, maxi, int(self.resolution))
        self.calibration_y = self.calibration_x * np.NaN
        self.sigNewPowerRange.emit()
        self.sigDoNextPoint.emit()
        self.sigModuleStateChanged.emit()

    def abort_calibration(self):
        """ Abort the calibration sequence """
        self.module_state.stop()
        self.timer.stop()
        self.sigModuleStateChanged.emit()

    def _get_next_index(self):
        """ Helper method that compute the index of the first NaN in self.calibration_y """
        nan_indexes = np.arange(len(self.calibration_y))[np.isnan(self.calibration_y)]
        if len(nan_indexes) == 0:
            return None
        else:
            return nan_indexes[0]

    def _next_point_apply_control(self):
        """ First part of the next point measurement : apply a given control value """
        if self.module_state() != 'running':
            return
        if len(self.calibration_y) == 0:
            self.log.error('Something went wrong here !')
        index = self._get_next_index()
        if index is None:  # All points are done
            return self._end_calibration()
        self._set_control(float(self.calibration_x[index]))
        self.timer.start(float(self.delay)*1e3)

    def _end_calibration(self):
        self.module_state.stop()
        self._compute_interpolated()
        self.sigCalibrationFinished.emit()
        self.sigNewPowerRange.emit()
        self.sigModuleStateChanged.emit()

    def _next_point_measure_power(self):
        """ Second part of the next point measurement : measure the power """
        if self.module_state() != 'running':
            return
        index = self._get_next_index()
        self.calibration_y[index] = self.power_meter().get_process_value()
        self.sigDoNextPoint.emit()

    def _compute_interpolated(self):
        """ Method called to compute the interpolation function on new calibration """
        if len(self.calibration_y) == 0:
            self.log.warning('Calibration data is empty. Can not interpolate')
            return
        if self.use_minimum_as_zero:
            self.calibration_y[np.argmin(self.calibration_y)] = 0
        try:
            self._interpolated = interp1d(self.calibration_x, self.calibration_y, fill_value="extrapolate")
            self._interpolated_inverse = interp1d(self.calibration_y, self.calibration_x, fill_value="extrapolate")
        except:
            self.log.error('Calibration data can not be used for interpolation')
