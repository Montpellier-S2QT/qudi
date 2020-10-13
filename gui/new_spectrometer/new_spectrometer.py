# -*- coding: utf-8 -*-
"""
This module contains a GUI for operating the spectrum logic module.

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

import os
import pyqtgraph as pg
import numpy as np

from core.connector import Connector
from core.util import units
from core.statusvariable import StatusVar
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase
from gui.fitsettings import FitSettingsDialog, FitSettingsComboBox
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic

class SpectrometerWindow(QtWidgets.QMainWindow):

    def __init__(self):
        """ Create the laser scanner window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_spectrometer_window.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

class Main(GUIBase):
    """
    """
    # declare connectors
    spectrumlogic = Connector(interface='SpectrumLogic')

    _counter_read_mode = StatusVar('counter_read_mode', 'FVB')
    _counter_exposure_time = StatusVar('counter_exposure_time', 0)
    _image_read_mode = StatusVar('image_read_mode', 'IMAGE_ADVANCED')
    _image_acquisition_mode = StatusVar('image_acquisition_mode', 'LIVE')
    _image_exposure_time = StatusVar('image_exposure_time', None)
    _image_readout_speed = StatusVar('image_readout_speed', None)
    _spectrum_read_mode = StatusVar('spectrum_read_mode', 'MULTIPLE_TRACKS')
    _spectrum_acquisition_mode = StatusVar('spectrum_acquisition_mode', 'SINGLE_SCAN')
    _spectrum_exposure_time = StatusVar('spectrum_exposure_time', None)
    _spectrum_readout_speed = StatusVar('spectrum_readout_speed', None)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """

        self._spectrumlogic = self.spectrumlogic()

        # setting up the window
        self._mw = SpectrometerWindow()

        self._grating_index_buttons = [self._mw.grating_1, self._mw.grating_2, self._mw.grating_3]
        self._input_port_buttons = [self._mw.input_front, self._mw.input_side]
        self. _input_slit_width_spins = [self._mw.input_slit_width_front, self._mw.input_slit_width_side]
        self._output_port_buttons = [self._mw.output_front, self._mw.output_side]
        self._output_slit_width_spins = [self._mw.output_slit_width_front, self._mw.output_slit_width_side]
        self._camera_gain_buttons = [self._mw.gain_1, self._mw.gain_2, self._mw.gain_3]

        trigger_modes = self._spectrumlogic.camera_constraints.trigger_modes
        for i in range(len(trigger_modes)):
            self._mw.trigger_modes.setItemText(i, trigger_modes[i])

        camera_gains = self._spectrumlogic.camera_constraints.internal_gains
        for i in range(len(camera_gains)):
            self._camera_gain_buttons[i].setText(str(camera_gains[i]))

        self._grating_index_buttons[self._spectrumlogic.grating_index].setDown(True)

        self._mw.input_slit_width_front.setValue(self._spectrumlogic.get_input_slit_width(port='front')*1e6)
        self._mw.input_slit_width_side.setValue(self._spectrumlogic.get_input_slit_width(port='side')*1e6)
        if self._spectrumlogic.input_port == "INPUT_SIDE":
            self._input_port_buttons[1].setDown(True)
        else:
            self._input_port_buttons[0].setDown(True)

        self._mw.output_slit_width_front.setValue(self._spectrumlogic.get_output_slit_width(port='front')*1e6)
        self._mw.output_slit_width_side.setValue(self._spectrumlogic.get_output_slit_width(port='side')*1e6)
        if self._spectrumlogic.output_port == "OUTPUT_SIDE":
            self._output_port_buttons[1].setDown(True)
        else:
            self._output_port_buttons[0].setDown(True)

        self._mw.wavelength_correction.setValue(self._spectrumlogic.wavelength_calibration)

        self._camera_internal_gains = self._spectrumlogic.camera_constraints.internal_gains
        camera_gain_index = np.where([ gain == self._spectrumlogic.camera_gain for gain in self._camera_internal_gains])
        self._camera_gain_buttons[camera_gain_index[0][0]].setDown(True)

        self._mw.camera_temperature_setpoint.setValue(self._spectrumlogic.temperature_setpoint)
        self._mw.cooler_on.setDown(self._spectrumlogic.cooler_status)

        self._mw.trigger_modes.setCurrentText(self._spectrumlogic.trigger_mode)

        self._mw.camera_temperature_setpoint.setValue(self._spectrumlogic.temperature_setpoint)
        self._mw.cooler_on.setDown(self._spectrumlogic.cooler_status)

        if self._spectrumlogic.camera_constraints.has_shutter:
            self._mw.shutter_modes.setCurrentText(self._spectrumlogic.shutter_state)
        else:
            self._mw.shutter_modes.setEnabled(False)

        self._mw.center_wavelength.setValue(self._spectrumlogic.center_wavelength)

        self._mw.counter_read_modes.setCurrentText(self._counter_read_mode)
        self._mw.counter_exposure_time.setValue(self._counter_exposure_time)

        self._mw.image_read_modes.setCurrentText(self._image_read_mode)
        self._mw.image_acquisition_modes.setCurrentText(self._image_acquisition_mode)
        if self._image_exposure_time:
            self._mw.image_exposure_time.setValue(self._image_exposure_time)
        else:
            self._mw.image_exposure_time.setValue(self._spectrumlogic.exposure_time)
        if self._image_readout_speed:
            self._mw.image_readout_speed.setValue(self._image_readout_speed)
        else:
            self._mw.image_readout_speed.setValue(self._spectrumlogic.readout_speed)

        self._mw.spectrum_read_modes.setCurrentText(self._spectrum_read_mode)
        self._mw.spectrum_acquisition_modes.setCurrentText(self._spectrum_acquisition_mode)
        if self._spectrum_exposure_time:
            self._mw.spectrum_exposure_time.setValue(self._spectrum_exposure_time)
        else:
            self._mw.spectrum_exposure_time.setValue(self._spectrumlogic.exposure_time)
        if self._spectrum_readout_speed:
            self._mw.spectrum_readout_speed.setValue(self._spectrum_readout_speed)
        else:
            self._mw.spectrum_readout_speed.setValue(self._spectrumlogic.readout_speed)

        # Connect signals
        self._mw.grating_1.clicked.connect(self.manage_grating_index_buttons)
        self._mw.grating_2.clicked.connect(self.manage_grating_index_buttons)
        self._mw.grating_3.clicked.connect(self.manage_grating_index_buttons)

        self._mw.input_front.clicked.connect(self.manage_input_port_buttons)
        self._mw.input_side.clicked.connect(self.manage_input_port_buttons)

        self._mw.output_front.clicked.connect(self.manage_output_port_buttons)
        self._mw.output_side.clicked.connect(self.manage_output_port_buttons)

        self._mw.cooler_on.clicked.connect(self.manage_cooler_status)

        self._mw.gain_1.clicked.connect(self.manage_camera_gain_buttons)
        self._mw.gain_2.clicked.connect(self.manage_camera_gain_buttons)
        self._mw.gain_3.clicked.connect(self.manage_camera_gain_buttons)

        self._mw.start_counter_acquisition.clicked.connect(self.start_counter_acquisition)
        self._mw.stop_counter_acquisition.clicked.connect(self._spectrumlogic.stop_acquisition)

        self._mw.start_image_acquisition.clicked.connect(self.start_image_acquisition)
        self._mw.stop_image_acquisition.clicked.connect(self._spectrumlogic.stop_acquisition)

        self._mw.start_spectrum_acquisition.clicked.connect(self.start_spectrum_acquisition)
        self._mw.stop_spectrum_acquisition.clicked.connect(self._spectrumlogic.stop_acquisition)

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """

        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def update_general_settings(self):

        grating_index = np.where([btn.isDown() for btn in self._grating_index_buttons])[0][0]
        self._spectrumlogic.grating_index = grating_index

        input_port_index = np.where([btn.isDown() for btn in self._input_port_buttons])[0][0]
        self._spectrumlogic.input_port = self._spectrumlogic.spectro_constraints.ports[input_port_index].type
        self._spectrumlogic.input_slit_width =self._input_slit_width_spins[input_port_index].value()

        output_port_index = np.where([btn.isDown() for btn in self._output_port_buttons])[0][0]
        self._spectrumlogic.output_port = self._spectrumlogic.spectro_constraints.ports[2 + output_port_index].type
        self._spectrumlogic.output_slit_width =self._output_slit_width_spins[output_port_index].value()

        self._spectrumlogic.wavelength_calibration = self._mw.wavelength_correction.value()

        camera_gain_index = np.where([button.isDown() for button in self._camera_gain_buttons])[0][0]
        self._spectrumlogic.camera_gain = self._spectrumlogic.camera_constraints.internal_gains[camera_gain_index]

        self._spectrumlogic.trigger_mode = self._mw.trigger_modes.currentText()

        self._spectrumlogic.shutter_state = self._mw.shutter_modes.currentText()

    def start_counter_acquisition(self):
        self.update_general_settings()
        

    def stop_counter_acquisition(self):
        pass

    def start_image_acquisition(self):
        self.update_general_settings()

    def stop_image_acquisition(self):
        pass

    def start_spectrum_acquisition(self):
        self.update_general_settings()

    def stop_spectrum_acquisition(self):
        pass

    def manage_grating_index_buttons(self):

        for grating_index_button in self._grating_index_buttons:
            if grating_index_button == self.sender():
                grating_index_button.setDown(True)
            else:
                grating_index_button.setDown(False)

    def get_grating_index(self):

        grating_1 = self._mw.grating_1.isDown()
        grating_2 = self._mw.grating_2.isDown()
        grating_3 = self._mw.grating_3.isDown()

        return grating_1*1+grating_2*2+grating_3*3

    def manage_camera_gain_buttons(self):

        for camera_gain_button in self._camera_gain_buttons:
            if camera_gain_button == self.sender():
                camera_gain_button.setDown(True)
            else:
                camera_gain_button.setDown(False)

    def manage_input_port_buttons(self):

        for input_port_button in self._input_port_buttons:
            if input_port_button == self.sender():
                input_port_button.setDown(True)
            else:
                input_port_button.setDown(False)

    def manage_output_port_buttons(self):

        for output_port_button in self._output_port_buttons:
            if output_port_button == self.sender():
                output_port_button.setDown(True)
            else:
                output_port_button.setDown(False)

    def manage_cooler_status(self):

        self._spectrumlogic.temperature_setpoint = self._mw.camera_temperature_setpoint.value()
        cooler_status = self._spectrumlogic.cooler_status
        self._spectrumlogic.cooler_status = not cooler_status
        self._mw.cooler_on.setDown(not cooler_status)

