import numpy as np
import PyDAQmx as daq

from core.module import Base
from core.configoption import ConfigOption
from interface.fast_counter_interface import FastCounterInterface

class NationalInstrumentsFastCounter(Base, FastCounterInterface):
    """ This is the implementation of the FastCounterInterface for the NI card.

    The NI card is used to measure the voltage from an APD through the analog input.
    The maximum frequency should be used, as the analog to digital converter does not allow slower/better measurement.
    As a result, the strategy here is to record as many point as possible in time and integrate using the usual qudi logic.

    The card is configured in the gated regime: the acquisition of a "gate" (i.e. time window) is started by a digital
    rising edge on a trigger channel. To acquire the multiple points of the time window at max speed, an "internal clock"
    is started, this is a series of N digital pulses at this frequency, with N being such that the "record_length" is acquired.

    """

    _trigger_channel = ConfigOption('analog_input', 'Dev1/PFI13', missing='error')
    _analog_input_channel = ConfigOption('analog_input', 'Dev1/AI8', missing='error')
    _clock_channel = ConfigOption('clock_channel', 'Dev1/Ctr3', missing='error')

    _min_voltage = ConfigOption('min_voltage', -10)  # The NI doc states this can help  PYDAQmx choose better settings
    _max_voltage = ConfigOption('max_votlage', 10)

    # This size of the hardware buffer where the values a stored between each readout from the logic.
    _buffer_size = ConfigOption('buffer_size', 10e6)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        self._status = 0

        self._bin_width_s = None
        self._record_length_s = None
        self._number_of_gates = None

        # Create the analog input task
        self._ai_task = daq.TaskHandle()
        daq.DAQmxCreateTask('CounterAnalogIn', daq.byref(self._ai_task))
        daq.DAQmxCreateAIVoltageChan(self._ai_task, self._analog_input_channel, 'fast_counter_ai',
                                     daq.DAQmx_Val_RSE, self._min_voltage, self._max_voltage, daq.DAQmx_Val_Volts, '')
        # We determine the fastcounter time bin from AI max sampling rate
        max_sampling_rate = daq.c_double()
        daq.DAQmxGetAIConvMaxRate(self._ai_task, daq.byref(max_sampling_rate))
        self._sampling_rate = max_sampling_rate.value
        self._timebin = 1/max_sampling_rate.value

        # Create the clock task
        self._clock_task = daq.TaskHandle()
        daq.DAQmxCreateTask('fast_counter_clock', daq.byref(self._clock_task))
        daq.DAQmxCreateCOPulseChanFreq(self._clock_task, self._clock_channel, 'fast_counter_clock', daq.DAQmx_Val_Hz,
                                       daq.DAQmx_Val_Low, 0, self._sampling_rate, 0.5)
        # Connect the clock task start to the external trigger
        daq.DAQmxCfgDigEdgeStartTrig(self._clock_task, self._trigger_channel, daq.DAQmx_Val_Rising)

        # start the AI ADC on clock ticks
        daq.DAQmxCfgSampClkTiming(self._ai_task, self._clock_channel+'InternalOutput', self._sampling_rate,
                                  daq.DAQmx_Val_Rising, daq.DAQmx_Val_ContSamps, self._buffer_size)


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.  """
        daq.DAQmxClearTask(self._ai_task)
        daq.DAQmxClearTask(self._clock_task)

    def get_constraints(self):
        return {'hardware_binwidth_list': [self._timebin]}

    def configure(self, bin_width_s, record_length_s, number_of_gates=0):

        self._gate_bin_size = int(record_length_s / bin_width_s)
        self._number_of_gates = number_of_gates
        self._full_bin_size = self._gate_bin_size * self._number_of_gates
        self._sum_voltages = np.zeros(self._full_bin_size)
        self._number_of_sweeps = 0
        self._buffer_incomplete_sweep = np.array([])

        daq.DAQmxCfgImplicitTiming(self._clock_task, daq.DAQmx_Val_FiniteSamps, self._gate_bin_size)

        self._status = 1  # idle
        return bin_width_s, self._gate_bin_size*bin_width_s, number_of_gates

    def get_status(self):
        return self._status

    def start_measure(self):
        daq.DAQmxStartTask(self._ai_task)
        daq.DAQmxStartTask(self._clock_task)
        self._status = 2

    def stop_measure(self):
        daq.DAQmxStopTask(self._ai_task)
        daq.DAQmxStopTask(self._clock_task)
        self._status = 1

    def pause_measure(self):
        self.stop_measure()

    def continue_measure(self):
        self.start_measure()

    def is_gated(self):
        return True

    def get_binwidth(self):
        return self._timebin

    def get_data_trace(self):
        """ Return the current time resolved data, which is the sum of the voltages since the beginning.
        We assume there is going to be several sweeps, i.e. complete acquisition loop.

        Here we record continuously the analog data, and we don't wait for one sweep to be finished.
        We just save the incomplete sweep data in a variable "buffer_incomplete_sweeps" and add them at the beginning
        of next loop.
        """
        try:
            raw_data = np.full(self._buffer_size, 0, dtype=np.float64)
            read_samples = daq.int32()
            daq.DAQmxReadAnalogF64(self._ai_task, -1, 10, daq.DAQmx_Val_GroupByChannel,
                                   raw_data, raw_data.size, daq.byref(read_samples), None)
            if read_samples > 0:
                raw_data = raw_data[:read_samples]
                raw_data = np.concatenate((self._buffer_incomplete_sweep, raw_data))
                number_of_new_full_sweep = len(raw_data) // self._full_bin_size
                if number_of_new_full_sweep > 0:
                    data_to_add = raw_data[:number_of_new_full_sweep*self._full_bin_size]
                    data_to_add = data_to_add.reshape((number_of_new_full_sweep, self._full_bin_size))
                    self._sum_voltages += data_to_add.sum(axis=0)
                    self._number_of_sweeps += number_of_new_full_sweep
                self._buffer_incomplete_sweep = raw_data[number_of_new_full_sweep*self._full_bin_size:]

            final_data = self._sum_voltages
            final_data = final_data.reshape((self._number_of_gates, self._gate_bin_size))
            info_dict = {'elapsed_sweeps': self._number_of_sweeps, 'elapsed_time': None}
            return final_data, info_dict

        except:
            self.log.exception('Getting samples from counter failed.')
