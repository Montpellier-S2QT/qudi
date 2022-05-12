# -*- coding: utf-8 -*-
""" 
This file defines a generic procedure object used to describe a measurement. 
It is the basis of specific scan modes, which are either predefined in .py
files or created on the fly in a notebook. 

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
from qtpy import QtCore

class GenericProcedure(object):
    """ Object defining a generic measurement procedure, 
    helping you to build the one you need.
    """

    sigPixelReady = QtCore.Signal(OrderedDict) # to send the data back to the logic
    
    def __init__(self, name, bricks_logic):
        """ The constructor for a scanning procedure needs the name of the 
        procedure and a NVMicroscopyBricksLogic.

        @param str name: name of the procedure (like "Quenching").
        @param NVMicroscopyBricksLogic bricks_logic: logic connected to the 
               hardware and defining all the basic operations.
        """
        self.name = name
        self.bricks_logic = bricks_logic
        self.parameter_dict = {} # dict of 2-tuples (value, unit)
        # list of the channels to plot, each element should be a dict with the same
        # keys as the topo channel described here
        self.outputs = [{"title": "Topography", "image": np.zeros(100, 100),
                         "line": np.transpo}] 
        pass

    
    def scan_init(self):
        """
        The initial steps to perform before starting the scan itself.
        For example, starting the MW, setting up the AWG trigger, etc.
        """
        return

    
    def compute_measurement_duration(self, x_res, y_res, return_slowness):
        """ Computes the time that the scan is supposed to last.
        
        @return float duration: expected measurement time in seconds 
        """
        duration = 0
        return duration
    
    
    def acquisition(self):
        """
        Function called by the main scanning logic at each pixel.
        """
        sigPixelReady.emit(self.outputs)
        return


    def end_of_line_action(self):
        """
        If you need to do something at the end of each line, like an optimize or a Rabi.
        """
        return
    

    def scan_end(self):
        """
        The final steps to perform after finishing the scan itself.
        For example, stopping the MW, etc.
        """
        return
    
