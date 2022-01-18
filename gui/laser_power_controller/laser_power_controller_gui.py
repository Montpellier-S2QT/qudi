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
import os
import math
import pyqtgraph as pg

from core.connector import Connector
from core.mapper import Mapper, Converter
from gui.guibase import GUIBase
from gui.colordefs import QudiPalettePale as palette
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic



class MainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'main.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class LaserWidget(QtWidgets.QWidget):
    """ Create a laser widget based on the *.ui file. """
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'widget.ui')
        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)


class ConfigureWindow(QtWidgets.QMainWindow):
    """ Create the configure window based on the *.ui file. """
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'configure.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


def find_nearest_index(array, value):
    """ Find the index of the closest value in an array. """
    idx = np.searchsorted(array, value, side="left")
    if idx > 0 and (idx == len(array) or math.fabs(value - array[idx-1]) < math.fabs(value - array[idx])):
        return idx-1
    else:
        return idx


class Main(GUIBase):
    """ GUI module to control one or multiple laser power

     This module can be connected to one or multiple logic modules

     power_controller_gui:
        module.Class: 'laser_power_controller.laser_power_controller_gui.Main'
        connect:
            logic: 'green_power_controller'
     """

    logic = Connector(interface='LaserPowerController')
    logic2 = Connector(interface='LaserPowerController', optional=True)
    logic3 = Connector(interface='LaserPowerController', optional=True)
    logic4 = Connector(interface='LaserPowerController', optional=True)
    logic5 = Connector(interface='LaserPowerController', optional=True)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self._mw = None
        self.widgets = []
        self.mapper = None

    def on_activate(self):
        """ Definition and initialisation of the GUI """

        self.mapper = Mapper()

        self._mw = MainWindow()
        logic_modules = self.get_logic_modules()
        for logic in logic_modules:
            self.initiate_logic(logic())

    def on_deactivate(self):
        """ Deactivate the module properly. """
        self.mapper.clear_mapping()
        self._mw.close()
        self._mw = None
        for widget in self.widgets:
            if hasattr(widget, 'configure_window') and widget.configure_window is not None:
                widget.configure_window.close()
        self.widgets = []

    def initiate_logic(self, logic):
        """ Initiate a logic module widget. """
        widget = LaserWidget()
        widget.color_label.setStyleSheet("QLabel{{background-color : {}}}".format(logic.color))
        widget.label.setText(logic.name)
        self.update_power_range_logic_to_gui(logic, widget)
        widget.checkBox.setEnabled(logic.power_switch.is_connected)

        self.mapper.add_mapping(widget=widget.checkBox, model=logic,
                                model_getter='get_switch_state',
                                model_property_notifier='sigNewSwitchState',
                                model_setter='set_switch_state',
                                widget_property_notifier='stateChanged')

        self.mapper.add_mapping(widget=widget.powerSpinBox, model=logic,
                                model_getter='get_power_setpoint',
                                model_property_notifier='sigNewPower',
                                model_setter='set_power',
                                widget_property_notifier='editingFinished')

        class SliderConverter(Converter):
            def widget_to_model(self, data):
                return widget.slider_powers[data]

            def model_to_widget(self, data):
                return int(find_nearest_index(widget.slider_powers, data))

        self.mapper.add_mapping(widget=widget.slider, model=logic,
                                model_getter=logic.get_power_setpoint,
                                model_property_notifier=logic.sigNewPower,
                                model_setter=logic.set_power,
                                widget_property_notifier=widget.slider.valueChanged,
                                converter=SliderConverter())

        logic.sigNewPowerRange.connect(lambda: self.update_power_range_logic_to_gui(logic, widget))
        widget.configureButton.clicked.connect(lambda: self.open_configure_window(logic, widget))

        self._mw.verticalLayout.addWidget(widget)
        self.widgets.append(widget)
        widget.configure_window = None


    def update_power_range_logic_to_gui(self, logic, widget):
        """ Update a widget slider range from logic value. """
        widget.slider_powers = self._compute_slider_powers(logic.power_min, logic.power_max)
        widget.slider.setMaximum(len(widget.slider_powers) - 1)

    def show(self):
        """ Make window visible and put it above all other windows. """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def _compute_slider_powers(self, mini, maxi, decimal=1, decade=4):
        """ Helper method to compute human friendly rounded values to match to slider position

        For example, for a maxi of 1.473, a mini of 0 and just 2 decades, the result is the array :
         array(   [0.   , 0.1  , 0.11 , 0.12 , 0.13 , 0.14 , 0.15 , 0.16 , 0.17 ,
                   0.18 , 0.19 , 0.2  , 0.21 , 0.22 , 0.23 , 0.24 , 0.25 , 0.26 ,
                   0.27 , 0.28 , 0.29 , 0.3  , 0.31 , 0.32 , 0.33 , 0.34 , 0.35 ,
                   0.36 , 0.37 , 0.38 , 0.39 , 0.4  , 0.41 , 0.42 , 0.43 , 0.44 ,
                   0.45 , 0.46 , 0.47 , 0.48 , 0.49 , 0.5  , 0.51 , 0.52 , 0.53 ,
                   0.54 , 0.55 , 0.56 , 0.57 , 0.58 , 0.59 , 0.6  , 0.61 , 0.62 ,
                   0.63 , 0.64 , 0.65 , 0.66 , 0.67 , 0.68 , 0.69 , 0.7  , 0.71 ,
                   0.72 , 0.73 , 0.74 , 0.75 , 0.76 , 0.77 , 0.78 , 0.79 , 0.8  ,
                   0.81 , 0.82 , 0.83 , 0.84 , 0.85 , 0.86 , 0.87 , 0.88 , 0.89 ,
                   1.   , 1.1  , 1.2  , 1.3  , 1.4  , 1.473])

        """
        if mini == maxi:
            return np.array([0])

        current = maxi
        finals = [current]
        for i in range(decade):
            if current < mini:
                break
            power = np.floor(np.log10(current))
            number = int(current / 10 ** power * 10 ** decimal) / 10 ** decimal
            while number >= 1:
                finals.append(number * 10 ** power)
                number -= 1 / 10 ** decimal
            finals.append(number * 10 ** power)
            current = finals[-1] - 1 / 10 ** decimal * 10 ** power

        finals = np.array(finals)[:-1]
        finals = finals[finals > mini]
        finals = np.append(finals, mini)
        finals = np.flip(finals, axis=0)
        return finals

    def get_logic_modules(self):
        """ Get a list of the connected logic modules """
        result = [self.logic]
        for logic in [self.logic2, self.logic3, self.logic4, self.logic5]:
            if logic.is_connected:
                result.append(logic)
        return result

    # Configure window methods
    def open_configure_window(self, logic, widget):
        """ Create the configure window """

        if widget.configure_window is None:
            window = ConfigureWindow()

            window.runAction.triggered.connect(logic.start_calibration)
            window.abortAction.triggered.connect(logic.abort_calibration)

            window.resolution.setValue(logic.resolution)
            window.delay.setValue(logic.delay)

            window.resolution.editingFinished.connect(lambda: logic.set_resolution(window.resolution.value()))
            window.delay.editingFinished.connect(lambda: logic.set_delay(window.delay.value()))

            widget.curve = pg.PlotDataItem(logic.calibration_x, logic.calibration_y,
                                          pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                          symbol='o',
                                          symbolPen=palette.c1,
                                          symbolBrush=palette.c1,
                                          symbolSize=7)

            window.plotWidget.addItem(widget.curve)
            window.plotWidget.setLabel(axis='left', text='Power', units='W')
            window.plotWidget.setLabel(axis='bottom', text='Control', units='')
            window.plotWidget.showGrid(x=True, y=True, alpha=0.8)

            logic.sigDoNextPoint.connect(lambda: self.update_calibration_data(logic, widget))
            logic.sigDoNextPoint.connect(lambda: self.update_progress(logic, widget))

            logic.sigModuleStateChanged.connect(lambda: self.update_module_state(logic, widget))

            widget.configure_window = window
            self.update_progress(logic, widget)
            self.update_module_state(logic, widget)
        else:
            widget.configure_window.show()

    def update_calibration_data(self, logic, widget):
        """ Update the plot with logic's data """
        if len(logic.calibration_y) > 0:
            x, y = logic.calibration_x, logic.calibration_y
            mask = ~ np.isnan(y)
            x, y = x[mask], y[mask]
        else:
            x, y = [], []
        widget.curve.setData(x, y)

    def update_progress(self, logic, widget):
        """ Update the progress bar to show evolution """
        if len(logic.calibration_x) == 0:
            progress = 0
        else:
            progress = 1 - np.isnan(logic.calibration_y).sum() / len(logic.calibration_y)
            progress = np.round(progress*100)
        widget.configure_window.progressBar.setValue(progress)

    def update_module_state(self, logic, widget):
        """ Update action buttons depending on module state """
        running = logic.module_state() == 'running'
        widget.configure_window.runAction.setEnabled(not running)
        widget.configure_window.abortAction.setEnabled(running)
        widget.configure_window.saveAction.setEnabled(not running)
