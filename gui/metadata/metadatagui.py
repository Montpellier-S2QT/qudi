# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI to handle the metadata.

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

from core.connector import Connector
from core.configoption import ConfigOption
from gui.guibase import GUIBase
from qtpy import QtWidgets
from qtpy import uic
from qtwidgets.scientific_spinbox import ScienDSpinBox

try:
    import pyperclip
    PYPERCLIP_OK = True
except ModuleNotFoundError:
    PYPERCLIP_OK = False


class MetadataMainWindow(QtWidgets.QMainWindow):
    """ The main window for the metadata GUI.
    """
    
    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_metadatagui.ui')

        # Load it
        super(MetadataMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()


class MetadataGui(GUIBase):
    """ This is the GUI Class for metadata module.

    Example config for copy-paste:

    metadata:
        module.Class: 'metadata.metadatagui.MetadataGui'
        connect:
            savelogic: 'savelogic'
    """

    # declare connectors
    savelogic = Connector(interface='SaveLogic')
    read_only = ConfigOption('read_only', default=False)
  
    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        
    def on_activate(self):
        """ Definition, configuration and initialisation of the GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """

        ########################################################################
        #                      General configurations                          #
        ########################################################################
        
        self._mw = MetadataMainWindow()
        self._gl = self._mw.gridLayout

        self.entry_dict = {}
        self.timestamp = ""

        self._mw.add_pushButton.clicked.connect(self.add_param)

        if PYPERCLIP_OK:
            self._mw.copy_pushButton.clicked.connect(self.timestamp_to_clipboard)
        else:
            self.log.warning('Install pyperclip (pip install pyperclip) to copy timestamp to clipboard.')

        if self.read_only:
            self._mw.add_pushButton.setEnabled(False)
        
        # connect to signals from logic
        self.savelogic().sigAddParamsUpdated.connect(self.update_param_list)
        self.savelogic().sigFileSaved.connect(self.display_saved_file)

    def on_deactivate(self):
        """ Reverse steps of activation
        """
        self._mw.close()

    def show(self):
        """ Make window visible and put it above all other windows. 
        """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()

    def update_param_list(self):
        """ Updates the display when the parameter dict is changed.
        """
        params_dict = self.savelogic().get_additional_parameters()
        
        for k in params_dict.keys():
            to_add = True
            number = False
            # check if the new value is a number
            try:    
                value = float(params_dict[k])
                number = True
            except ValueError:
                value = str(params_dict[k])

            # check if we know k already and if the value did not change type
            # if the type changed, we remove the widgets and add them again
            if k in self.entry_dict.keys():
                try:
                    if number:
                        self.entry_dict[k][1].setValue(value)
                    else:
                        self.entry_dict[k][1].setText(value)
                    to_add = False
                except:
                    self.entry_dict[k][0].hide()
                    self.entry_dict[k][1].hide()
                    self.entry_dict[k][2].hide()
                    self.entry_dict.pop(k)

            if to_add:
                if number:
                    input_widget = ScienDSpinBox()
                    input_widget.setValue(value)
                    input_widget.editingFinished.connect(
                        lambda: self.update_value(input_widget.value(), k))
                    
                else:
                    input_widget = QtWidgets.QLineEdit()
                    input_widget.setText(value)
                    input_widget.editingFinished.connect(
                        lambda: self.update_value(input_widget.text(), k))

                    
                self.entry_dict[k] = (QtWidgets.QLabel(str(k)), input_widget,
                                      QtWidgets.QPushButton("Remove"))
                last_row = self._gl.rowCount() +1
                self._gl.addWidget(self.entry_dict[k][0], last_row, 1)
                self._gl.addWidget(self.entry_dict[k][1], last_row, 2)
                self._gl.addWidget(self.entry_dict[k][2], last_row, 3)
                self.entry_dict[k][2].clicked.connect(lambda :\
                                    self.savelogic().remove_additional_parameter(k))

            if self.read_only:
                self.entry_dict[k][1].setReadOnly(True)
                self.entry_dict[k][2].setEnabled(False)
                
        to_remove = []
        for k in self.entry_dict.keys():
            if k not in params_dict.keys():
                to_remove.append(k)
        for k in to_remove:
            self.entry_dict[k][0].hide()
            self.entry_dict[k][1].hide()
            self.entry_dict[k][2].hide()
            self.entry_dict.pop(k)
        return

    def update_value(self, value, key):
        """ Change a value in the additional_parameters dict of savelogic.
        """
        self.savelogic().update_additional_parameters({key: value})
        return

    def display_saved_file(self, module, timestamp):
        self._mw.last_file_label.setText(f"Last file saved by {module} module with timestamp {timestamp}.")
        self.timestamp = timestamp
        return

    def timestamp_to_clipboard(self):
        """ Copy the currently displayed timestamp to the clipboard.
        """
        pyperclip.copy(self.timestamp)

    def add_param(self):
        """ Opens a dialog to input the parameters.
        """
        add_dialog = QtWidgets.QDialog()
        add_dialog.setWindowTitle("Add a metadata entry")
        key_label = QtWidgets.QLabel("Key:", add_dialog)
        key_label.move(20,20)
        input_label = QtWidgets.QLabel("Value:", add_dialog)
        input_label.move(20,60)
        input_key = QtWidgets.QLineEdit("", add_dialog)
        input_key.move(60, 20)
        input_value = QtWidgets.QTextEdit("", add_dialog)
        input_value.move(60, 60)
        button = QtWidgets.QPushButton("Done", add_dialog)
        button.move(280, 260)
        button.clicked.connect(lambda : self.get_added_param(input_key, input_value))
        button.clicked.connect(add_dialog.accept)
        button2 = QtWidgets.QPushButton("Cancel", add_dialog)
        button2.move(200, 260)
        button2.clicked.connect(add_dialog.reject)
        add_dialog.exec()

    def get_added_param(self, input_key, input_value):
        """ Get the input parameters from the dialog.
        """
        key = input_key.text()
        key = self.remove_annoying_characters(key)
        value = input_value.toPlainText()
        value = self.remove_annoying_characters(str(value))
        try:
            value = float(value)
        except:
            pass
        self.update_value(value, key)
    
    def remove_annoying_characters(self, input_string):
        """ Removes unwanted characters from the string (for easier parsing of the file headers).
        """
        bad_chars = [":", "#", "\n"]
        for ch in bad_chars:
            input_string = input_string.replace(ch, "")
        return input_string

