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
    starting_point = StatusVar('starting_point', default='LL')
    x_center_pos = StatusVar('x_center_pos', default=15e-6)
    y_center_pos = StatusVar('y_center_pos', default=15e-6)
    scan_width = StatusVar('scan_width', default=1e-6)
    scan_height = StatusVar('scan_height', default=1e-6)
    user_save_tag = StatusVar('user_save_tag', default='')

    # signals
    sigUpdateDuration = QtCore.Signal(str) # connected in GUI
    sigUpdateRemTime = QtCore.Signal(str) # connected in GUI
    sigRefreshScanArea = QtCore.Signal() # connected in GUI
    sigUpdateProcedureList = QtCore.Signal(list) # connected in GUI
    
    sigXResChanged = QtCore.Signal(int) # for mapper
    sigYResChanged = QtCore.Signal(int) # for mapper
    sigRSChanged = QtCore.Signal(float) # for mapper
    sigAngleChanged = QtCore.Signal(float) # for mapper
    sigStartPointChanged = QtCore.Signal(str)
    sigScanWidthChanged = QtCore.Signal(float) # for mapper
    sigScanHeightChanged = QtCore.Signal(float) # for mapper
    sigXCenterChanged = QtCore.Signal(float) # for mapper
    sigYCenterChanged = QtCore.Signal(float) # for mapper
    sigFileTagChanged = QtCore.Signal(str) # for mapper

    sigStartScan = QtCore.Signal()
    sigStopScan = QtCore.Signal(bool)
    sigResumeScan = QtCore.Signal()
   


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
            return 
        else:
            return self.x_res

        
    # y resolution
    def handle_y_res(self, value=None):
        if value is not None:
            self.y_res = value
            self.sigYResChanged.emit(self.y_res)
            return 
        else:
            return self.y_res

        
    # return slowness
    def handle_rs(self, value=None):
        if value is not None:
            self.return_slowness = value
            self.sigRSChanged.emit(self.return_slowness)
            return 
        else:
            return self.return_slowness

        
    # scan angle
    def handle_angle(self, value=None):
        if value is not None:
            self.angle = value
            self.sigAngleChanged.emit(self.angle)
            self.sigRefreshScanArea.emit()
            return 
        else:
            return self.angle

        
    # scan starting point
    def handle_starting_point(self, value=None):
        if value is not None:
            self.starting_point = value
            self.sigStartPointChanged.emit(self.starting_point)
            self.sigRefreshScanArea.emit()
            return 
        else:
            return self.starting_point

        
    # scan width
    def handle_scan_width(self, value=None):
        if value is not None:
            self.scan_width = value
            self.sigScanWidthChanged.emit(self.scan_width)
            self.sigRefreshScanArea.emit()
            return 
        else:
            return self.scan_width

        
    # scan height
    def handle_scan_height(self, value=None):
        if value is not None:
            self.scan_height = value
            self.sigScanHeightChanged.emit(self.scan_height)
            self.sigRefreshScanArea.emit()
            return 
        else:
            return self.scan_height

        
    # scan center pos x
    def handle_x_center(self, value=None):
        if value is not None:
            self.x_center_pos = value
            self.sigXCenterChanged.emit(self.x_center_pos)
            self.sigRefreshScanArea.emit()
            return 
        else:
            return self.x_center_pos

        
    # scan center pos y    
    def handle_y_center(self, value=None):
        if value is not None:
            self.y_center_pos = value
            self.sigYCenterChanged.emit(self.y_center_pos)
            self.sigRefreshScanArea.emit()
            return 
        else:
            return self.y_center_pos


    # file_tag
    def handle_file_tag(self, value=None):
        if value is not None:
            self.user_save_tag = value
            self.sigFileTagChanged.emit(self.user_save_tag)
            return 
        else:
            return self.user_save_tag

        
    def scan_area_corners(self):
        """ Returns the positions of the corners of the scan region."""
        x0 = self.x_center_pos
        y0 = self.y_center_pos
        w = self.scan_width
        h = self.scan_height
        a = self.angle*np.pi/180
        xcoords = x0+0.5*np.array([-w*np.cos(a)+h*np.sin(a), w*np.cos(a)+h*np.sin(a),
                                   w*np.cos(a)-h*np.sin(a), -w*np.cos(a)-h*np.sin(a)])
        ycoords = y0+0.5*np.array([-w*np.sin(a)-h*np.cos(a), w*np.sin(a)-h*np.cos(a),
                                   w*np.sin(a)+h*np.cos(a), -w*np.sin(a)+h*np.cos(a)])
        return np.transpose(np.stack((xcoords, ycoords)))

    
    def starting_point_coords(self):
        """ Returns the position of the starting corner of the scan region."""
        coords = self.scan_area_corners()
        if self.starting_point == "LL":
            return coords[0, :]
        elif self.starting_point == "LR":
            return coords[1, :]
        elif self.starting_point == "UR":
            return coords[2, :]
        else:
            return coords[3, :]

        
    def change_current_procedure(self, procedure_name):
        pass

    def update_scanning_procedures(self):
        pass
