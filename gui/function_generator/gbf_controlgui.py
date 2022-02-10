# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI for iso-b scan.

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

from interface.gbf_interface import Waveform, Mode, Triggersource

from core.util import units
from core.module import Connector
from gui.guibase import GUIBase
#from gui.guiutils import ColorBar, CrossLine, CrossROI
from gui.fitsettings import FitSettingsDialog
import gui.colordefs as cdef
from gui.colordefs import QudiPalettePale as palette
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic

class GBFcontrolwindow(QtWidgets.QMainWindow):
    """ The main window to control the gbf.
    """
    
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_gbf_control.ui')

        # Load it
        super(GBFcontrolwindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class GBFcontrolGui(GUIBase):
    """ This is the GUI class to control the gbf.
    """
    
    _modclass = 'gbfcontrolgui'
    _modtype = 'gui'

    # declare connectors
    gbflogic = Connector(interface='GBFlogic')

    
    # declare signals
    sigStartRamp = QtCore.Signal(dict)
    sigStopRamp = QtCore.Signal()
    sigSetParameters = QtCore.Signal(dict)
    sigGetParameters = QtCore.Signal()
    sigSetChannel = QtCore.Signal(str)
    sigSetOutput = QtCore.Signal(str)
    sigSetWaveform = QtCore.Signal(str)
    sigSetMode = QtCore.Signal(str)
    sigSetTriggerSource = QtCore.Signal(str)
    sigDoFit =  QtCore.Signal()

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        
    def on_activate(self):
        """ Definition, configuration and initialisation of the gbf controler.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """
        
        self._gbf_logic = self.gbflogic()
        
        ########################################################################
        #                      General configurations                          #
        ########################################################################
        
        # use the inherited class 'Ui_CryoMonitoringGuiUI' to create now the GUI element:
        self._mw = GBFcontrolwindow()
        
        self._mw.comboBox_channel.addItems(["1", "2"])
        self._mw.comboBox_output.addItems(["OFF", "ON"])
        self._mw.comboBox_waveform.addItems(Waveform._member_names_)
        self._mw.comboBox_mode.addItems(Mode._member_names_)
        self._mw.comboBox_trigger_source.addItems(Triggersource._member_names_)


        ########################################################################
        #                          Connect signals                             #
        ########################################################################
        
        # interaction with user
        self._mw.pushButton_go.clicked.connect(self.set_gbf_parameters)
        self._mw.pushButton_get_status.clicked.connect(self.get_gbf_parameters)
        self._mw.pushButton_ramp.clicked.connect(self.do_the_ramp)
        self._mw.pushButton_ramp_stop.clicked.connect(self.stop_ramp_measurement)
        self._mw.pushButton_fit_electric_field.clicked.connect(self.do_fit)

        self._mw.comboBox_output.currentIndexChanged.connect(self.toggle_output)        
        self._mw.comboBox_channel.currentIndexChanged.connect(self.set_channel)
        self._mw.comboBox_waveform.currentIndexChanged.connect(self.set_waveform)
        self._mw.comboBox_mode.currentIndexChanged.connect(self.set_mode)
        self._mw.comboBox_trigger_source.currentIndexChanged.connect(self.set_trigger)
        
        self._mw.actionSave.triggered.connect(self.save_routine)
        
        # signals from logic
        self._gbf_logic.sigCurrentParameters.connect(self.display_status)
        self._gbf_logic.sigUpdatedFitParameters.connect(self.display_fit)
        self._gbf_logic.sigUpdatedFitPlot.connect(self.refresh_plot_fit)
        self._gbf_logic.sigMeasurementStopped.connect(self.enable_buttons)
        self._gbf_logic.sigUpdatedEfield.connect(self.refresh_plot_Efield)
        
        # signals to logic
        self.sigSetOutput.connect(self._gbf_logic.toggle_output)
        self.sigSetChannel.connect(self._gbf_logic.set_channel)
        self.sigSetWaveform.connect(self._gbf_logic.set_waveform)
        self.sigSetMode.connect(self._gbf_logic.set_mode)
        self.sigSetTriggerSource.connect(self._gbf_logic.set_trigger)
        self.sigSetParameters.connect(self._gbf_logic.set_gbf_parameters)
        self.sigGetParameters.connect(self._gbf_logic.get_gbf_parameters)
        self.sigStartRamp.connect(self._gbf_logic.do_the_ramp)
        self.sigStopRamp.connect(self._gbf_logic.stop_ramp_measurement)
        self.sigDoFit.connect(self._gbf_logic.do_fit)
        
        #Initialisation of the burst mode
        self.set_mode()
        self.set_trigger()
        self.set_waveform()
        
        #Initialisation of coherent value
        self._mw.doubleSpinBox_amplitude.setValue(0.001)
        self._mw.doubleSpinBox_frequency.setValue(100)
        self._mw.spinBox_numberofcycles.setValue(1)
        self.set_gbf_parameters()

        self._mw.doubleSpinBox_pi_pulse.setValue(1)        
        self._mw.doubleSpinBox_evolution_time.setValue(3)
        self._mw.doubleSpinBox_mw_power.setValue(20)
        self._mw.doubleSpinBox_mw_frequency.setValue(2.87)
        self._mw.doubleSpinBox_max_amplitude.setValue(1.5)
        self._mw.doubleSpinBox_min_amplitude.setValue(0.001)
        self._mw.doubleSpinBox_step_amplitude.setValue(0.1)
        self._mw.doubleSpinBox_measurement_time.setValue(30)

        ########################################################################
        #                          Load displays                               #
        ########################################################################
        # self._mw.spinBox_nb_pts.setValue(20)
        # self._mw.doubleSpinBox_theta_for_phi_sweep.setValue(90)
        # self._mw.doubleSpinBox_phi_for_theta_sweep.setValue(0)
        
        self.Efield_plot = pg.PlotDataItem(self._gbf_logic.measured_data[:,0],
                                              self._gbf_logic.measured_data[:,1],
                                              pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                              symbol='o',
                                              symbolPen=palette.c1,
                                              symbolBrush=palette.c1,
                                              symbolSize=7)
        self.Efield_plot_error = pg.ErrorBarItem(x=self._gbf_logic.measured_data[:,0],
                                               y=self._gbf_logic.measured_data[:,1],
                                               height=self._gbf_logic.measured_data[:,2],
                                               top=0, bottom=0, pen=palette.c1)
        self.Efield_plot_fit = pg.PlotDataItem(self._gbf_logic.measured_data[:,0],
                                                  self._gbf_logic.Efield_fit,
                                                  pen=pg.mkPen(palette.c2))
        
        self._mw.electric_field_ViewWidget.addItem(self.Efield_plot)
        self._mw.electric_field_ViewWidget.addItem(self.Efield_plot_error)
        self._mw.electric_field_ViewWidget.addItem(self.Efield_plot_fit)
        self._mw.electric_field_ViewWidget.setLabel('bottom', 'Amplitude' , units='V')
        self._mw.electric_field_ViewWidget.setLabel('left', 'Electric field Signal', units='')
        #  # to get the fitting models with the correct format
        # self._fsd = FitSettingsDialog(self._orientation_logic._odmr_logic.fc)
        # self._fsd.applySettings()

        # Show the main window
        self.show()
        
        return
    

    def on_deactivate(self):
        """ Reverse steps of activation.

        @return (int): error code (0:OK, -1:error)
        """    
        
        if self._gbf_logic.check_before_closing():
            self._mw.close()
            return 0
        else:
            self.log.warning("I think you should turn off the output")
            messagebox = QtGui.QMessageBox()
            messagebox.setText("Please turn off the output !")
            messagebox.setStandardButtons(QtGui.QMessageBox.Ok)
            messagebox.setWindowTitle("Warning")
            messagebox.exec_()
            return -1
    
    
    def show(self):
        """ Make window visible and put it above all other windows. 
        """
        
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()
        
        return

    def disable_buttons(self):
        """ Avoid the user to do annoying things during the sweeps.
        """
        
        self._mw.doubleSpinBox_amplitude.setEnabled(False)
        self._mw.doubleSpinBox_frequency.setEnabled(False)
        self._mw.doubleSpinBox_pi_pulse.setEnabled(False)
        self._mw.doubleSpinBox_evolution_time.setEnabled(False)
        self._mw.doubleSpinBox_mw_power.setEnabled(False)
        self._mw.doubleSpinBox_mw_frequency.setEnabled(False)
        self._mw.doubleSpinBox_max_amplitude.setEnabled(False)
        self._mw.doubleSpinBox_min_amplitude.setEnabled(False)
        self._mw.doubleSpinBox_step_amplitude.setEnabled(False)
        self._mw.doubleSpinBox_measurement_time.setEnabled(False) 
        
        self._mw.spinBox_numberofcycles.setEnabled(False)
        
        self._mw.comboBox_waveform.setEnabled(False)
        self._mw.comboBox_mode.setEnabled(False)
        self._mw.comboBox_trigger_source.setEnabled(False)
        self._mw.comboBox_output.setEnabled(False)
        self._mw.comboBox_channel.setEnabled(False)        
        
        self._mw.pushButton_go.setEnabled(False)
        self._mw.pushButton_ramp.setEnabled(False)
        self._mw.pushButton_get_status.setEnabled(False)
        
        return


    def enable_buttons(self):
        """ Re-enable the interaction with the user.
        """
        
        self._mw.doubleSpinBox_amplitude.setEnabled(True)
        self._mw.doubleSpinBox_frequency.setEnabled(True)
        self._mw.doubleSpinBox_pi_pulse.setEnabled(True)
        self._mw.doubleSpinBox_evolution_time.setEnabled(True)
        self._mw.doubleSpinBox_mw_power.setEnabled(True)
        self._mw.doubleSpinBox_mw_frequency.setEnabled(True)
        self._mw.doubleSpinBox_max_amplitude.setEnabled(True)
        self._mw.doubleSpinBox_min_amplitude.setEnabled(True)
        self._mw.doubleSpinBox_step_amplitude.setEnabled(True)
        self._mw.doubleSpinBox_measurement_time.setEnabled(True) 
        
        self._mw.spinBox_numberofcycles.setEnabled(True)
        
        self._mw.comboBox_waveform.setEnabled(True)
        self._mw.comboBox_mode.setEnabled(True)
        self._mw.comboBox_trigger_source.setEnabled(True)
        self._mw.comboBox_output.setEnabled(True)
        self._mw.comboBox_channel.setEnabled(True)        
        
        self._mw.pushButton_go.setEnabled(True)
        self._mw.pushButton_ramp.setEnabled(True)
        self._mw.pushButton_get_status.setEnabled(True)
        
        return
        
    
        ########################################################################
        ########################################################################
        ########################################################################
        ########################################################################
        
        
        #   Definition of the general functions to control the GBF parameters
                        
        
        ########################################################################
        ########################################################################
        ########################################################################
        ########################################################################


        ########################################################################
        #                        Set the GBF parameters                        #
        ########################################################################

    def toggle_output(self):
        """Function which takes the information about the output box and emit a signal to
        turn ON or turn OFF the output on the hardware.
        Signal: str to logic"""
        
        output = self._mw.comboBox_output.currentText()
        self.sigSetOutput.emit(output)
        self.log.info("GBF: I turned {} the output boss.".format(output))
        return
        
    def set_channel(self):
        """Function which takes the information of the channel box and emit a signal 
        to change the channel on the hardware.
        Signal: str to logic"""
        
        channel = self._mw.comboBox_channel.currentText()
        self.sigSetChannel.emit(channel)
        self.log.info("GBF: Good choice, I set the channel {}.".format(channel))
        return

    def set_waveform(self):
        """Function which takes the information of the waveform box and emit a signal 
        to change the waveform on the hardware.
        Signal: str to logic"""
        
        waveform = self._mw.comboBox_waveform.currentText()
        self.sigSetWaveform.emit(waveform)
        self.log.info("GBF: I set the waveform function {}.".format(waveform))
        return
    
    def set_mode(self):
        """Function which takes the information of the mode box and emit a signal 
        to change the mode on the hardware.
        Signal: str to logic"""
        
        mode = self._mw.comboBox_mode.currentText()
        self.sigSetMode.emit(mode)
        self.log.info("GBF: I set the mode {}.".format(mode))
        return

    def set_trigger(self):
        """Function which takes the information of the trigger source box and emit a signal 
        to change the trigger source on the hardware.
        Signal: str to logic"""
        
        trigger_source = self._mw.comboBox_trigger_source.currentText()
        self.sigSetTriggerSource.emit(trigger_source)
        self.log.info("GBF: I set the trigger source {}.".format(trigger_source))
        return
    
        ########################################################################
        #                 Get the GBF parameters and edit them                 #
        ########################################################################
        
    def get_gbf_parameters(self):
        """Function which emits a signal to get the information of the current
        GBF parameters on the hardware.
        Signal: to logic"""
        
        self.sigGetParameters.emit()
        self.log.info("GBF: Let me check it. I am looking for the information.")
        return 
    
    def display_status(self, params_dict):
        """ Display the value of the GBF paramaters.
        
        @param dict params_dict: dictionary with entries being again dictionaries
                       with two needed keywords 'value' and 'unit' and one
                       optional keyword 'error'.
        
        Example of a param dict:
        param_dict = {'amplitude': {'value':1, 'unit': 'V'},
                      'frequency':  {'value':100e3,  'unit': 'Hz'},
                      'waveform':       {'value':'sine', 'unit': ''}}
        
        @return (dict): The formated_results
        """
        
        self._mw.textBrowser_gbf_parameters.clear()
        try:
            formated_results = units.create_formatted_output(params_dict)
        except:
            formated_results = 'this fit does not return formatted results'
        self._mw.textBrowser_gbf_parameters.setPlainText(formated_results)
        self.log.info("GBF: Here are my current setting parameters")
        return formated_results
    
        ########################################################################
        #                           Set the GBF parameters                     #
        ########################################################################
           
    def set_gbf_parameters(self):
        """Function which takes the information on the channel, amplitude, 
        frequency, mode and number of cycles boxes and emit a signal to logic
        to change it on the hardware.
        Signal: dict to logic
        """
        
        params_dict = {}
        amplitude = self._mw.doubleSpinBox_amplitude.value()
        params_dict['amplitude'] = amplitude
        frequency = self._mw.doubleSpinBox_frequency.value()
        params_dict['frequency'] = frequency*1e3
        if self._gbf_logic.mode == 'burst': 
            numberofcycles = self._mw.spinBox_numberofcycles.value
            params_dict['number of cycles'] = numberofcycles
        self.sigSetParameters.emit(params_dict)
        self.log.info("GBF: One seconde please, let me set everything")
        return params_dict 


        ########################################################################
        ########################################################################
        ########################################################################
        ########################################################################
        
        
        #   Definition of the function to perform the electric field ramp
                        
                                    
        ########################################################################
        ########################################################################
        ########################################################################
        ########################################################################


        ########################################################################
        #                      Electric field ramp measurements                #
        ########################################################################
    
    def do_the_ramp(self):
        """Function which takes the information on the pi pulse, evolution time,
        MW power, MW frequency, max amplitude, min amplitude, step amplitude and
        measurement times boxes and emit a signal to start the electric field ramp
        measurement.
        Signal: dict to logic"""
        
        params_dict = {}
        pi_pulse = self._mw.doubleSpinBox_pi_pulse.value()
        params_dict["pi pulse"] = pi_pulse*1e-6
        evolution_time = self._mw.doubleSpinBox_evolution_time.value()
        params_dict["evolution time"] = evolution_time*1e-6
        mw_power = self._mw.doubleSpinBox_mw_power.value()
        params_dict["MW power"] = mw_power
        mw_frequency = self._mw.doubleSpinBox_mw_frequency.value()
        params_dict["MW frequency"] = mw_frequency*1e9
        max_amplitude = self._mw.doubleSpinBox_max_amplitude.value()
        params_dict["max amplitude"] = max_amplitude
        min_amplitude = self._mw.doubleSpinBox_min_amplitude.value()
        params_dict["min amplitude"] = min_amplitude
        step_amplitude = self._mw.doubleSpinBox_step_amplitude.value()
        params_dict["step amplitude"] = step_amplitude
        measurement_time = self._mw.doubleSpinBox_measurement_time.value()
        params_dict["measurement time"] = measurement_time
        self.sigStartRamp.emit(params_dict)
        self.disable_buttons()
        self.log.info("GBF: Let's start the electric field ramp measurement")

    def stop_ramp_measurement(self):
        self.sigStopRamp.emit()
        
        ########################################################################
        #                 Fit the ramp and display the fitting curve           #
        ########################################################################

    def do_fit(self):
        """Function which emits a signal to logic to start the fitting procedure.
        
        Signal: to logic
        """
        self.sigDoFit.emit()
        
    def display_fit(self, params_dict):
        """Display the fit value of the ramp.
        
        @param dict params_dict: dictionary with entries being again dictionaries
                       with two needed keywords 'value' and 'unit' and one
                       optional keyword 'error'.
        
        Example of a param dict:
        param_dict = {'fit amplitude': {'value':1, 'unit': 'V'},
                      'fit period':  {'value':100e3,  'unit': 'Hz'}}
        
        @return (dict): The formated_results
        """
        
        self._mw.textBrowser_fit_electric_field.clear()
        try:
            formated_results = units.create_formatted_output(params_dict)
        except:
            formated_results = 'this fit does not return formatted results'
        self._mw.textBrowser_fit_electric_field.setPlainText(formated_results)
        
        return formated_results


        ########################################################################
        ########################################################################
        ########################################################################
        ########################################################################
        
        
        #   Definition of useful functions
                        
                                    
        ########################################################################
        ########################################################################
        ########################################################################
        ########################################################################

    def refresh_plot_Efield(self):
        """ Refresh the plot widget with new data.
        """
        
        self.Efield_plot.setData(x=self._gbf_logic.measured_data[:,0],
                                    y=self._gbf_logic.measured_data[:,1])
        self.Efield_plot_error.setData(x=self._gbf_logic.measured_data[:,0],
                                     y=self._gbf_logic.measured_data[:,1],
                                     height=self._gbf_logic.measured_data[:,2])
        return

    def refresh_plot_fit(self):
        self.Efield_plot_fit.setData(x=self._gbf_logic.measured_data[:,0],
                                         y=self._gbf_logic.Efield_fit)
        return
        
        ########################################################################
        #                               Save and Close                         #
        ########################################################################        
 
    def save_routine(self):
        """Call save_data from logic.
        """
        self._gbf_logic.save_data()
        self.log.info("GBF : I save the data")
        return
        