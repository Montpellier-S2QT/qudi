# -*- coding: utf-8 -*-
""" 
This module is a logic containing "bricks" of measurement procedures
for scanning NV microscopy experiments. It is passed as an argument to
the procedure objects.

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

from logic.generic_logic import GenericLogic
from core.connector import Connector

from qtpy import QtCore

class NVMicroscopyBricksLogic(GenericLogic):
    
    _modclass = 'microscopybrickslogic'
    _modtype = 'logic'

    # declare connectors
    confocalscanner = Connector(interface='ConfocalScannerInterface') # to get the counts, not for moving
    microwave = Connector(interface='MicrowaveInterface')
    odmrlogic = Connector(interface='ODMRLogic')
    afm = Connector(interface='AFMZScannerInterface', optional=True)
    pulser = Connector(interface='PulserInterface', optional=True)
    pulsedlogic = Connector(interface='PulsedMasterLogic', optional=True)

    # signals

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)


     def on_activate(self):
        """ Initialization performed during activation of the module.
        """
        return


    def on_deactivate(self):
        """ Deinitialization performed during deactivation of the module.
        """
        return


    ###########
    # Actions #
    ###########

    def set_zscanner_position(self, scanner_state="retracted", relative_lift=None):
        """ Retracts or engage the afm zscanner, or set it at a given lift position, 
        after checking the surface position.
        
        @param str scanner_state: "engaged", "retracted" or "lifted". If you choose
                                  "lifted", you need to specify a lift value, 
                                  otherwise the scanner is retracted.
        @param float relative_lift: distance to set between the tip and the surface, 
                                    in m. If None, the scanner is retracted.
        """
        if self.afm() is None:
            self.log.error("No AFM scanner is connected, cannot set its position!")
            return
        else:
            pass

    
    def set_awg_trigger(self, channel, value, mode="rising"):
        """ Sets up the AWG trigger.
        
        @param str channel: designation of the trigger input channel
        @param float value: trigger level in V
        @param str mode: "rising" or "falling", to specify if the sequence should 
                         be triggered on the rising or the falling edge.
        """
        if self.pulser() is None:
            self.log.error("No pulser is connected, cannot set its trigger!")
        else:
            pass
    
    ################
    # Measurements #
    ################

    def get_PL(self, meas_time):
        """ Gets the PL value from the counter averaged over the requested time.

        @param float meas_time: duration of the PL measurement, in s.

        @return float Topovalue: measured topography in m.
        @return float PLvalue: measured PL rate in cts/s. 
        """
        return 


    def get_PL_with_MW(self, freq_list, power_list, total_meas_time):
        """ Gets the PL value at several MW frequencies (for iso-B for ex.).

        @param list freq_list: list of the desired MW frequencies, in Hz.
        @param list or float power_list: list of the desired MW power, either a
                                         single value or a list of the same length
                                         as freq_list.
        @param float total_meas_time: total duration of the measurement, each 
                                      frequency is accumulated during a this time 
                                      divided by the number of frequencies.

        @return float topo_value: measured topography in m.
        @return list PL_list: measured PL rates in cts/s. 
        """
        return


    def measure_ESR(self, start, stop, step, power, time_per_pt, nb_sweeps):
        """ Returns an ESR spectrum, possibly over several ranges.

        @param list or float start: start frequency for each range, in Hz. 
        @param list or float stop: stop frequency for each range, in Hz.
        @param float step: frequency step, in Hz.
        @param float power: MW power in dBm.
        @param float time_per_pt: time in s spent on each frequency 
                                  during one sweep. 
        @param int nb_sweeps: number of sweeps to average.

        @return float topo_value: measured topography in m.
        @return list freq_list: MW frequencies used for the spectrum, in Hz.
        @return list PL_list: measured PL rates in cts/s. 
        """
        return


    def run_pulsed_sequence(self, name, param_dict, meas_time):
        """ Runs a pulsed measurement, calling a predefined method.

        @param str name: name of the predefined method to use.
        @param dict param_dict: values of the parameters required by the
                                pulse sequence.
        @param float meas_time: total averaging time, in s.

        @return ndarray pulsed_data: result of the pulsed sequence.
        """
        if self.pulsedlogic() is None:
            self.log.error("No pulsed measurement logic is connected, cannot run a pulsed sequence!")
        else:
            pass
        return 
