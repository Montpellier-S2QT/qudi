import numpy as np
import PyDAQmx as daq

from core.module import Base
from interface.fast_counter_interface import FastCounterInterface

class NationalInstrumentsFastCounter(Base, FastCounterInterface):
    """ This is the implementation of the FastCounterInterface for the NI card. """

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self._task = None
        self._bin_width_s = None
        self._record_length_s = None
        self._number_of_gates = None

        self._timebin = 4e-6
        self._buffer_size = int(10e6)


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._status = 0
        self._counter_task = None
        self._clock_task = None

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        daq.DAQmxClearTask(self._clock_task)
        daq.DAQmxClearTask(self._counter_task)

    def get_constraints(self):
        constraints = dict()
        constraints['hardware_binwidth_list'] = [self._timebin]
        return constraints


    def configure(self, bin_width_s, record_length_s, number_of_gates=0):

        self.stop_measure()
        if self._counter_task is not None:
            daq.DAQmxClearTask(self._clock_task)
            daq.DAQmxClearTask(self._counter_task)

        clock_channel = "Dev1/ctr1"
        counter_channel = 'Dev1/ctr0'

        self._gate_bin_size = int(record_length_s / bin_width_s)
        self._number_of_gates = number_of_gates
        self._full_bin_size = self._gate_bin_size * self._number_of_gates
        self._sum_voltages = np.zeros(self._full_bin_size)
        self._number_of_sweeps = 0
        self._buffer_incomplete_sweep = np.array([])

        self._clock_task = daq.TaskHandle()
        daq.DAQmxCreateTask('fast_counter_clock', daq.byref(self._clock_task))
        daq.DAQmxCreateCOPulseChanFreq(self._clock_task, clock_channel, 'Clock Producer', daq.DAQmx_Val_Hz,
                                       daq.DAQmx_Val_Low, 0, int(1/self._timebin), 0.5)
        daq.DAQmxCfgImplicitTiming(self._clock_task, daq.DAQmx_Val_FiniteSamps, self._gate_bin_size)


        photon_source = "PFI8"
        self._counter_task = daq.TaskHandle()
        daq.DAQmxCreateTask('fast_counter', daq.byref(self._counter_task))
        daq.DAQmxCreateCICountEdgesChan(self._counter_task, counter_channel, 'Counter Channel',
                                        daq.DAQmx_Val_Rising, 0, daq.DAQmx_Val_CountUp)
        daq.DAQmxSetCICountEdgesTerm(self._counter_task, counter_channel, photon_source)
        daq.DAQmxCfgSampClkTiming(self._counter_task, 'PFI13', 250e3, daq.DAQmx_Val_Rising,
                                  daq.DAQmx_Val_ContSamps, self._gate_bin_size)
        daq.DAQmxSetReadRelativeTo(self._counter_task, daq.DAQmx_Val_CurrReadPos)
        daq.DAQmxSetReadOffset(self._counter_task, 0)
        daq.DAQmxSetReadOverWrite(self._counter_task, daq.DAQmx_Val_DoNotOverwriteUnreadSamps)

        self._status = 1  # idle
        return 4e-6, self._gate_bin_size*bin_width_s, number_of_gates

    def get_status(self):
        return self._status

    def start_measure(self):
        daq.DAQmxStartTask(self._counter_task)
        daq.DAQmxStartTask(self._clock_task)
        self._status = 2

    def stop_measure(self):
        if self._counter_task is not None:
            daq.DAQmxStopTask(self._counter_task)
            daq.DAQmxStopTask(self._clock_task)
        self._status = 1

    def pause_measure(self):
        self.stop_measure()

    def continue_measure(self):
        self.start_measure

    def is_gated(self):
        return False

    def get_binwidth(self):
        return 4e-6

    def get_data_trace(self):

        try:
            raw_count_data = np.empty(self._buffer_size, dtype=np.uint32)
            n_read_samples = daq.int32()  # number of samples which were actually read, will be stored her
            # read the counter value: This function is blocking and waits for the counts to be all filled
            daq.DAQmxReadCounterU32(self._counter_task, -1, 10, raw_count_data, self._buffer_size,
                                    daq.byref(n_read_samples), None)
            raw_count_data = raw_count_data[:int(n_read_samples)]
            number_of_full_sweep = int(n_read_samples) // self._full_bin_size
            if number_of_full_sweep > 0:
                data_to_add_now = raw_count_data[:number_of_full_sweep*self._full_bin_size]
                data_to_add_now = data_to_add_now.reshape((number_of_full_sweep, self._full_bin_size))
                self._sum_voltages += data_to_add_now.sum(axis=0)
                self._number_of_sweeps += number_of_full_sweep
            data_to_add_later = raw_count_data[number_of_full_sweep*self._full_bin_size:]
            if len(data_to_add_later) > 0:
                self._buffer_incomplete_sweep = np.concatenate((self._buffer_incomplete_sweep, data_to_add_later))
                if len(self._buffer_incomplete_sweep) >= self._full_bin_size:
                    data_to_add_now = self._buffer_incomplete_sweep[:self._full_bin_size]
                    self._buffer_incomplete_sweep = self._buffer_incomplete_sweep[:self._full_bin_size]
                    self._sum_voltages += data_to_add_now
                    self._number_of_sweeps += 1

            final_data = self._sum_voltages / self._number_of_sweeps

            return final_data.reshape((self._number_of_gates, self._gate_bin_size))

        except:
            self.log.exception('Getting samples from counter failed.')
