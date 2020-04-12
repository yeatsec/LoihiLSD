from noc_utils import Queue, SpikeMsg
import numpy as np
from discretize import overflow_signed, decay_int, U_BITS

MAX_DELAY = 64
MIN_DELAY = 1
COMPARTMENTS_PER_CORE = 1024
MAX_AXON_IN = 4096
MAX_AXON_OUT = 4096
MAX_FAN_IN_STATE = 16384 # synapses 128KByte/8Byte


DTYPE = np.int32

class SynapseState:

    def __init__(self, neuron_id, weight, delay): # tag unused
        self.neuron_id = neuron_id
        self.weight = weight
        self.delay = delay

    def get_neuron_id(self):
        return self.neuron_id

    def get_weight(self):
        return self.weight

    def get_delay(self):
        return self.delay

class Core:
    """"""
    def __init__(self, core_id, n_neurons):
        self.core_id = core_id
        self.n_neurons = n_neurons
        self.in_buffer = Queue()
        self.out_buffer = Queue(capacity=MAX_AXON_OUT) # worst case buffering
        self.cur_nrn = 0
        # variables
        self.axon_in = {} # map of axon_in to list of synapses, each synapse has a delay
        self.input = np.zeros((MAX_DELAY, self.n_neurons), dtype=DTYPE)
        self.current = np.zeros(self.n_neurons, dtype=DTYPE)
        self.voltage = np.zeros(self.n_neurons, dtype=DTYPE)
        self.decay_u = np.full(self.n_neurons, np.nan, dtype=DTYPE)
        self.decay_v = np.full(self.n_neurons, np.nan, dtype=DTYPE)
        self.vth = np.full(self.n_neurons, np.nan, dtype=DTYPE)
        self.vmin = np.full(self.n_neurons, np.nan, dtype=DTYPE)
        self.vmax = np.full(self.n_neurons, np.nan, dtype=DTYPE)

        self.bias = np.full(self.n_neurons, np.nan, dtype=DTYPE)
        self.ref = np.full(self.n_neurons, np.nan, dtype=DTYPE)

        # discretization methods
        self._decay_current = lambda x, u: decay_int(x, self.decay_u, offset=1) + u
        self._decay_voltage = lambda x, u: decay_int(x, self.decay_v) + u
        self._overflow = lambda x, b: overflow_signed(x, bits=b, out=x)

    # taken from nengo_loihi emulator
    def advance_input(self):
        self.input[:-1] = self.input[1:]
        self.input[-1] = 0

    def program(self):
        pass

    def process_msg(self):
        if not self.in_buffer.is_empty():
            msg = self.in_buffer.dequeue()
            for ax_in in msg.axon_ids: # index into synapse state
                synapse_list = self.axon_in[ax_in]
                for syn in synapse_list:
                    self.input[syn.get_delay()][syn.get_neuron_id()] += syn.get_weight() # TODO - quantization

    def process_neuron(self):
        if self.cur_nrn < self.n_neurons and not self.out_buffer.is_full():
            # add input to current and decay
            self.current[self.cur_nrn] = self.decay_u(self.current[self.cur_nrn], \
                self.input[0][self.cur_nrn])
            self._overflow(self.current[self.cur_nrn], U_BITS)
            self.voltage[self.cur_nrn] = self.decay_v(self.voltage[self.cur_nrn], \
                self.current[self.cur_nrn])
            self.voltage[self.cur_nrn] = np.clip(self.voltage[self.cur_nrn], \
                self.vmin[self.cur_nrn], self.vmax[self.cur_nrn])
            if (self.voltage[self.cur_nrn] > self.vth[self.cur_nrn]): # spike
                self.voltage[self.cur_nrn] = 0
                # create spike message(s)
                for smsg_data in self.out_axon_state[self.cur_nrn]:
                    self.out_buffer.enqueue(SpikeMsg(smsg_data[0], smsg_data[1], delay=smsg_data[2]))

    def ready(self):
        return self.cur_nrn == self.n_neurons and self.in_buffer.ready() and self.out_buffer.ready()



# FROM NENGO_LOIHI
# self.compartment.advance_input()
# self.synapses.inject_current(
#     self.t, self.inputs, self.axons, self.compartment.spiked
# )
# self.synapses.update_input(self.compartment.input)
# self.synapses.update_traces(self.t, self.rng)
# self.synapses.update_weights(self.t, self.rng)
# self.compartment.update(self.rng)
# self.probes.update(self.t, self.compartment)