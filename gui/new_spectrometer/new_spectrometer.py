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
        self._output_port_buttons = [self._mw.output_front, self._mw.output_side]
        self._camera_gain_buttons = [self._mw.gain_1, self._mw.gain_2, self._mw.gain_3]

        self._grating_index_buttons[self._spectrumlogic.grating_index].isDown()

        if self._spectrumlogic.input_port == "INPUT_SIDE":
            self._input_port_buttons[1].isDown()
        else:
            self._input_port_buttons[0].isDown()

        if self._spectrumlogic.output_port == "OUTPUT_SIDE":
            self._output_port_buttons[1].isDown()
        else:
            self._output_port_buttons[0].isDown()

        self._camera_internal_gains = self._spectrumlogic.camera_constraints.internal_gains
        camera_gain_index = np.where(self._camera_internal_gains[self._camera_internal_gains == self._spectrumlogic.camera_gain])
        self._camera_gain_buttons[camera_gain_index[0][0]].isDown()

        # Connect singals
        self._mw.grating_1.clicked.connect(self.manage_grating_index_buttons)
        self._mw.grating_2.clicked.connect(self.manage_grating_index_buttons)
        self._mw.grating_3.clicked.connect(self.manage_grating_index_buttons)

        self._mw.input_front.clicked.connect(self.manage_input_port_buttons)
        self._mw.input_side.clicked.connect(self.manage_input_port_buttons)

        self._mw.output_front.clicked.connect(self.manage_output_port_buttons)
        self._mw.output_side.clicked.connect(self.manage_output_port_buttons)

        self._mw.gain_1.clicked.connect(self.manage_camera_gain_buttons)
        self._mw.gain_2.clicked.connect(self.manage_camera_gain_buttons)
        self._mw.gain_3.clicked.connect(self.manage_camera_gain_buttons)

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

    def update_settings(self):

        grating_index = np.where([button.isDown() for button in self._grating_index_buttons])[0]
        input_port_index = np.where([button.isDown() for button in self._input_port_buttons])[0]
        output_port_index = np.where([button.isDown() for button in self._output_port_buttons])[0]
        camera_gain_index = np.where([button.isDown() for button in self._camera_gain_buttons])[0]

        self._spectrumlogic.grating_index = grating_index
        self._spectrumlogic.input_port = self._spectrumlogic.spectro_constraints.ports[input_port_index]
        self._spectrumlogic.output_port = self._spectrumlogic.spectro_constraints.ports[2+output_port_index]
        self._spectrumlogic.camera_gain = self._spectrumlogic.camera_constraints.internal_gains[camera_gain_index]


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

