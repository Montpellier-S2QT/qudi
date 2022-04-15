# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI for controlling a 3D superconducting
magnet.

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
from core.connector import Connector
from core.configoption import ConfigOption
from gui.guibase import GUIBase
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy import uic

class VectorMagnetMainWindow(QtWidgets.QMainWindow):
    """ The main window for the superconducting magnet GUI.
    """
    
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_vectormagnetgui.ui')

        # Load it
        super(VectorMagnetMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()
        
class VectorMagnetGui(GUIBase):
    """ This is the GUI Class for the superconducting magnet.
    """
    
    _modclass = 'VectorMagnetGui'
    _modtype = 'gui'
    _magnet_type = ConfigOption("magnet_type", "coil") # otherwise "supra"
    
    # declare connectors
    scmagnetlogic = Connector(interface='SuperConductingMagnetLogic')
    coilmagnetlogic = Connector(interface='Vectormagnetlogic')
    
    # declare signals
    sigGoToField = QtCore.Signal(float, float, float)
    
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        
    def on_activate(self):
        """ Definition, configuration and initialisation of the quenching GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """
        if self._magnet_type == 'supra':
            self._magnetlogic = self.scmagnetlogic()
        elif self._magnet_type == 'coil':
            self._magnetlogic = self.coilmagnetlogic()
        else:
            self.log.warning("Unknown magnet type, using coil instead.")
            self._magnetlogic = self.scmagnetlogic()
        
        ########################################################################
        #                      General configurations                          #
        ########################################################################
        
        # use the inherited class 'Ui_SCMagnetGuiUI' to create now the GUI element:
        self._mw = VectorMagnetMainWindow()
        
        self._mw.pushButton_convert.clicked.connect(self.convert_xyz)
        self._mw.pushButton_go_to.clicked.connect(self.go_to_field)
        self._mw.B_perp_pushButton.clicked.connect(self.compute_B_perp)
        
        # send signals to logic
        self.sigGoToField.connect(
            self._magnetlogic.go_to_field, QtCore.Qt.QueuedConnection)
        
        # connect to signals from logic
        self._magnetlogic.sigFieldSet.connect(self.enable_gui)
        self._magnetlogic.sigSweeping.connect(self.update_sweep_display)
        self._magnetlogic.sigCurrentsValuesUpdated.connect(self.update_currents_display)
        self._magnetlogic.sigNewFieldValues.connect(self.update_field_values)
        
        # get power supply and coil status
        self._mw.Bx_status_display.setText(self._magnetlogic.get_sweep_status("x"))
        self._mw.By_status_display.setText(self._magnetlogic.get_sweep_status("y"))
        self._mw.Bz_status_display.setText(self._magnetlogic.get_sweep_status("z"))
        currents = self._magnetlogic.get_currents("x")
        self._mw.iout_x_display.setText("{:.4f} A".format(currents[0]))
        self._mw.imag_x_display.setText("{:.4f} A".format(currents[1]))
        currents = self._magnetlogic.get_currents("y")
        self._mw.iout_y_display.setText("{:.4f} A".format(currents[0]))
        self._mw.imag_y_display.setText("{:.4f} A".format(currents[1]))
        currents = self._magnetlogic.get_currents("z")
        self._mw.iout_z_display.setText("{:.4f} A".format(currents[0]))
        self._mw.imag_z_display.setText("{:.4f} A".format(currents[1]))
        
        self._mw.pushButton_go_to.setEnabled(False)
        return
    
    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        if self._magnetlogic.check_before_closing():
            self._mw.close()
            return 0
        else:
            self.log.warning("Not all the fields are zero or a heater is ON!")
            messagebox = QtGui.QMessageBox()
            messagebox.setText("Not all the fields are zero or a heater is ON!")
            messagebox.setStandardButtons(QtGui.QMessageBox.Ok)
            messagebox.setWindowTitle("Warning")
            messagebox.exec_()
            return -1
        
        return

    
    def show(self):
        """ Make window visible and put it above all other windows. 
        """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()
        
        return

    
    def update_sweep_display(self, coil, sweeping):
        """ Update the GUI if a coil is sweeping or idling
            @param str "x", "y" or "z"
            @param bool sweeping or not
        """
        if coil=="x":
            if sweeping:
                self._mw.Bx_status_display.setText("sweeping...")
            else:
                self._mw.Bx_status_display.setText("sweep paused")
        elif coil=="y":
            if sweeping:
                self._mw.By_status_display.setText("sweeping...")
            else:
                self._mw.By_status_display.setText("sweep paused")
        else:
            if sweeping:
                self._mw.Bz_status_display.setText("sweeping...")
            else:
                self._mw.Bz_status_display.setText("sweep paused")
        
        return

    
    def update_currents_display(self, coil, iout, imag):
        """ Update the displayed value of currents
            @param str "x", "y" or "z"
            @param float
            @param float
        """
        if coil=="x":
            self._mw.iout_x_display.setText("{:.4f} A".format(iout))
            self._mw.imag_x_display.setText("{:.4f} A".format(imag))
        elif coil=="y":
            self._mw.iout_y_display.setText("{:.4f} A".format(iout))
            self._mw.imag_y_display.setText("{:.4f} A".format(imag))
        else:
            self._mw.iout_z_display.setText("{:.4f} A".format(iout))
            self._mw.imag_z_display.setText("{:.4f} A".format(imag))
        
        return

    
    def update_field_values(self, Bx, By, Bz):
        """ Update the displayed value of B
            @param float
            @param float
            @param float
        """
        self.Bx = Bx
        self.By = By
        self.Bz = Bz
        self._mw.display_x.setText("{:.3f} mT".format(Bx))
        self._mw.display_y.setText("{:.3f} mT".format(By))
        self._mw.display_z.setText("{:.3f} mT".format(Bz))

        
    def convert_xyz(self):
        """ Converts the field in spherical coords to cartesian coords.
        """
        mag = self._mw.doubleSpinBox_magnitude.value()
        theta = self._mw.doubleSpinBox_theta.value()*np.pi/180
        phi = self._mw.doubleSpinBox_phi.value()*np.pi/180
        
        self.Bx = np.round(mag*np.sin(theta)*np.cos(phi), decimals=3)
        self.By = np.round(mag*np.sin(theta)*np.sin(phi), decimals=3)
        self.Bz = np.round(mag*np.cos(theta), decimals=3)
        
        self._mw.display_x.setText("{:.3f} mT".format(self.Bx))
        self._mw.display_y.setText("{:.3f} mT".format(self.By))
        self._mw.display_z.setText("{:.3f} mT".format(self.Bz))
        self._mw.pushButton_go_to.setEnabled(True)
        
        return

    
    def go_to_field(self):
        """ Sends the signal with the three field values x, y, z and 
            disable the GUI buttons.
        """
        self._mw.pushButton_convert.setEnabled(False)
        self._mw.pushButton_go_to.setEnabled(False)
        self._mw.B_perp_pushButton.setEnabled(False)

        if self._mw.offset_checkBox.isChecked():
            if self._mw.spherical_radioButton.isChecked():
                mag = self._mw.offset_mag_doubleSpinBox.value()
                theta = self._mw.offset_theta_doubleSpinBox.value()*np.pi/180
                phi = self._mw.offset_phi_doubleSpinBox.value()*np.pi/180
                self.Bx = self.Bx + np.round(mag*np.sin(theta)*np.cos(phi), decimals=3)
                self.By = self.By + np.round(mag*np.sin(theta)*np.sin(phi), decimals=3)
                self.Bz = self.Bz + np.round(mag*np.cos(theta), decimals=3)
            elif self._mw.cartesian_radioButton.isChecked():
                self.Bx = self.Bx + self._mw.offset_Bx_doubleSpinBox.value()
                self.By = self.By + self._mw.offset_By_doubleSpinBox.value()
                self.Bz = self.Bz + self._mw.offset_Bz_doubleSpinBox.value()
            else:
                self.log.warning("No offset field specified!")

        if self._magnet_type == 'supra':
            self.sigGoToField.emit(self.Bx, self.By, self.Bz)
        else:
            # coil magnet logic needs the field in Gauss
            self.sigGoToField.emit(self.Bx, self.By,
                                        self.Bz)
            # else:
            #     self.log.warning("No field was applied")
            #     self.enable_gui()
                
        return
    
    
    # def check_field_sign(self):
    #     """ Displays a warning if cables need to be switched """
        
    #     self.Bx_to_coil = self.Bx*10
    #     self.By_to_coil = self.By*10
    #     self.Bz_to_coil = self.Bz*10
        
    #     switch_x = self.Bx < 0
    #     switch_y = self.By < 0
    #     switch_z = self.Bz < 0
    #     text_x = "normal state: red on red and black on black."
    #     text_z = text_x
    #     text_y = "normal state: red on black and black on red."
        
    #     if switch_x:
    #         text_x ="inverted state: red on black and black on red."
    #         self.Bx_to_coil = -self.Bx_to_coil
    #     if switch_y:
    #         text_y ="inverted state: red on red and black on black."
    #         self.By_to_coil = -self.By_to_coil
    #     if switch_z:    
    #         text_z ="inverted state: red on black and black on red."
    #         self.Bz_to_coil = -self.Bz_to_coil
            
    
    #     msg = QtWidgets.QMessageBox()
    #     msg.setWindowTitle("Cable inversion status")
    #     msg.setText(f"You might need to invert the cables on some channels.\n \n"
    #                 f"The needed configuration is following:\n"
    #                 f"Coil x, {text_x}\n"
    #                 f"Coil y, {text_y}\n"
    #                 f"Coil z, {text_z}\n\n"
    #                 f"Click OK when you are done.")
    #     msg.setIcon(QtWidgets.QMessageBox.Warning)
    #     msg.setStandardButtons(QtWidgets.QMessageBox.Cancel|QtWidgets.QMessageBox.Ok)
    #     rep = msg.exec()
    #     print(rep)
    #     if rep == QtWidgets.QMessageBox.Ok:
    #         return True
    #     else:
    #         return False


    def compute_B_perp(self):
        """
        Compute Bperp for a given angle in the perpendicular plane, and sets it as target field.
        """
        theta_tip = self._mw.theta_tip_doubleSpinBox.value()*np.pi/180
        phi_tip = self._mw.phi_tip_doubleSpinBox.value()*np.pi/180
        beta_perp = self._mw.beta_perp_doubleSpinBox.value()*np.pi/180
        mag = self._mw.doubleSpinBox_magnitude_Bperp.value()

        u_perp = np.array([-np.sin(phi_tip), np.cos(phi_tip), 0])
        v_perp = np.array([-np.cos(theta_tip)*np.cos(phi_tip),
                           -np.cos(theta_tip)*np.sin(phi_tip),
                           np.sin(theta_tip)])
        Bperp_dir = np.cos(beta_perp)*u_perp + np.sin(beta_perp)*v_perp
        self.Bx = np.round(mag*Bperp_dir[0], decimals=3)
        self.By = np.round(mag*Bperp_dir[1], decimals=3)
        self.Bz = np.round(mag*Bperp_dir[2], decimals=3)
        
        self._mw.display_x.setText("{:.3f} mT".format(self.Bx))
        self._mw.display_y.setText("{:.3f} mT".format(self.By))
        self._mw.display_z.setText("{:.3f} mT".format(self.Bz))

        self._mw.pushButton_go_to.setEnabled(True)

        return
    
    
    def enable_gui(self):
        """Enables all the buttons again once the field is set.
        """
        self._mw.pushButton_convert.setEnabled(True)
        self._mw.B_perp_pushButton.setEnabled(True)
        
        return    
