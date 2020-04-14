from noc_utils import Queue, SpikeMsg
import numpy as np
from discretize import overflow_signed, decay_int, U_BITS

MAX_DELAY = 64
MIN_DELAY = 1
COMPARTMENTS_PER_CORE = 1024
MAX_AXON_IN = 4096
MAX_AXON_OUT = 4096
MAX_FAN_IN_STATE = 16384 # synapses 128KByte/8Byte


DTYPE = np.float32 # TODO - discretization

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

    def __repr__(self):
        return 'nrn_id: {} wgt: {} dly: {}'.format(self.neuron_id, self.weight, self.delay)

class Core:
    """"""
    def __init__(self, core_id, tstep_ref_func):
        self.core_id = core_id
        self.cur_tstep = tstep_ref_func
        self.n_neurons = 0
        self.n_axon_out = 0
        self.n_synapse_in = 0
        self.in_buffer = Queue()
        self.out_buffer = Queue(capacity=MAX_AXON_OUT) # worst case buffering
        self.noc_ref = None
        self.cur_nrn = 0
        # variables
        self.axon_in = dict() # map of axon_in to list of synapses, each synapse has a delay
        self.axon_out = dict()
        self.input = None
        self.current = []
        self.voltage = []
        self.decay_u = []
        self.decay_v = []
        self.vth = []
        self.vmin = []
        self.vmax = []
        self.bias = []
        self.bias_delay = []

        # discretization methods
        # self._decay_current = lambda x, u: decay_int(x, self.decay_u, offset=1) + u
        # self._decay_voltage = lambda x, u: decay_int(x, self.decay_v) + u
        # self._overflow = lambda x, b: overflow_signed(x, bits=b, out=x)
        self._decay_current = lambda ind: self.current[ind] * self.decay_u[ind] + self.input[0][ind]
        self._decay_voltage = lambda ind, c: self.voltage[ind] * self.decay_v[ind] + c

    # taken from nengo_loihi emulator
    def advance_input(self):
        self.input[:-1] = self.input[1:]
        self.input[-1] = 0

    def next_timestep(self):
        self.advance_input()
        self.cur_nrn = 0

    def get_sink_ref(self):
        return self.in_buffer

    def set_sink_ref(self, ref):
        self.noc_ref = ref

    def add_synapse_in(self, ax_in, synapse_state):
        # synapse is part of an axon_in list
        if not ax_in in self.axon_in:
            self.axon_in[ax_in] = []
        self.axon_in[ax_in].append(synapse_state)
        # synapse contains weight, delay, and target neuron id
        self.n_synapse_in += 1

    def add_axon_out(self, neuron_id, spike_msg_data):
        """
        add_axon_out - add efferent spike message to another core
        neuron_id: id of src neuron
        spike_msg_data: tuple containing SpikeMsg state
            core_id: (x, y) tuple for destination core
            axon_ids: list of axon_ids within dst core that this message targets
            delay: optional delay variable. default is 1, the minimum delay
        """
        assert spike_msg_data[2] <= MAX_DELAY
        assert spike_msg_data[2] >= MIN_DELAY
        if not neuron_id in self.axon_out.keys():
            self.axon_out[neuron_id] = []
        self.axon_out[neuron_id].append(spike_msg_data)
        self.n_axon_out += 1

    def add_neuron(self, decay_u, decay_v, vth, bias=0, bias_delay=0, vmin=0, vmax=np.inf):
        self.n_neurons += 1
        assert self.n_neurons <= COMPARTMENTS_PER_CORE
        self.decay_u.append(decay_u)
        self.decay_v.append(decay_v)
        self.vth.append(vth)
        self.vmin.append(vmin)
        self.vmax.append(vmax)
        self.bias.append(bias)
        self.bias_delay.append(bias_delay)
        return self.n_neurons - 1

    def prepare_computation(self):
        assert self.n_neurons <= COMPARTMENTS_PER_CORE
        assert len(self.axon_in.keys()) <= MAX_AXON_IN
        assert self.n_axon_out <= MAX_AXON_OUT
        assert self.n_synapse_in <= MAX_FAN_IN_STATE
        self.cur_nrn = 0
        self.input = np.zeros((MAX_DELAY, self.n_neurons), dtype=DTYPE)
        self.current = np.zeros(self.n_neurons, dtype=DTYPE)
        self.voltage = np.zeros(self.n_neurons, dtype=DTYPE)
        self.decay_u = np.asarray(self.decay_u, dtype=DTYPE)
        self.decay_v = np.asarray(self.decay_v, dtype=DTYPE)
        self.vth = np.asarray(self.vth, dtype=DTYPE)
        self.vmin = np.asarray(self.vmin, dtype=DTYPE)
        self.vmax = np.asarray(self.vmax, dtype=DTYPE)
        self.bias = np.asarray(self.bias, dtype=DTYPE)
        self.bias_delay = np.asarray(self.bias_delay, dtype=np.int32)

    def process_noc(self):
        # fill in_buffer
        if not self.out_buffer.is_empty() and not self.noc_ref.is_full():
            self.noc_ref.enqueue(self.out_buffer.dequeue())
        # out_buffer will be emptied by the Router

    def process_msg(self):
        if not self.in_buffer.is_empty():
            msg = self.in_buffer.dequeue()
            print('Process message! {}'.format(str(msg)))
            for ax_in in msg.axon_ids: # index into synapse state
                print(self.axon_in)
                synapse_list = self.axon_in[ax_in]
                for syn in synapse_list:
                    self.input[syn.get_delay() + msg.get_delay()][syn.get_neuron_id()] += syn.get_weight() # TODO - quantization

    @staticmethod
    def clip(_val, _min, _max):
        if _val > _max:
            return _max
        if _val < _min:
            return _min
        return _val

    def process_neuron(self):
        if self.cur_nrn < self.n_neurons and not self.out_buffer.is_full():
            # add input to current and decay
            self.current[self.cur_nrn] = self._decay_current(self.cur_nrn)
            # self._overflow(self.current[self.cur_nrn], U_BITS)
            c_b = self.current[self.cur_nrn]
            # only add the bias if the delay is passed
            if self.cur_tstep() >= self.bias_delay[self.cur_nrn]:
                c_b += self.bias[self.cur_nrn]
            # self._overflow(self.current[self.cur_nrn], U_BITS)
            self.voltage[self.cur_nrn] = self._decay_voltage(self.cur_nrn, c_b)
            self.voltage[self.cur_nrn] = Core.clip(self.voltage[self.cur_nrn], self.vmin[self.cur_nrn], \
                self.vmax[self.cur_nrn])
            if (self.voltage[self.cur_nrn] > self.vth[self.cur_nrn]): # spike
                self.voltage[self.cur_nrn] = 0.0
                # create spike message(s)
                if self.cur_nrn in self.axon_out.keys(): # prevent KeyError
                    for smsg_data in self.axon_out[self.cur_nrn]:
                        self.out_buffer.enqueue(SpikeMsg(smsg_data[0], smsg_data[1], delay=smsg_data[2]))
            self.cur_nrn += 1 # program counter for next neuron

    def ready(self):
        return self.cur_nrn == self.n_neurons and self.in_buffer.ready() and self.out_buffer.ready()

    def advance_timestep(self):
        assert self.ready()
        self.cur_nrn = 0
        self.advance_input()

    def operate(self):
        self.process_neuron()
        self.process_noc()
        self.process_msg()
