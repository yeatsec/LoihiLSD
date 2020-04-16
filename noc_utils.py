from collections import OrderedDict
import numpy as np

class SpikeMsg:

    def __init__(self, core_id, axon_ids, delay=1):
        """
        Parameters:
        core_id: destination core for this message
        axon_ids: list of destination axon_id instances
        delay: delay value for the message. may have additional delay added at destination
        """
        self.core_id = core_id
        self.axon_ids = axon_ids
        self.delay = delay
        self.traveled = False
        self.op = 'nop'

    def decrement_delay(self):
        self.delay -= 1
        assert self.delay != 0

    def set_traveled(self, b):
        self.traveled = b

    def get_traveled(self):
        return self.traveled

    def set_op(self, op):
        assert type(op) is type('I am a string')
        self.op = op

    def get_delay(self):
        return self.delay

    def __repr__(self):
        return 'SpikeMsg(core_id: {} axon_id: {} delay: {} op: {} tr: {})'.format(self.core_id, self.axon_ids, self.delay, self.op, self.traveled)

class Queue:

    def __init__(self, capacity=1000, decode = lambda msg: msg.set_op('nop'), pQ=True):
        self.buffer = []
        self.capacity = capacity
        self.decode = decode
        self.pQ = pQ

    def enqueue(self, msg):
        assert not self.is_full() # should not be calling this if buffer at capacity
        # do decode step here
        msg.set_traveled(True)
        self.decode(msg)
        self.buffer.append(msg) # do pQ stuff on op step

    def dequeue(self):
        assert not self.is_empty()
        return self.buffer.pop(0)

    def next_op_step(self):
        for i, msg in enumerate(self.buffer):
            msg.set_traveled(False)
            if self.pQ and msg.get_delay() == 1 and i > 0:
                self.buffer.insert(0, self.buffer.pop(i))

    def is_empty(self):
        return len(self.buffer) == 0

    def is_full(self, amt=1):
        return len(self.buffer)+amt-1 >= self.capacity

    def dec_delays(self):
        # iterate through the messages in the buffer and decrement delay
        if self.pQ:
            tmp = len(self.buffer)
            for i, msg in enumerate(self.buffer):
                msg.decrement_delay()
                msg.set_traveled(False)
                assert msg.get_delay() > 0
                if msg.get_delay() == 1:
                    self.buffer.insert(0, self.buffer.pop(i))
            assert len(self.buffer) == tmp
                    

    def __repr__(self):
        return str(self.buffer)

    def req(self):
        if self.is_empty():
            return 'nop', True # since this doesn't match the keys in the arbiter, it won't try to use it
        return self.buffer[0].op, self.buffer[0].get_traveled()

    def ready(self):
        if self.pQ and not self.is_empty():
            no_delay_one = True
            for msg in self.buffer:
                if no_delay_one and msg.get_delay() == 1:
                    no_delay_one = False
                    break
            return no_delay_one
        else:
            return self.is_empty()

    def get_util(self):
        return float(len(self.buffer))/self.capacity


class Router:
    """
    Class to define a router implementation.

    Contains:
        input link references
        output link references
        xbar instance
        selection/control logic/arbitration // handled by xbar
    """

    def __init__(self, router_id, keys=['north', 'east', 'south', 'west', 'local']):
        self.router_id = router_id
        #self.in_cap = in_cap
        self.arity = len(keys)
        self.keys = keys
        self.buffers = OrderedDict()
        self.sink_refs = OrderedDict()
        for key in keys:
            self.buffers[key] = Queue(decode=self.decode)
            self.sink_refs[key] = None
        self.xbar = None

    def set_sink_ref(self, key, ref):
        self.sink_refs[key] = ref

    def get_buffer_ref(self, key):
        return self.buffers[key]

    def initialize_crossbar(self):
        self.xbar = Crossbar(self.buffers, self.sink_refs)

    def operate(self):
        assert type(self.xbar) is Crossbar
        self.xbar.operate()

    def next_op_step(self):
        for buffkey in self.buffers.keys():
            self.buffers[buffkey].next_op_step()

    def decode(self, msg):
        if (msg.core_id == self.router_id):
                msg.set_op('local')
        elif (msg.core_id[0] != self.router_id[0]): # DOR is x then y
            if msg.core_id[0] > self.router_id[0]:
                msg.set_op('east')
            else:
                msg.set_op('west')
        else: # delta_y must be different
            if msg.core_id[1] > self.router_id[1]:
                msg.set_op('north')
            else:
                msg.set_op('south')

    def __repr__(self):
        basestr = 'Router ID: {}\n'.format(self.router_id)
        for key in self.keys:
            basestr += '{}: {}\n'.format(key, str(self.buffers[key]))
        return basestr

    def ready(self):
        r = True
        for buffkey in self.buffers.keys():
            if r:
                r = self.buffers[buffkey].ready() # if false, will break next iteration
            else:
                break
        return r

    def next_timestep(self):
        assert self.ready()
        for buffkey in self.buffers.keys():
            self.buffers[buffkey].dec_delays()

    def get_util(self):
        return np.asarray([[0.0, self.buffers['north'].get_util(), 0.0], \
            [self.buffers['west'].get_util(), 0.0, self.buffers['east'].get_util()], \
                [self.buffers['local'].get_util(), self.buffers['south'].get_util(), 0.0]], dtype=float)
        

class Arbiter:
    """
    Class which implements a simple arbiter to be combined with others in an allocator
    Each valid output link will have an arbiter that grants xbar access
    """
    
    def __init__(self, direction, in_buffs_dict, sink):
        """
        @param resource_dict: dictionary of resource refs
        """
        self.direction = direction
        self.resource_refs = in_buffs_dict
        self.sink = sink
        self.start_ind = 0

    def arbitrate(self):
        if (not self.sink.is_full()):
            msg = None
            for i, key in enumerate(self.resource_refs.keys()):
                mop, trav = self.resource_refs[key].req()
                if ((not trav) and i > self.start_ind and mop == self.direction):
                    self.start_ind = i
                    msg = self.resource_refs[key].dequeue()
            if msg is None: # loop back around
                for i, key in enumerate(self.resource_refs.keys()):
                    mop, trav = self.resource_refs[key].req()
                    if ((not trav) and i <= self.start_ind and mop == self.direction):
                        self.start_ind = i
                        msg = self.resource_refs[key].dequeue()
            if msg is not None: # send the message to its designated endpoint
                assert type(msg) is SpikeMsg
                self.sink.enqueue(msg)

class Crossbar:
    """
    Class which handles simultaneous point-to-point connection from all inputs to all outputs
    Contains arbiter objects that collectively handle crossbar resource allocation
    """

    def __init__(self, in_buffs_dict, sinks_dict):
        # store references to incoming buffers
        self.in_buff_refs = in_buffs_dict
        self.sink_refs = sinks_dict
        self.arbiters = {}
        for key in self.sink_refs.keys():
            self.arbiters[key] = Arbiter(key, self.in_buff_refs, self.sink_refs[key])

    def operate(self):
        for key in self.sink_refs.keys():
            self.arbiters[key].arbitrate()

