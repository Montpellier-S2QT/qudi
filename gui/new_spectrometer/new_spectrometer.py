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
from functools import partial

from core.connector import Connector
from core.util import units
from core.statusvariable import StatusVar
from gui.colordefs import QudiPalettePale as palette
from gui.colordefs import ColorScaleMagma
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
    _counter_time_window = StatusVar('counter_time_window', 60)
    _image_read_mode = StatusVar('image_read_mode', 'IMAGE_ADVANCED')
    _image_acquisition_mode = StatusVar('image_acquisition_mode', 'LIVE')
    _image_exposure_time = StatusVar('image_exposure_time', None)
    _image_readout_speed = StatusVar('image_readout_speed', None)
    _spectrum_read_mode = StatusVar('spectrum_read_mode', 'MULTIPLE_TRACKS')
    _spectrum_acquisition_mode = StatusVar('spectrum_acquisition_mode', 'SINGLE_SCAN')
    _spectrum_exposure_time = StatusVar('spectrum_exposure_time', None)
    _spectrum_readout_speed = StatusVar('spectrum_readout_speed', None)

    _counter_data = StatusVar('counter_data', np.zeros((2, 1000)), )
    _image_data = StatusVar('image_data', np.zeros((1000, 1000)))
    _spectrum_data = StatusVar('spectrum_data', np.zeros((2, 1000)))

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
        self._input_slit_width_spins = [self._mw.input_slit_width_front, self._mw.input_slit_width_side]
        self._output_port_buttons = [self._mw.output_front, self._mw.output_side]
        self._output_slit_width_spins = [self._mw.output_slit_width_front, self._mw.output_slit_width_side]
        self._camera_gain_buttons = [self._mw.gain_1, self._mw.gain_2, self._mw.gain_3]

        self._start_acquisition_buttons = [self._mw.start_counter_acquisition, self._mw.start_image_acquisition,
                                           self._mw.start_spectrum_acquisition]
        self._start_dark_acquisition_buttons = [self._mw.image_acquire_dark, self._mw.spectrum_acquire_dark]
        self._stop_acquisition_buttons = [self._mw.stop_counter_acquisition, self._mw.stop_image_acquisition,
                                           self._mw.stop_spectrum_acquisition]

        for btn in self._grating_index_buttons:
            btn.setCheckable(True)
        for btn in self._input_port_buttons:
            btn.setCheckable(True)
        for btn in self._output_port_buttons:
            btn.setCheckable(True)
        for btn in self._camera_gain_buttons:
            btn.setCheckable(True)


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
        camera_gain_index = np.where([gain == self._spectrumlogic.camera_gain for gain in self._camera_internal_gains])
        self._camera_gain_buttons[camera_gain_index[0][0]].setDown(True)

        self._camera_temperature_timer = QtCore.QTimer()
        self._camera_temperature_timer.timeout.connect(self._update_camera_temperature, QtCore.Qt.QueuedConnection)
        self._camera_temperature_timer.start(500)

        self._mw.trigger_modes.setCurrentText(self._spectrumlogic.trigger_mode)

        self._mw.camera_temperature_setpoint.setValue(self._spectrumlogic.temperature_setpoint)
        self._mw.cooler_on.setCheckable(True)
        self._mw.cooler_on.setDown(self._spectrumlogic.cooler_status)

        if self._spectrumlogic.camera_constraints.has_shutter:
            self._mw.shutter_modes.setCurrentText(self._spectrumlogic.shutter_state)
        else:
            self._mw.shutter_modes.setEnabled(False)

        self._mw.center_wavelength.setValue(self._spectrumlogic.center_wavelength*1e9)

        self._mw.counter_read_modes.setCurrentText(self._counter_read_mode)
        self._mw.counter_exposure_time.setValue(self._counter_exposure_time)
        self._mw.counter_time_window.setValue(self._counter_time_window)

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

        # Connect signals :
        for btn in self._grating_index_buttons:
            btn.toggled.connect(self.manage_grating_index_buttons)

        for btn in self._input_port_buttons:
            btn.toggled.connect(self.manage_input_port_buttons)

        for btn in self._output_port_buttons:
            btn.toggled.connect(self.manage_output_port_buttons)

        self._mw.cooler_on.toggled.connect(self.manage_cooler_status)

        for btn in self._camera_gain_buttons:
            btn.toggled.connect(self.manage_camera_gain_buttons)

        for i in range(len(self._start_acquisition_buttons)):
            self._start_acquisition_buttons[i].clicked.connect(partial(self.start_acquisition, i, False))
            self._start_acquisition_buttons[i].setEnabled(True)

        for i in range(len(self._start_dark_acquisition_buttons)):
            self._start_dark_acquisition_buttons[i].clicked.connect(partial(self.start_acquisition, i, True))
            self._start_dark_acquisition_buttons[i].setEnabled(True)

        for i in range(len(self._stop_acquisition_buttons)):
            self._stop_acquisition_buttons[i].clicked.connect(partial(self.stop_acquisition, i))
            self._stop_acquisition_buttons[i].setEnabled(False)

        self._mw.counter_graph.setLabel('left', 'photon counts', units='counts/s')
        self._mw.counter_graph.setLabel('bottom', 'acquisition time', units='s')
        self._counter_plot = self._mw.counter_graph.plot(self._counter_data[0], self._counter_data[1])

        self._image = pg.ImageItem(image=self._image_data, axisOrder='row-major')
        self._mw.image_graph.addItem(self._image)
        self._color_map = ColorScaleMagma()
        self._image.setLookupTable(self._color_map.lut)

        self._mw.spectrum_graph.setLabel('left', 'Photoluminescence', units='counts/s')
        self._mw.spectrum_graph.setLabel('bottom', 'wavelength', units='m')
        self._spectrum_plot = self._mw.spectrum_graph.plot(self._spectrum_data[0], self._spectrum_data[1])

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._counter_read_mode = self._mw.counter_read_modes.currentText()
        self._counter_exposure_time = self._mw.counter_exposure_time.value()
        self._image_read_mode = self._mw.image_read_modes.currentText()
        self._image_acquisition_mode = self._mw.image_acquisition_modes.currentText()
        self._image_exposure_time = self._mw.image_exposure_time.value()
        self._image_readout_speed = self._mw.image_readout_speed.value()
        self._spectrum_read_mode = self._mw.spectrum_read_modes.currentText()
        self._spectrum_acquisition_mode = self._mw.spectrum_acquisition_modes.currentText()
        self._spectrum_exposure_time = self._mw.spectrum_exposure_time.value()
        self._spectrum_readout_speed = self._mw.spectrum_readout_speed.value()
        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def update_general_settings(self):

        self._spectrumlogic.wavelength_calibration = self._mw.wavelength_correction.value()

        self._spectrumlogic.trigger_mode = self._mw.trigger_modes.currentText()

        self._spectrumlogic.shutter_state = self._mw.shutter_modes.currentText()

        self._spectrumlogic.center_wavelength = self._mw.center_wavelength.value()*1e-9

    def _buttons_enable_config(self, mode_index, acquisition_started):

        for i in range(3):
            stop_btn_state = acquisition_started
            start_btn_state = not acquisition_started
            if i != mode_index and acquisition_started:
                stop_btn_state = False
            if i<2:
                self._start_dark_acquisition_buttons[i].setEnabled(start_btn_state)
            self._stop_acquisition_buttons[i].setEnabled(stop_btn_state)
            self._start_acquisition_buttons[i].setEnabled(start_btn_state)

    def start_acquisition(self, mode_index, acquire_dark):

        self._buttons_enable_config(mode_index, True)
        self.update_general_settings()
        if mode_index == 0:
            self._spectrumlogic.read_mode = self._mw.counter_read_modes.currentText()
            self._spectrumlogic.exposure_time = self._mw.counter_exposure_time.value()
            # TODO : Add readout speed
            self._spectrumlogic.acquisition_mode = "LIVE_SCAN"
            self._counter_time_window = self._mw.counter_time_window.value()
            self._spectrumlogic.sigUpdateData.connect(lambda: self._update_data(mode_index))
        elif mode_index == 1:
            self._spectrumlogic.read_mode = self._mw.image_read_modes.currentText()
            self._spectrumlogic.acquisition_mode = self._mw.image_acquisition_modes.currentText()
            self._spectrumlogic.exposure_time = self._mw.image_exposure_time.value()
            self._spectrumlogic.sigUpdateData.connect(lambda: self._update_data(mode_index))
        else:
            self._spectrumlogic.read_mode = self._mw.spectrum_read_modes.currentText()
            self._spectrumlogic.acquisition_mode = self._mw.spectrum_acquisition_modes.currentText()
            self._spectrumlogic.exposure_time = self._mw.spectrum_exposure_time.value()
            self._spectrumlogic.sigUpdateData.connect(lambda: self._update_data(mode_index))

        if acquire_dark:
            self._spectrumlogic.shutter_state = 'CLOSED'
        else:
            self._spectrumlogic.shutter_state = self._mw.shutter_modes.currentText()

        self._spectrumlogic.start_acquisition()

    def _update_data(self, mode_index):

        data = self._spectrumlogic.acquired_data

        if mode_index == 0:
            counts = sum([track.sum() for track in data])
            x = np.append(self._counter_data[0], self._counter_data[0][-1]+self._spectrumlogic.exposure_time)
            y = np.append(self._counter_data[1], counts)
            self._counter_data = np.array([x, y])
            self._counter_plot.setData(x, y)
            #self._mw.counter_graph.setRange(xRange=(x[-1] - self._counter_time_window, x[-1]))
        if mode_index == 1:
            self._image_data = data
            self._image.setImage(data)
        else:
            x = self._spectrumlogic.wavelength_spectrum
            if self._spectrumlogic.acquisition_mode == "MULTI_SCAN":
                y = np.sum(self._spectrumlogic.acquired_data, axis=0)
            else:
                y = self._spectrumlogic.acquired_data
            self._spectrum_data = np.array([x, y])
            self._spectrum_plot.setData(x, y)

        if self._spectrumlogic.module_state() == "idle":
            self._spectrumlogic.sigUpdateData.disconnect()
            self._buttons_enable_config(mode_index, False)

    def stop_acquisition(self, mode_index):
        self._buttons_enable_config(mode_index, False)
        self._spectrumlogic.stop_acquisition()

    def manage_grating_index_buttons(self):

        for i in range(len(self._grating_index_buttons)):
            btn = self._grating_index_buttons[i]
            if btn == self.sender():
                btn.setDown(True)
                self._spectrumlogic.grating_index = i
            else:
                btn.setDown(False)

    def get_grating_index(self):

        grating_1 = self._mw.grating_1.isDown()
        grating_2 = self._mw.grating_2.isDown()
        grating_3 = self._mw.grating_3.isDown()

        return grating_1*1+grating_2*2+grating_3*3

    def manage_camera_gain_buttons(self):

        for i in range(len(self._camera_gain_buttons)):
            btn = self._camera_gain_buttons[i]
            if btn == self.sender():
                btn.setDown(True)
                self._spectrumlogic.camera_gain = self._spectrumlogic.camera_constraints.internal_gains[i]
            else:
                btn.setDown(False)

    def manage_input_port_buttons(self):

        for i in range(len(self._input_port_buttons)):
            btn = self._input_port_buttons[i]
            if btn == self.sender():
                btn.setDown(True)
                self._spectrumlogic.input_port = self._spectrumlogic.spectro_constraints.ports[i].type
                self._spectrumlogic.input_slit_width = self._input_slit_width_spins[i].value() * 1e-6
            else:
                btn.setDown(False)

    def manage_output_port_buttons(self):

        for i in range(len(self._output_port_buttons)):
            btn = self._output_port_buttons[i]
            if btn == self.sender():
                btn.setDown(True)
                self._spectrumlogic.output_port = self._spectrumlogic.spectro_constraints.ports[i+2].type
                self._spectrumlogic.output_slit_width = self._output_slit_width_spins[i].value() * 1e-6
            else:
                btn.setDown(False)

    def manage_cooler_status(self):

        self._spectrumlogic.temperature_setpoint = self._mw.camera_temperature_setpoint.value()
        cooler_status = self._spectrumlogic.cooler_status
        self._spectrumlogic.cooler_status = not cooler_status
        self._mw.cooler_on.setDown(not cooler_status)

    def _update_camera_temperature(self):

        self._mw.cooler_on_label.setText("Cooler "+ "ON" if self._spectrumlogic.cooler_status else "OFF")
        self._mw.camera_temperature.setText(str(round(self._spectrumlogic.camera_temperature-273.15, 2))+"°C")
