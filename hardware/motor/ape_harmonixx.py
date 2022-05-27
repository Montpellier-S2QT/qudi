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

import socket

class Harmonixx(Base, MotorInterface):

    """ This hardware aim to control the harmonixx module from APE which enable SHG, THG and FHG from of fundamental
    laser beam.

    This interface is useful for a standard, fixed wavelength laser that you can find in a lab.
    It handles power control via constant power or constant current mode, a shutter state if the hardware has a shutter
    and a temperature regulation control.

    ape_harmonixx:
        module.Class: 'motor.ape_harmonixx.Harmonixx'
        host: '127.0.0.1'
        port: '51300'

    """

    _host = ConfigOption('host', default="127.0.0.1")
    _port = ConfigOption('port', missing='error')

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self.dev = None
        self.connected = False

        if not isinstance(self._port, int) or not self._port or not 1 <= self._port <= 65535:
            self.log.error('Portnumber must be passed as integer (range 1..65535)')
        else:
            try:
                self.dev = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.dev.connect((self._host, self._port))
                self.connected = True
                time.sleep(1)

            except:
                import traceback
                traceback.print_exc()
                self.connected = False
                self.dev = None

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        if self.connected:
            self.dev.close()
        return 0

    def send(self, command):
        cmd = command.rstrip()+"\r\n"
        self.dev.send(cmd.encode())

    def read_scpi(self):
        if self.receive(1)[0] != ord("#"):
            return bytearray([])
        else:
            header_len = int(self.receive(1).decode())
            if header_len < 0:
                return bytearray([])
            else:
                data_len = int(self.receive(header_len).decode())
                if data_len <= 0:
                    return bytearray([])

                else:
                    return self.receive(data_len)

    def receive(self, length=-1):
        data_read = length
        answer = bytearray([])
        buffer = bytearray([])
        if not isinstance(length, int):
            raise Exception('[Receive] Data length must be passed as integer')

        if not self.connected:
            raise Exception('[Receive] Error. Not connected')
        else:
            try:
                if length == 0:
                    answer = bytearray([])

                elif length > 0:
                    while data_read > 0:
                        buffer = self.dev.recv(data_read)
                        answer.extend(buffer)
                        data_read -= len(buffer)
                else:
                    while True:
                        buffer = self.dev.recv(1)
                        if buffer[0] != 0:
                            answer.extend(buffer)
                        if buffer[0] == 0x0a:
                            break
            except:
                import traceback
                traceback.print_exc()
                raise Exception('[Receive] Error while reading data')

            return answer

    def query(self, command, block=False):
        answer = bytearray([])
        self.send(command)
        if block == False:
            answer = self.receive().decode().rstrip()
        else:
            answer = self.read_scpi()

        return answer

    def idn(self):
        return self.query("*idn?")

    def stb(self):
        return self.query("*stb?")

    def oper(self):
        return self.query("*oper?")

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
            'label': "SHG",
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
            'label': "SHG",
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
            'label': "SHG",
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
            if label == "WAVELENGTH":
                cmd = self._cmd_from_axis[label]
                abs_pos = self._axis_pos[label] + rel_pos
                wl = str(int(abs_pos*1e9))
                wl = (4-len(wl))*'0'+wl if len(wl)!= 4 else wl
                self._device.write("{}{}".format(cmd, wl))
                self._device.read()
                time.sleep(0.2*abs(abs_pos*1e9-self._axis_pos["WAVELENGTH"]*1e9))
                self._device.read()
                pos_dict[label] = float(self._device.read()[3:])*1e-9
            else:
                cmd = self._cmd_from_axis[label]
                self._device.write("{}{}".format(cmd, int(rel_pos)))
                self._device.read()
                pos_dict[label] = float(self._device.read()[3:].split(" ")[self._axis_index[label]])
        return pos_dict

    def move_abs(self, param_dict):
        """Moves stage to an absolute angle (absolute movement)

        @param dict param_dict: Dictionary with axis name and target position in deg

        @return dict velocity: Dictionary with axis name and final position in deg
        """
        pos_dict = {}
        for label, abs_pos in param_dict.items():
            if label == "WAVELENGTH":
                cmd = self._cmd_from_axis[label]
                wl = str(int(abs_pos*1e9))
                wl = (4-len(wl))*'0'+wl if len(wl) != 4 else wl
                self._device.write("{}{}".format(cmd, wl))
                self._device.read()
                time.sleep(0.2*abs(abs_pos*1e9-self._axis_pos["WAVELENGTH"]*1e9))
                self._device.read()
                pos_dict[label] = float(self._device.read()[3:])*1e-9
            else:
                cmd = self._cmd_from_axis[label]
                rel_pos = str(int(abs(self._axis_pos[label] - abs_pos)))
                rel_pos = (3-len(rel_pos))*'0'+wl if len(rel_pos) < 3 else rel_pos
                self._device.write("{}{}".format(cmd, rel_pos))
                self._device.read()
                pos_dict[label] = float(self._device.read()[3:].split(" ")[self._axis_index[label]])
        return pos_dict

    def abort(self):
        """Stops movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        self._device.write("BRK")
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
            if label == "WAVELENGTH":
                pos_dict[label] = self._axis_pos[label]
            else:
                cmd = self._cmd_from_axis[label]
                self._device.write("{}+0".format(cmd))
                self._device.read()
                pos_dict[label] = float(self._device.read()[3:].split(" ")[self._axis_index[label]])

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
            if label == "WAVELENGTH":
                self._device.write("{}".format(label))
                time.sleep(2)
                self._device.read()
                pos_dict[label] = float(self._device.read()[3:])*1e-9
        else:
                self._device.write("{}+0".format(label))
                self._device.read()
                pos_dict[label] = float(self._device.read()[3:].split(" ")[self._axis_index[label]])

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
