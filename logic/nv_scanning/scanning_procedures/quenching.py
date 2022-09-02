# -*- coding: utf-8 -*-
""" 
This file defines the quenching scan procedure.

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
from logic.nv_scanning.generic_procedure import GenericProcedure
from collections import OrderedDict
import numpy as np

class QuenchingProcedure(GenericProcedure):
    """ Object defining the quenching measurement procedure.
    """

    sigPixelReady = QtCore.Signal(OrderedDict) # to send the data back to the logic
    
    def __init__(self, name, bricks_logic):
        """ The constructor for a scanning procedure needs the name of the 
        procedure and a NVMicroscopyBricksLogic.

        @param str name: name of the procedure (like "Quenching").
        @param NVMicroscopyBricksLogic bricks_logic: logic connected to the 
               hardware and defining all the basic operations.
        """
        super().__init__(name, bricks_logic)
        self.name = name
        self.bricks_logic = bricks_logic
        self.parameter_dict = {"Measurement time": (0.1, "s")} # dict of 2-tuples (value, unit)
        self.clock_frequency = 1/self.parameter_dict["Measurement time"][0]
        # list of the channels to plot, each element should be a dict with the same
        # keys as the topo channel described here
        self.outputs = OrderedDict()
        self.outputs["Topography"] = {"title": "Topography", "image": np.zeros((100, 100)),
                                      "line": np.zeros(100), "name": "z",
                                      "unit": "m", "cmap_name": "gray",
                                      "plane_fit": True, "line_correction": True}
        self.outputs["PL Quenching"] = {"title": "PL Quenching", "image": np.zeros((100, 100)),
                                        "line": np.zeros(100), "name": "PL",
                                        "unit": "cts/s", "cmap_name": "copper",
                                        "plane_fit": False, "line_correction": True}
        return

    
    def scan_init(self):
        """
        The initial steps to perform before starting the scan itself.
        For example, starting the MW, setting up the AWG trigger, etc.
        """
        # to set up the scanner in the logic
        self.clock_frequency = 1/self.parameter_dict["Measurement time"][0]
        return

    
    def compute_measurement_duration(self, x_res, y_res, width, return_slowness, move_time):
        """ Computes the time that the scan is supposed to last.
        
        @return str displaystr: str showing the expected measurement time
        """
        fwd = x_res*y_res*self.parameter_dict["Measurement time"][0]
        bwd = y_res*(width/return_slowness)*move_time
            
        self.duration = fwd+bwd
        displaystr = self.format_time(self.duration)
        return displaystr
    
    
    def acquisition(self, px_position):
        """
        Function called by the main scanning logic at each pixel.
        @param tuple px_position: x index, y index, position of the current px
        """
        counts = self.bricks_logic.get_PL(self.parameter_dict["Measurement time"][0])
        self.outputs["Topography"]["image"][px_position[1], px_position[0]] = counts[0]
        self.outputs["PL"]["image"][px_position[1], px_position[0]] = counts[1]
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
    
