# -*- coding: utf-8 -*-
"""
Interact with switches.

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

from logic.generic_logic import GenericLogic
from core.connector import Connector
from core.configoption import ConfigOption
from core.util.mutex import RecursiveMutex
from qtpy import QtCore


class SwitchLogic(GenericLogic):
    """ Logic module for interacting with the hardware switches.
    This logic has the same structure as the SwitchInterface but supplies additional functionality:
        - switches can either be manipulated by index or by their names
        - signals are generated on state changes

    switchlogic:
        module.Class: 'switch_logic.SwitchLogic'
        watchdog_interval: 1  # optional
        autostart_watchdog: True  # optional
        connect:
            switch: <switch name>
    """

    # connector for one switch, if multiple switches are needed use the SwitchCombinerInterfuse
    switch = Connector(interface='SwitchInterface')

    _custom_name_config = ConfigOption(name='custom_name', default=None, missing='nothing')
    _custom_states_config = ConfigOption(name='custom_states', default=None, missing='nothing')

    _watchdog_interval = ConfigOption(name='watchdog_interval', default=1.0, missing='nothing')
    _autostart_watchdog = ConfigOption(name='autostart_watchdog', default=False, missing='nothing')

    sigSwitchesChanged = QtCore.Signal(dict)
    sigWatchdogToggled = QtCore.Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._thread_lock = RecursiveMutex()

        self._watchdog_active = None
        self._watchdog_interval_ms = None
        self._old_states = None
        self._custom_states = None
        self._hardware_states = None

    def on_activate(self):
        """ Activate module """

        # First we check custom switch names of config
        if not isinstance(self._custom_states, dict):
            self.log.error('custom_states must be a dict of tuples')
        if len(self._custom_states) != len(self.hardware().get_available_states()):
            self.log.error('number of elements in custom states do not match')
        if not all((isinstance(name, str) and name) for name in self._custom_states):
            self.log.error('Switch name must be non-empty string')
        if not all(len(states) > 1 for states in self._custom_states.values()):
            self.log.error('State tuple must contain at least 2 states')
        if not all(all((s and isinstance(s, str)) for s in states) for states in self._custom_states.values()):
            self.log.error('Switch states must be non-empty strings')

        # Convert state lists to tuples in order to restrict mutation
        self._custom_states = {switch: tuple(states) for switch, states in self._custom_states.items()}
        # Store the hardware defined states for name conversion
        self._hardware_states = self.hardware().available_states

        # Now we set up watchdog
        self._old_states = self.states
        self._watchdog_interval_ms = int(round(self._watchdog_interval * 1000))

        if self._autostart_watchdog:
            self._watchdog_active = True
            QtCore.QMetaObject.invokeMethod(self, '_watchdog_body', QtCore.Qt.QueuedConnection)
        else:
            self._watchdog_active = False

    def on_deactivate(self):
        """ Deactivate module """
        self._watchdog_active = False

    def device_name(self):
        """ Name of the connected hardware switch as string.

        @return str: The name of the connected hardware switch
        """
        return self.switch().get_name()

    @property
    def watchdog_active(self):
        return self._watchdog_active

    @property
    def states(self):
        """ The current states the hardware is in as state dictionary with switch names as keys and
        state names as values.

        @return dict: All the current states of the switches in the form {"switch": "state"}
        """
        with self._thread_lock:
            try:
                states = self.switch().get_states()
            except:
                self.log.exception(f'Error during query of all switch states.')
                states = dict()
            return states

    @states.setter
    def states(self, state_dict):
        """ The setter for the states of the hardware.

        The states of the system can be set by specifying a dict that has the switch names as keys
        and the names of the states as values.

        @param dict state_dict: state dict of the form {"switch": "state"}
        """
        with self._thread_lock:
            try:
                self.switch().states = state_dict
            except:
                self.log.exception('Error while trying to set switch states.')

            states = self.states
            if states:
                self.sigSwitchesChanged.emit({switch: states[switch] for switch in state_dict})

    def get_state(self, switch):
        """ Query state of single switch by name

        @param str switch: name of the switch to query the state for
        @return str: The current switch state
        """
        with self._thread_lock:
            try:
                state = self.switch().get_state(switch)
            except:
                self.log.exception(f'Error while trying to query state of switch "{switch}".')
                state = None
            return state

    @QtCore.Slot(str, str)
    def set_state(self, switch, state):
        """ Query state of single switch by name

        @param str switch: name of the switch to change
        @param str state: name of the state to set
        """
        with self._thread_lock:
            try:
                self.switch().set_state(switch, state)
            except:
                self.log.exception(
                    f'Error while trying to set switch "{switch}" to state "{state}".'
                )
            curr_state = self.get_state(switch)
            if curr_state is not None:
                self.sigSwitchesChanged.emit({switch: curr_state})

    @QtCore.Slot(bool)
    def toggle_watchdog(self, enable):
        """

        @param bool enable:
        """
        enable = bool(enable)
        with self._thread_lock:
            if enable != self._watchdog_active:
                self._watchdog_active = enable
                self.sigWatchdogToggled.emit(enable)
                if enable:
                    QtCore.QMetaObject.invokeMethod(self,
                                                    '_watchdog_body',
                                                    QtCore.Qt.QueuedConnection)

    @QtCore.Slot()
    def _watchdog_body(self):
        """ Helper function to regularly query the states from the hardware.

        This function is called by an internal signal and queries the hardware regularly to fire
        the signal sig_switch_updated, if the hardware changed its state without notifying the logic.
        The timing of the watchdog is set by the ConfigOption watchdog_interval in seconds.
        """
        with self._thread_lock:
            if self._watchdog_active:
                curr_states = self.states
                diff_state = {switch: state for switch, state in curr_states.items() if
                              state != self._old_states[switch]}
                self._old_states = curr_states
                if diff_state:
                    self.sigSwitchesChanged.emit(diff_state)
                QtCore.QTimer.singleShot(self._watchdog_interval_ms, self._watchdog_body)
