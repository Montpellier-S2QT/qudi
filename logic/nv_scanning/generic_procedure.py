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

class GenericProcedure(object):
    """ Object defining a generic measurement procedure, 
    helping you to build the one you need.
    """

    def __init__(self, name, bricks_logic):
        """ The constructor for a scanning procedure needs the name of the 
        procedure and a NVMicroscopyBricksLogic.

        @param str name: name of the procedure (like "Quenching").
        @param NVMicroscopyBricksLogic bricks_logic: logic connected to the 
               hardware and defining all the basic operations.
        """
        parameter_dict = {} # dict of 2-tuples (value, unit)
        outputs_list = ["Topo"] # list of the generated data channels to plot 
        pass

    
    def scan_init(self):
        """
        The initial steps to perform before starting the scan itself.
        For example, starting the MW, setting up the AWG trigger, etc.
        """
        return

    
    def acquisition(self):
        """
        Function called by the main scanning logic at each pixel.

        @return OrderedDict pixel_outputs: the keys should be the items 
                of outputs_list.
        """
        return pixel_outputs


    def scan_end(self):
        """
        The final steps to perform after finishing the scan itself.
        For example, stopping the MW, etc.
        """
        return
    
