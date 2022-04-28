# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI for scanning NV microscopy.

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

import numpy as np
import pyqtgraph as pg
from collections import OrderedDict

from core.module import Connector
from core.statusvariable import StatusVar
from core.mapper import Mapper, Converter
from gui.guibase import GUIBase
from gui.colordefs import QudiPalettePale as palette

#from gui.fitsettings import FitSettingsDialog
from qtwidgets.scientific_spinbox import ScienDSpinBox
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic


class NVScanningMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_nv_scanning_maingui.ui')

        # Load it
        super(NVScanningMainWindow, self).__init__()

        uic.loadUi(ui_file, self)
        self.show()


class NVScanningGui(GUIBase):
    """ This is the GUI Class for scanning NV microscopy.
    """

    _modclass = 'NVScanningGui'
    _modtype = 'gui'

    # declare connectors
    microscopelogic = Connector(interface='NVMicroscopeLogic')
    # odmrlogic = Connector(interface='ODMRLogic') # needed ?

    # status variables
    max_scanner = StatusVar('max_scanner', default=30e-6)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        
    def on_activate(self):
        """ Definition, configuration and initialization of the magnetometer
        GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """
        # create the main window 
        self._mw = NVScanningMainWindow()
        
        # create the mapper to handle the parameter values
        self.mapper = Mapper()

        # connect a few things
        self._mw.actionChange_scanner_range.triggered.connect(self.change_max_scanner)

        self.initiate_general_params_dock()
        self.initiate_mapping_dock()
        self.initiate_XYscanner_dock()

        self.spec_params_widgets = {}
        
        # Show the main window
        self.show()
        return


    def on_deactivate(self):
        """ Reverse steps of activation.
        """
        self.mapper.clear_mapping()
        self._mw.close()
        return


    def show(self):
        """ Make window visible and put it above all other windows. 
        """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()
        return


    def initiate_general_params_dock(self):
        """ Connection of the input widgets in the mapping parameters dockwidget."""
        
        # connect the inputs
        self.mapper.add_mapping(widget=self._mw.file_tag_lineEdit,
                                model=self.microscopelogic(),
                                model_getter='handle_file_tag',
                                model_property_notifier='sigFileTagChanged',
                                model_setter='handle_file_tag')

        self._mw.refresh_procedures_PushButton.clicked.connect(
            self.microscopelogic().update_scanning_procedures)
        self._mw.procedures_ComboBox.currentTextChanged.connect(
            self.microscopelogic().change_current_procedure)

        self.microscopelogic().sigUpdateProcedureList.connect(self.update_procedure_combobox)
        return
        
    
    def initiate_mapping_dock(self):
        """ Connection of the input widgets in the mapping parameters dockwidget."""

        # connect the inputs
        self.mapper.add_mapping(widget=self._mw.x_res_SpinBox,
                                model=self.microscopelogic(),
                                model_getter='handle_x_res',
                                model_property_notifier='sigXResChanged',
                                model_setter='handle_x_res')
        
        self.mapper.add_mapping(widget=self._mw.y_res_SpinBox,
                                model=self.microscopelogic(),
                                model_getter='handle_y_res',
                                model_property_notifier='sigYResChanged',
                                model_setter='handle_y_res')

        self.mapper.add_mapping(widget=self._mw.rs_DoubleSpinBox,
                                model=self.microscopelogic(),
                                model_getter='handle_rs',
                                model_property_notifier='sigRSChanged',
                                model_setter='handle_rs')
        self._mw.rs_DoubleSpinBox.setMinimum(10e-9)


        # connect the starting points radiobuttons
        self._mw.StartPointButtonGroup.buttonClicked.connect(
            lambda button: self.microscopelogic().handle_starting_point(button.text()))
        self.microscopelogic().sigStartPointChanged.connect(
            lambda sp: getattr(self._mw, sp+'_radioButton').setChecked(True))
        
        # connect the time displays
        self.microscopelogic().sigUpdateRemTime.connect(
            self._mw.display_remaining_time.setText)
        self.microscopelogic().sigUpdateDuration.connect(
            self._mw.display_scan_duration.setText)

        # creating a graph item to display the plot area
        # get the coords
        self.scan_area_corners = self.microscopelogic().scan_area_corners()
        # close the loop
        self.scan_area_corners = np.append(self.scan_area_corners,
                                           [[self.scan_area_corners[0, 0], self.scan_area_corners[0, 1]]],
                                           axis=0)
        self.scan_area_plot = pg.PlotDataItem(self.scan_area_corners, pen=pg.mkPen(palette.c1), symbol='o',
                                              symbolPen=palette.c1, symbolBrush=palette.c1, symbolSize=5)
        self.start_plot = pg.PlotDataItem(x=np.array([self.microscopelogic().starting_point_coords()[0]]),
                                          y=np.array([self.microscopelogic().starting_point_coords()[1]]),
                                          pen=pg.mkPen(palette.c2), symbol='o',
                                          symbolPen=palette.c2, symbolBrush=palette.c2, symbolSize=7)
        # adding graph item to the view box
        self._mw.scanAreaView.addItem(self.scan_area_plot)
        self._mw.scanAreaView.addItem(self.start_plot)
        self._mw.scanAreaView.setLabel('bottom', 'X position', units='m')
        self._mw.scanAreaView.setLabel('left', 'Y position', units='m')
        self._mw.scanAreaView.setAspectLocked(lock=True, ratio=1)
        #self._mw.scanAreaView.setRange(xRange=(0, self.max_scanner),
        #                               yRange=(0, self.max_scanner))

        self.microscopelogic().sigRefreshScanArea.connect(self.update_scan_area_plot)
        return
            

    def initiate_XYscanner_dock(self):
        """ Connection of the input widgets in the XY scanner parameters dockwidget."""

        # connects the inputs
        self.mapper.add_mapping(widget=self._mw.angle_DoubleSpinBox,
                                model=self.microscopelogic(),
                                model_getter='handle_angle',
                                model_property_notifier='sigAngleChanged',
                                model_setter='handle_angle')

        self.mapper.add_mapping(widget=self._mw.width_DoubleSpinBox,
                                model=self.microscopelogic(),
                                model_getter='handle_scan_width',
                                model_property_notifier='sigScanWidthChanged',
                                model_setter='handle_scan_width')

        self.mapper.add_mapping(widget=self._mw.height_DoubleSpinBox,
                                model=self.microscopelogic(),
                                model_getter='handle_scan_height',
                                model_property_notifier='sigScanHeightChanged',
                                model_setter='handle_scan_height')

        self.mapper.add_mapping(widget=self._mw.x_position_DoubleSpinBox,
                                model=self.microscopelogic(),
                                model_getter='handle_x_center',
                                model_property_notifier='sigXCenterChanged',
                                model_setter='handle_x_center')

        self.mapper.add_mapping(widget=self._mw.y_position_DoubleSpinBox,
                                model=self.microscopelogic(),
                                model_getter='handle_y_center',
                                model_property_notifier='sigYCenterChanged',
                                model_setter='handle_y_center')


        self._mw.moveto_pushButton.clicked.connect(self.moveto)
        self._mw.moveto_start_pushButton.clicked.connect(self.moveto_start)
        self._mw.moveto_zero_pushButton.clicked.connect(self.moveto_zero)

        return

    
    def create_spec_params_widgets(self, spec_params_values):
        """ Gets the list of parameters and creates the corresponding widgets."""
        
        grid = self._mw.paramsGridLayout
        self.spec_params_values = spec_params_values

        # First purge the dict
        for k in self.spec_params_widgets.keys():
            self.spec_params_widgets[k][0].hide()
            self.spec_params_widgets[k][1].hide()
        self.spec_params_widgets = OrderedDict()

        # create all the widgets
        for param in self.spec_params_values.keys():
            if isinstance(self.spec_params_values[param][0], str):
                input_widget = QtWidgets.QLineEdit()
                input_widget.setText(spec_params_values[param][0])
            elif isinstance(self.spec_params_values[param][0], float):
                input_widget = ScienDSpinBox()
                input_widget.setValue(spec_params_values[param][0])
                if not spec_params_values[param][1]=='':
                    input_widget.setSuffix(spec_params_values[param][1])
            elif isinstance(self.spec_params_values[param][0], bool):
                input_widget = QtWidgets.QCheckBox()
                input_widget.setText('')
                input_widget.setChecked(self.spec_params_values[param][0])
            elif isinstance(self.spec_params_values[param][0], int):
                input_widget = QtWidgets.QSpinBox()
                input_widget.setValue(spec_params_values[param][0])
            else:
                self.log.warning("Unknown parameter type encountered!")

            # TODO: mapping, with a converter
            
            self.spec_params_widgets[param] = (QtWidgets.QLabel(str(param)), input_widget)
            last_row = grid.rowCount() +1
            grid.addWidget(self.spec_params_widgets[param][0], last_row, 1)
            grid.addWidget(self.spec_params_widgets[param][1], last_row, 2)

        return


    def update_scan_area_plot(self):
        """ Update the sketch of the scan region."""
        
        # get the coords
        self.scan_area_corners = self.microscopelogic().scan_area_corners()
        # close the loop
        self.scan_area_corners = np.append(self.scan_area_corners,
                                           [[self.scan_area_corners[0, 0], self.scan_area_corners[0, 1]]],
                                           axis=0)
        
        self.scan_area_plot.setData(self.scan_area_corners)
        self.start_plot.setData(x=np.array([self.microscopelogic().starting_point_coords()[0]]),
                                y=np.array([self.microscopelogic().starting_point_coords()[1]]))
        print(self.scan_area_corners*1e6)
        return


    def update_procedure_combobox(self, proc_list):
        """ Updates the list of available scanning procedures."""
        self._mw.procedures_ComboBox.clear()
        self._mw.procedures_ComboBox.addItems(proc_list)
        return
    
    
    def change_max_scanner(self):
        """
        Opens a dialog to input a new scanner range.
        """
        dialog = QtGui.QInputDialog()
        value, ok = dialog.getDouble(self._mw,"Scanner range",
                                     "New maximum scanner range (in µm):",
                                     self.max_scanner*1e6, 0, 100, 3)
        if value and ok:
            self.max_scanner = value*1e-6
            x = self._mw.x_position_DoubleSpinBox.value()
            y = self._mw.y_position_DoubleSpinBox.value()
            self._mw.x_position_DoubleSpinBox.setMaximum(self.max_scanner)
            self._mw.y_position_DoubleSpinBox.setMaximum(self.max_scanner)
            self._mw.width_DoubleSpinBox.setMaximum(self.max_scanner)
            self._mw.height_DoubleSpinBox.setMaximum(self.max_scanner)
            self._mw.x_position_DoubleSpinBox.setValue(x)
            self._mw.y_position_DoubleSpinBox.setValue(y)
            self.log.info("Changed max scanner range.")
        return
    

    def moveto(self):
        """ Action when the MoveTo button is pushed.
        NOT FINISHED
        """
        x = self._mw.x_position_DoubleSpinBox.value()
        y = self._mw.y_position_DoubleSpinBox.value()
        return


    def moveto_start(self):
        """ Action when the MoveTo_start button is pushed.
        NOT FINISHED
        """
        x = self._mw.x_position_DoubleSpinBox.value()
        y = self._mw.y_position_DoubleSpinBox.value()
        w = self._mw.width_DoubleSpinBox.value()
        h = self._mw.height_DoubleSpinBox.value()
        return


    def moveto_zero(self):
        """ Action when the MoveTo_zero button is pushed.
        NOT FINISHED
        """
        return
