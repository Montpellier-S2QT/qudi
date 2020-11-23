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
from core.configoption import ConfigOption
from core.util.units import ScaledFloat
from core.statusvariable import StatusVar
from gui.colordefs import QudiPalettePale as palette
from gui.colordefs import ColorScaleMagma
from gui.guibase import GUIBase
from gui.fitsettings import FitSettingsDialog, FitSettingsComboBox
from qtwidgets.scientific_spinbox import ScienDSpinBox, ScienSpinBox
from interface.grating_spectrometer_interface import PortType
from interface.science_camera_interface import ReadMode
from logic.spectrum_logic import AcquisitionMode
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        """ Create the laser scanner window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_mainwindow.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

class SettingsTab(QtWidgets.QWidget):

    def __init__(self):
        """ Create the laser scanner window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_settings_tab.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

class ImageTab(QtWidgets.QWidget):

    def __init__(self):
        """ Create the laser scanner window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_image_tab.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

class AlignementTab(QtWidgets.QWidget):

    def __init__(self):
        """ Create the laser scanner window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_alignement_tab.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()

class SpectrumTab(QtWidgets.QWidget):

    def __init__(self):
        """ Create the laser scanner window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_spectrum_tab.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class Main(GUIBase):
    """
    """
    # declare connectors
    spectrumlogic = Connector(interface='SpectrumLogic')
    savelogic = Connector(interface='SaveLogic')

    _cooler_temperature_unit = ConfigOption('cooler_temperature_unit')

    _alignement_read_mode = StatusVar('alignement_read_mode', 'FVB')
    _alignement_exposure_time = StatusVar('alignement_exposure_time', 0)
    _alignement_time_window = StatusVar('alignement_time_window', 60)

    _image_read_mode = StatusVar('image_read_mode', 'IMAGE_ADVANCED')
    _image_acquisition_mode = StatusVar('image_acquisition_mode', 'LIVE')
    _image_exposure_time = StatusVar('image_exposure_time', None)
    _image_readout_speed = StatusVar('image_readout_speed', None)

    _spectrum_read_mode = StatusVar('spectrum_read_mode', 'MULTIPLE_TRACKS')
    _spectrum_acquisition_mode = StatusVar('spectrum_acquisition_mode', 'SINGLE_SCAN')
    _spectrum_exposure_time = StatusVar('spectrum_exposure_time', None)
    _spectrum_readout_speed = StatusVar('spectrum_readout_speed', None)

    _active_tracks = StatusVar('active_tracks', [])

    _image_data = StatusVar('image_data', np.zeros((1000, 1000)))
    _image_dark = StatusVar('image_dark', np.zeros((1000, 1000)))
    _image_params = StatusVar('image_params', dict())
    _counter_data = StatusVar('counter_data', np.zeros((2, 1000)))
    _spectrum_data = StatusVar('spectrum_data', np.zeros((2, 1000)))
    _spectrum_dark = StatusVar('spectrum_dark', np.zeros(1000))
    _spectrum_params = StatusVar('spectrum_params', dict())

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        self._image_data = np.zeros((1000, 1000))

        self._spectrumlogic = self.spectrumlogic()

        # setting up the window
        self._mw = MainWindow()
        self._settings_tab = SettingsTab()
        self._image_tab = ImageTab()
        self._alignement_tab = AlignementTab()
        self._spectrum_tab = SpectrumTab()

        self._mw.tab.addTab(self._settings_tab, "Settings")
        self._mw.tab.addTab(self._image_tab, "Image")
        self._mw.tab.addTab(self._alignement_tab, "Aligement")
        self._mw.tab.addTab(self._spectrum_tab, "Spectrum")

        self._acquire_dark_buttons = []
        self._start_acquisition_buttons = []
        self._stop_acquisition_buttons = []
        self._save_data_buttons = []

        self._track_buttons = [self._image_tab.track1, self._image_tab.track2,
                               self._image_tab.track3, self._image_tab.track4]
        self._track_selector = []

        self._activate_settings_tab()
        self._activate_image_tab()
        self._activate_alignement_tab()
        self._activate_spectrum_tab()

        self._manage_stop_acquisition()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._alignement_read_mode = self._alignement_tab.read_modes.currentData()
        self._alignement_exposure_time = self.alignement_exposure_time_widget.value()
        self._image_acquisition_mode = self._image_tab.acquisition_modes.currentData()
        self._image_read_mode = self._image_tab.read_modes.currentData()
        self._image_exposure_time = self.image_exposure_time_widget.value()
        self._image_readout_speed = self._image_tab.readout_speed.currentData()
        self._spectrum_acquisition_mode = self._spectrum_tab.acquisition_modes.currentData()
        self._spectrum_read_mode = self._spectrum_tab.read_modes.currentData()
        self._spectrum_exposure_time = self.spectrum_exposure_time_widget.value()
        self._spectrum_readout_speed = self._spectrum_tab.readout_speed.currentData()
        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def _activate_settings_tab(self):

        spectro_constraints = self._spectrumlogic.spectro_constraints

        self._grating_buttons = [self._settings_tab.grating_1, self._settings_tab.grating_2, self._settings_tab.grating_3]
        self._input_port_buttons = [self._settings_tab.input_front, self._settings_tab.input_side]
        self._input_slit_width = []
        self._output_port_buttons = [self._settings_tab.output_front, self._settings_tab.output_side]
        self._output_slit_width = []

        for i in range(3):
            self._grating_buttons[i].setText('{}rpm'.format(
                int(self._spectrumlogic.spectro_constraints.gratings[i].ruling*1000)))
            self._grating_buttons[i].clicked.connect(partial(self._manage_grating_buttons, i))
            if i == self._spectrumlogic.grating_index:
                self._grating_buttons[i].setDown(True)

        input_ports = [port for port in spectro_constraints.ports if port.type in [PortType.INPUT_FRONT, PortType.INPUT_FRONT]]
        output_ports = [port for port in spectro_constraints.ports if port.type in [PortType.OUTPUT_FRONT, PortType.OUTPUT_SIDE]]

        for i in range(2):

            if i < len(input_ports):

                if len(input_ports) == 2:
                    self._input_port_buttons[i].clicked.connect(partial(self._manage_port_buttons, i))
                if input_ports[i].type.name == self._spectrumlogic.input_port:
                    self._input_port_buttons[i].setDown(True)

                input_widget = ScienDSpinBox()
                input_widget.setRange(input_ports[i].constraints.min, input_ports[i].constraints.max)
                input_widget.setValue(self._spectrumlogic.input_slit_width)
                input_widget.setSuffix('m')
                input_widget.valueChanged.connect(partial(self._spectrumlogic.set_input_slit_width, port=input_ports[i].type))
                self._input_slit_width.append(input_widget)
                self._settings_tab.input_layout.addWidget(input_widget, i, 2)

            else:
                self._input_port_buttons[i].setEnabled(False)

            if i < len(output_ports):

                if len(output_ports) == 2:
                    self._output_port_buttons[i].clicked.connect(partial(self._manage_port_buttons, i+2))
                if output_ports[i].type.name == self._spectrumlogic.output_port:
                    self._output_port_buttons[i].setDown(True)

                output_widget = ScienDSpinBox()
                output_widget.setRange(output_ports[i].constraints.min, output_ports[i].constraints.max)
                output_widget.setValue(self._spectrumlogic.output_slit_width)
                output_widget.setSuffix('m')
                output_widget.valueChanged.connect(partial(self._spectrumlogic.set_output_slit_width, port=output_ports[i].type))
                self._output_slit_width.append(output_widget)
                self._settings_tab.output_layout.addWidget(output_widget, i, 2)

            else:
                self._output_port_buttons[i].setEnabled(False)

        self._calibration_widget = ScienDSpinBox()
        self._calibration_widget.setValue(self._spectrumlogic.wavelength_calibration)
        self._calibration_widget.setSuffix('m')
        self._calibration_widget.valueChanged.connect(self.set_settings_params)
        self._settings_tab.calibration_layout.addWidget(self._calibration_widget)

        for gain in self._spectrumlogic.camera_constraints.internal_gains:
            self._settings_tab.camera_gains.addItem(str(gain), gain)
            self._settings_tab.camera_gains.currentTextChanged.connect(self.set_settings_params)
            if gain == self._spectrumlogic.camera_gain:
                self._settings_tab.camera_gains.setCurrentText(str(gain))

        for trigger_mode in self._spectrumlogic.camera_constraints.trigger_modes:
            self._settings_tab.trigger_modes.addItem(trigger_mode, trigger_mode)
            self._settings_tab.trigger_modes.currentTextChanged.connect(self.set_settings_params)
            if trigger_mode == self._spectrumlogic.trigger_mode:
                self._settings_tab.trigger_modes.setCurrentText(trigger_mode)

        self._temperature_widget = ScienDSpinBox()
        self._temperature_widget.setRange(-273.15, 500)
        self._temperature_widget.setValue(self._spectrumlogic.temperature_setpoint-273.15)
        self._temperature_widget.setSuffix('°C')
        self._temperature_widget.valueChanged.connect(self.set_settings_params)
        self._settings_tab.camera_cooler_layout.addWidget(self._temperature_widget)

        self._settings_tab.cooler_on.clicked.connect(self._manage_cooler_button)
        if self._spectrumlogic.cooler_status:
            self._settings_tab.cooler_on.setDown(True)
            self._settings_tab.cooler_on.setText("OFF")
            self._mw.cooler_on_label.setText("Cooler ON")
        else:
            self._settings_tab.cooler_on.setText("ON")
            self._mw.cooler_on_label.setText("Cooler OFF")
        self._mw.camera_temperature.setText("{}°C".format(round(self._spectrumlogic.camera_temperature-273.15, 2)))

        if not self._spectrumlogic.camera_constraints.has_shutter:
            self._settings_tab.shutter_modes.setEnabled(False)
            self._settings_tab.camera_gains.setCurrentText(self._spectrumlogic.shutter_state)

        self._center_wavelength_widget = ScienDSpinBox()
        self._center_wavelength_widget.setMinimum(0)
        self._center_wavelength_widget.setValue(self._spectrumlogic.center_wavelength)
        self._center_wavelength_widget.setSuffix("m")
        self._mw.center_wavelength.addWidget(self._center_wavelength_widget, 1)
        self._mw.go_to_wavelength.clicked.connect(self._manage_center_wavelength)
        self._mw.center_wavelength_current.setText("{:.2r}m".format(ScaledFloat(self._spectrumlogic.center_wavelength)))

        self._update_temperature_timer = QtCore.QTimer()
        self._update_temperature_timer.timeout.connect(self._update_temperature)

    def _activate_image_tab(self):

        for read_mode in self._spectrumlogic.camera_constraints.read_modes:
            if read_mode.name[:5] == "IMAGE":
                self._image_tab.read_modes.addItem(read_mode.name, read_mode.name)
                if read_mode == self._spectrumlogic.read_mode:
                    self._image_tab.read_modes.setCurrentText(read_mode.name)
        self._image_tab.read_modes.currentTextChanged.connect(self.set_image_params)

        for acquisition_mode in AcquisitionMode.__members__:
            self._image_tab.acquisition_modes.addItem(acquisition_mode, acquisition_mode)
            if acquisition_mode == self._spectrumlogic.acquisition_mode:
                self._image_tab.acquisition_modes.setCurrentText(acquisition_mode)
        self._image_tab.acquisition_modes.currentTextChanged.connect(self.set_image_params)

        self.image_exposure_time_widget = ScienDSpinBox()
        self.image_exposure_time_widget.setMinimum(0)
        self.image_exposure_time_widget.setValue(10)
        self.image_exposure_time_widget.setSuffix('s')
        self.image_exposure_time_widget.valueChanged.connect(self.set_image_params)
        self._image_tab.exposure_time_layout.addWidget(self.image_exposure_time_widget)

        for readout_speed in self._spectrumlogic.camera_constraints.readout_speeds:
            self._image_tab.readout_speed.addItem(str(readout_speed), readout_speed)
            if readout_speed == self._spectrumlogic.readout_speed:
                self._image_tab.readout_speed.setCurrentText(str(readout_speed))
        self._image_tab.readout_speed.currentTextChanged.connect(self.set_image_params)

        self._image_tab.save.clicked.connect(partial(self.save_data, 0))
        self._save_data_buttons.append(self._image_tab.save)
        self._image_tab.acquire_dark.clicked.connect(partial(self.start_dark_acquisition, 0))
        self._acquire_dark_buttons.append(self._image_tab.acquire_dark)
        self._image_tab.start_acquisition.clicked.connect(partial(self.start_acquisition, 0))
        self._start_acquisition_buttons.append(self._image_tab.start_acquisition)
        self._image_tab.stop_acquisition.clicked.connect(self.stop_acquisition)
        self._stop_acquisition_buttons.append(self._image_tab.stop_acquisition)

        self._image = pg.ImageItem(image=self._image_data, axisOrder='row-major')
        self._color_map = ColorScaleMagma()
        self._image.setLookupTable(self._color_map.lut)
        self._image_tab.graph.addItem(self._image)

        track_colors = ["r", "b", "y", "g"]
        for i in range(4):
            self._track_buttons[i].setCheckable(True)
            self._track_buttons[i].clicked.connect(partial(self._manage_track_buttons, i))
            if 2*i<len(self._active_tracks):
                top_pos = self._active_tracks[2*i]
                bottom_pos = self._active_tracks[2*i+1]
            else:
                top_pos = 0
                bottom_pos = 0
            top = pg.InfiniteLine(pos=top_pos, angle=0, movable=True, pen=track_colors[i])
            top.hide()
            bottom = pg.InfiniteLine(pos=bottom_pos, angle=0, movable=True, pen=track_colors[i])
            bottom.hide()
            self._track_selector.append((top, bottom))
            self._image_tab.graph.addItem(top)
            self._image_tab.graph.addItem(bottom)

    def _activate_alignement_tab(self):

        self.time_window_widget = ScienDSpinBox()
        self.time_window_widget.setMinimum(0)
        self.time_window_widget.setValue(30)
        self.time_window_widget.setSuffix('s')
        self.time_window_widget.valueChanged.connect(self._change_time_window)
        self._alignement_tab.time_window_layout.addWidget(self.time_window_widget,1)
        self._alignement_tab.clean.clicked.connect(self._clean_time_window)

        for read_mode in self._spectrumlogic.camera_constraints.read_modes:
            self._alignement_tab.read_modes.addItem(str(read_mode.name), read_mode.name)
            if read_mode == self._spectrumlogic.read_mode:
                self._alignement_tab.read_modes.setCurrentText(str(read_mode.name))
        self._alignement_tab.read_modes.currentTextChanged.connect(self.set_alignement_params)

        self.alignement_exposure_time_widget = ScienDSpinBox()
        self.alignement_exposure_time_widget.setMinimum(0)
        self.alignement_exposure_time_widget.setValue(self._spectrumlogic.exposure_time)
        self.alignement_exposure_time_widget.setSuffix('s')
        self.alignement_exposure_time_widget.valueChanged.connect(self.set_alignement_params)
        self._alignement_tab.exposure_time_layout.addWidget(self.alignement_exposure_time_widget)
        self._change_time_window()

        self._alignement_tab.start_acquisition.clicked.connect(partial(self.start_acquisition, 1))
        self._start_acquisition_buttons.append(self._alignement_tab.start_acquisition)
        self._alignement_tab.stop_acquisition.clicked.connect(self.stop_acquisition)
        self._stop_acquisition_buttons.append(self._alignement_tab.stop_acquisition)

        self._alignement_tab.graph.setLabel('left', 'photon counts', units='counts/s')
        self._alignement_tab.graph.setLabel('bottom', 'acquisition time', units='s')
        self._counter_plot = self._alignement_tab.graph.plot(self._counter_data[0], self._counter_data[1])

    def _activate_spectrum_tab(self):

        for read_mode in self._spectrumlogic.camera_constraints.read_modes:
            if read_mode.name[:5] != "IMAGE":
                self._spectrum_tab.read_modes.addItem(str(read_mode.name), read_mode.name)
                if read_mode == self._spectrumlogic.read_mode:
                    self._spectrum_tab.read_modes.setCurrentText(str(read_mode.name))
        self._spectrum_tab.read_modes.currentTextChanged.connect(self.set_spectrum_params)

        for acquisition_mode in AcquisitionMode.__members__:
            self._spectrum_tab.acquisition_modes.addItem(acquisition_mode, acquisition_mode)
            if acquisition_mode == self._spectrumlogic.acquisition_mode:
                self._spectrum_tab.acquisition_modes.setCurrentText(acquisition_mode)
        self._spectrum_tab.acquisition_modes.currentTextChanged.connect(self.set_spectrum_params)

        self.spectrum_exposure_time_widget = ScienDSpinBox()
        self.spectrum_exposure_time_widget.setMinimum(0)
        self.spectrum_exposure_time_widget.setValue(self._spectrumlogic.exposure_time)
        self.spectrum_exposure_time_widget.setSuffix('s')
        self.spectrum_exposure_time_widget.valueChanged.connect(self.set_spectrum_params)
        self._spectrum_tab.exposure_time_layout.addWidget(self.spectrum_exposure_time_widget)

        for readout_speed in self._spectrumlogic.camera_constraints.readout_speeds:
            self._spectrum_tab.readout_speed.addItem(str(readout_speed), readout_speed)
            if readout_speed == self._spectrumlogic.readout_speed:
                self._spectrum_tab.readout_speed.setCurrentText(str(readout_speed))
        self._spectrum_tab.read_modes.currentTextChanged.connect(self.set_spectrum_params)

        self._spectrum_tab.save.clicked.connect(partial(self.save_data, 1))
        self._save_data_buttons.append(self._image_tab.save)
        self._spectrum_tab.acquire_dark.clicked.connect(partial(self.start_dark_acquisition, 1))
        self._acquire_dark_buttons.append(self._spectrum_tab.acquire_dark)
        self._spectrum_tab.start_acquisition.clicked.connect(partial(self.start_acquisition, 2))
        self._start_acquisition_buttons.append(self._spectrum_tab.start_acquisition)
        self._spectrum_tab.stop_acquisition.clicked.connect(self.stop_acquisition)
        self._stop_acquisition_buttons.append(self._spectrum_tab.stop_acquisition)

        self._spectrum_tab.graph.setLabel('left', 'Photoluminescence', units='counts/s')
        self._spectrum_tab.graph.setLabel('bottom', 'wavelength', units='m')
        self._spectrum_plot = self._spectrum_tab.graph.plot(self._spectrum_data[0], self._spectrum_data[1])

    def update_settings(self):

        self._grating_index_buttons[self._spectrumlogic.grating_index].setDown(True)

        self._mw.input_slit_width_front.setValue(self._spectrumlogic.get_input_slit_width(port='front') * 1e6)
        self._mw.input_slit_width_side.setValue(self._spectrumlogic.get_input_slit_width(port='side') * 1e6)
        if self._spectrumlogic.input_port == "INPUT_SIDE":
            self._input_port_buttons[1].setDown(True)
        else:
            self._input_port_buttons[0].setDown(True)

        self._mw.output_slit_width_front.setValue(self._spectrumlogic.get_output_slit_width(port='front') * 1e6)
        self._mw.output_slit_width_side.setValue(self._spectrumlogic.get_output_slit_width(port='side') * 1e6)
        if self._spectrumlogic.output_port == "OUTPUT_SIDE":
            self._output_port_buttons[1].setDown(True)
        else:
            self._output_port_buttons[0].setDown(True)

        self._mw.wavelength_correction.setValue(self._spectrumlogic.wavelength_calibration * 1e9)

        self._camera_internal_gains = self._spectrumlogic.camera_constraints.internal_gains
        camera_gain_index = np.where([gain == self._spectrumlogic.camera_gain for gain in self._camera_internal_gains])
        self._camera_gain_buttons[camera_gain_index[0][0]].setDown(True)

        self._mw.trigger_modes.setCurrentText(self._spectrumlogic.trigger_mode)

        self._mw.camera_temperature_setpoint.setValue(self._spectrumlogic.temperature_setpoint)
        self._mw.cooler_on.setCheckable(True)
        self._mw.cooler_on.setDown(self._spectrumlogic.cooler_status)

        if self._spectrumlogic.camera_constraints.has_shutter:
            self._mw.shutter_modes.setCurrentText(self._spectrumlogic.shutter_state)
        else:
            self._mw.shutter_modes.setEnabled(False)

        self._mw.center_wavelength.setValue(self._spectrumlogic.center_wavelength * 1e9)

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

    def set_settings_params(self):

        self._spectrumlogic.wavelength_calibration = self._calibration_widget.value()
        self._spectrumlogic.camera_gain = self._settings_tab.camera_gains.currentData()
        self._spectrumlogic.trigger_mode = self._settings_tab.trigger_modes.currentData()
        self._spectrumlogic.temperature_setpoint = self._temperature_widget.value()+273.15
        self._spectrumlogic.shutter_state = self._settings_tab.shutter_modes.currentText()

    def set_image_params(self):

        self._spectrumlogic.acquisition_mode = self._image_tab.acquisition_modes.currentData()
        self._spectrumlogic.read_mode = self._image_tab.read_modes.currentData()
        self._spectrumlogic.exposure_time = self.image_exposure_time_widget.value()
        self._spectrumlogic.readout_speed = self._image_tab.readout_speed.currentData()

        self._spectrumlogic._update_acquisition_params()
        self._image_params = self._spectrumlogic.acquisition_params

    def set_alignement_params(self):

        self._spectrumlogic.acquisition_mode = "LIVE_SCAN"
        self._spectrumlogic.read_mode = self._alignement_tab.read_modes.currentData()
        self._spectrumlogic.exposure_time = self.alignement_exposure_time_widget.value()
        self._spectrumlogic.readout_speed = max(self._spectrumlogic.camera_constraints.readout_speeds)

        self._manage_tracks()
        self._change_time_window()

    def set_spectrum_params(self):

        self._spectrumlogic.acquisition_mode = self._spectrum_tab.acquisition_modes.currentData()
        self._spectrumlogic.read_mode = self._spectrum_tab.read_modes.currentData()
        self._spectrumlogic.exposure_time = self.spectrum_exposure_time_widget.value()
        self._spectrumlogic.readout_speed = self._spectrum_tab.readout_speed.currentData()

        self._manage_tracks()
        self._spectrumlogic._update_acquisition_params()
        self._spectrum_params = self._spectrumlogic.acquisition_params

    def start_dark_acquisition(self, index):

        self._manage_start_acquisition(index)

        self._spectrumlogic.acquisition_mode = "SINGLE_SCAN"
        self._spectrumlogic.shutter_state = "CLOSED"
        self._spectrumlogic.sigUpdateData.connect(partial(self._update_dark, index))

        if index == 0:
            self._spectrumlogic.read_modes = self._image_tab.read_modes.currentData()
            self._spectrumlogic.exposure_time = self.image_exposure_time_widget.value()
            self._spectrumlogic.readout_speed = self._image_tab.readout_speed.currentData()
        elif index == 1:
            self._spectrumlogic.read_modes = self._spectrum_tab.read_modes.currentData()
            self._spectrumlogic.exposure_time = self._spectrum_exposure_time.value()
            self._spectrumlogic.readout_speed = self._spectrum_tab.readout_speed.currentData()

        self._spectrumlogic.start_acquisition()

    def start_acquisition(self, index):

        self._manage_start_acquisition(index)
        self._spectrumlogic.sigUpdateData.connect(partial(self._update_data, index))

        if index==0:
            self.set_image_params()
        elif index==1:
            self.set_alignement_params()
        elif index==2:
            self.set_spectrum_params()

        self._spectrumlogic.start_acquisition()

    def stop_acquisition(self):

        self._spectrumlogic.stop_acquisition()
        self._spectrumlogic.sigUpdateData.disconnect()
        self._manage_stop_acquisition()

    def _manage_grating_buttons(self, index):

        for i in range(3):
            btn = self._grating_buttons[i]
            if i == index:
                btn.setDown(True)
                self._spectrumlogic.grating_index = i
            else:
                btn.setDown(False)
        self._mw.center_wavelength_current.setText("{:.2r}m".format(ScaledFloat(self._spectrumlogic.center_wavelength)))

    def _manage_port_buttons(self, index):
        for i in range(2):
            if index < 2:
                btn = self._input_port_buttons[i]
                if i == index:
                    btn.setDown(True)
                    self._spectrumlogic.input_port = self._spectrumlogic.spectro_constraints.ports[i].type
                else:
                    btn.setDown(False)
            elif index > 1:
                btn = self._output_port_buttons[i]
                if i+2 == index:
                    btn.setDown(True)
                    self._spectrumlogic.output_port = self._spectrumlogic.spectro_constraints.ports[i+2].type
                else:
                    btn.setDown(False)

    def _manage_cooler_button(self):
        cooler_on = not self._spectrumlogic.cooler_status
        self._spectrumlogic.cooler_status = cooler_on
        self._settings_tab.cooler_on.setDown(cooler_on)
        self._settings_tab.cooler_on.setText("ON" if not cooler_on else "OFF")
        self._mw.cooler_on_label.setText("Cooler {}".format("ON" if cooler_on else "OFF"))

    def _manage_center_wavelength(self):

        self._spectrumlogic.center_wavelength = self._center_wavelength_widget.value()
        self._mw.center_wavelength_current.setText("{:.2r}m".format(ScaledFloat(self._spectrumlogic.center_wavelength)))

    def _manage_tracks(self):

        self._active_tracks = []
        for i in range(4):
            if self._track_selector[i][0].isVisible():
                track = self._track_selector[i]
                self._active_tracks.append(int(track[0].getXPos()))
                self._active_tracks.append(int(track[1].getXPos()))
        self._spectrumlogic.active_tracks = self._active_tracks

    def _update_temperature(self):

        self._mw.camera_temperature.setText(str(round(self._spectrumlogic.camera_temperature-273.15, 2))+"°C")

    def _manage_track_buttons(self, index):

        track_selector = self._track_selector[index]
        if track_selector[0].isVisible():
            for selector in track_selector:
                selector.hide()
        else:
            for selector in track_selector:
                selector.setVisible(True)

    def _manage_start_acquisition(self, index):

        for i in range(3):
            self._start_acquisition_buttons[i].setEnabled(False)
            if i == index:
                self._stop_acquisition_buttons[i].setEnabled(True)
            else:
                self._stop_acquisition_buttons[i].setEnabled(False)
            if i < 2:
                self._acquire_dark_buttons[i].setEnabled(False)
                self._save_data_buttons[i].setEnabled(False)

    def _manage_stop_acquisition(self):

        for i in range(3):
            self._start_acquisition_buttons[i].setEnabled(True)
            self._stop_acquisition_buttons[i].setEnabled(False)
            if i<2:
                self._acquire_dark_buttons[i].setEnabled(True)
                self._save_data_buttons[i].setEnabled(True)

    def _clean_time_window(self):

        self._counter_data = np.zeros((2, 1000))
        self._change_time_window()

    def _change_time_window(self):

        time_window = self.time_window_widget.value()
        exposure_time = self.alignement_exposure_time_widget.value()
        number_points = int(time_window / exposure_time)
        x = np.linspace(self._counter_data[0, -1] - time_window, self._counter_data[0, -1], number_points)
        if self._counter_data.shape[1] < number_points:
            y = np.zeros(number_points)
            y[-self._counter_data.shape[1]:] = self._counter_data[1]
        else:
            y = self._counter_data[1,-number_points:]
        self._counter_data = np.array([x, y])
        self._alignement_tab.graph.setRange(xRange=(x[-1]-self.time_window_widget.value(), x[-1]))

    def _update_data(self, index):

        data = [self._spectrumlogic.acquired_data]

        if index == 0:
            if self._image_dark.shape == data[-1].shape:
                self._image_data = data - self._image_dark
            else:
                self._image_data = data
            self._image.setImage(image=self._image_data[-1])
        elif index == 1:
            counts = sum([sum(track) for track in data])
            x = self._counter_data[0]+self._spectrumlogic.exposure_time
            y = np.append(self._counter_data[1][1:], counts)
            self._counter_data = np.array([x, y])
            self._alignement_tab.graph.setRange(xRange=(x[-1]-self.time_window_widget.value(), x[-1]))
            self._counter_plot.setData(x, y)
        elif index == 2:
            x = self._spectrumlogic.wavelength_spectrum
            if len(self._image_dark) == len(data[-1]):
                y = data[-1] - self._spectrum_dark
            else:
                y = data[-1]
            self._spectrum_data = np.array([x, y])
            self._spectrum_plot.setData(x, y)

        if not self._spectrumlogic.module_state() == 'locked':
            self._spectrumlogic.sigUpdateData.disconnect()
            self._manage_stop_acquisition()

    def _update_dark(self, index):

        dark = self._spectrumlogic.acquired_data

        if index == 0:
            self._image_dark = dark
            self._image_tab.dark_acquired_msg.setText("Dark Acquired")
        elif index == 1:
            self._spectrum_dark = dark
            self._spectrum_tab.dark_acquired_msg.setText("Dark Acquired")

        self._spectrumlogic.sigUpdateData.disconnect()
        self._manage_stop_acquisition()
        self._spectrumlogic.shutter_state = self._settings_tab.shutter_modes.currentText()

    def save_data(self, index):

        filepath = self.savelogic().get_path_for_module(module_name='spectrometer')

        if index==0:
            data = {'data': np.array(self._image_data).flatten()}
            self.savelogic().save_data(data, filepath=filepath, parameters=self._image_params)
        elif index==1:
            data = {'data': np.array(self._spectrum_data).flatten()}
            self.savelogic().save_data(data, filepath=filepath, parameters=self._spectrum_params)