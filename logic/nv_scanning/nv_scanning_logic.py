# -*- coding: utf-8 -*-
""" 
This module is the skeleton logic for a scanning NV microscope, 
handling the scanning and the data saving/sending to the GUI.

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
import threading
from collections import OrderedDict

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex
from core.connector import Connector
from core.configoption import ConfigOption
from core.statusvariable import StatusVar

from qtpy import QtCore

class WorkerThread(QtCore.QRunnable):
    """ Create a simple Worker Thread class, with a similar usage to a python
    Thread object. This Runnable Thread object is intended to be run from a
    QThreadpool.

    @param obj_reference target: A reference to a method, which will be executed
                                 with the given arguments and keyword arguments.
                                 Note, if no target function or method is passed
                                 then nothing will be executed in the run
                                 routine. This will serve as a dummy thread.
    @param tuple args: Arguments to make available to the run code, should be
                       passed in the form of a tuple
    @param dict kwargs: Keywords arguments to make available to the run code
                        should be passed in the form of a dict
    @param str name: optional, give the thread a name to identify it.
    """

    def __init__(self, target=None, args=(), kwargs={}, name=''):
        super(WorkerThread, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.target = target
        self.args = args
        self.kwargs = kwargs
        if name == '':
            name = str(self.get_thread_obj_id())
        self.name = name
        self._is_running = False

        
    def get_thread_obj_id(self):
        """ Get the ID from the current thread object. """
        return id(self)

    
    @QtCore.Slot()
    def run(self):
        """ Initialise the runner function with passed self.args, self.kwargs."""
        if self.target is None:
            return
        self._is_running = True
        self.target(*self.args, **self.kwargs)
        self._is_running = False

        
    def is_running(self):
        return self._is_running

    
    def autoDelete(self):
        """ Delete the thread. """
        self._is_running = False
        return super(WorkerThread, self).autoDelete()


class NVMicroscopeLogic(GenericLogic):
    
    _modclass = 'NVMicroscopeLogic'
    _modtype = 'logic'

    # declare connectors
    confocalscanner = Connector(interface='ConfocalScannerInterface')
    savelogic = Connector(interface='SaveLogic')

    # status variables
    return_slowness = StatusVar('return_slowness', default=50e-9)
    x_res = StatusVar('x_res', default=100)
    y_res = StatusVar('y_res', default=100)
    angle = StatusVar('y_res', default=0)
    x_center_pos = StatusVar('x_center_pos', default=15e-6)
    y_center_pos = StatusVar('y_center_pos', default=15e-6)
    scan_width = StatusVar('scan_width', default=1e-6)
    scan_height = StatusVar('scan_height', default=1e-6)
    user_save_tag = StatusVar('user_save_tag', default='')


    # signals
    sigUpdateDuration = QtCore.Signal(str) # connected in GUI
    sigUpdateRemTime = QtCore.Signal(str) # connected in GUI
    sigRefreshScanArea = QtCore.Signal(list) # connected in GUI
    
    sigXResChanged = QtCore.Signal(int) # for mapper
    sigYResChanged = QtCore.Signal(int) # for mapper
    sigRSChanged = QtCore.Signal(float) # for mapper
    sigAngleChanged = QtCore.Signal(float) # for mapper
    
    sigStartPointChanged = QtCore.Signal(str)



    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

        
    def on_activate(self):
        """ Initialization performed during activation of the module.
        """

        # in this threadpool our worker thread will be run
        self.threadpool = QtCore.QThreadPool()
        return
    

    def on_deactivate(self):
        """ Deinitialization performed during deactivation of the module.
        """
        return

    ##################################
    # Handling of all the parameters #
    ##################################

    # x resolution
    def handle_x_res(self, value=None):
        if value is not None:
            self.x_res = value
            self.sigXResChanged.emit(self.x_res)
            self.update_scan_area()
            return 
        else:
            return self.x_res

    # y resolution
    def handle_y_res(self, value=None):
        if value is not None:
            self.y_res = value
            self.sigYResChanged.emit(self.y_res)
            self.update_scan_area()
            return 
        else:
            return self.y_res

    # return slowness
    def handle_rs(self, value=None):
        if value is not None:
            self.return_slowness = value
            self.sigRSChanged.emit(self.return_slowness)
            self.update_scan_area()
            return 
        else:
            return self.return_slowness

    def handle_angle(self, value=None):
        if value is not None:
            self.angle = value
            self.sigAngleChanged.emit(self.angle)
            self.update_scan_area()
            return 
        else:
            return self.angle

    def handle_starting_point(self, value=None):
        if value is not None:
            self.starting_point = value
            self.sigStartPointChanged.emit(self.starting_point)
            self.update_scan_area()
            return 
        else:
            return self.starting_point


    #def update_scan_area(self):
