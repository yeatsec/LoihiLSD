
class SpikeMsg:

    def __init__(self, core_id, axon_ids, delay=None):
        """
        Parameters:
        core_id: destination core for this message
        axon_ids: list of destination axon_id instances
        delay: delay value for the message. may have additional delay added at destination
        """
        self.core_id = core_id
        self.axon_ids = axon_ids
        self.delay = delay
        self.op = 'nop'

    def decrement_delay(self):
        self.delay -= 1
        assert self.delay != 0

    def set_op(self, op):
        assert type(op) is type('I am a string')
        self.op = op

    def __repr__(self):
        return 'SpikeMsg(core_id: {} axon_id: {} delay: {} op: {})'.format(self.core_id, self.axon_id, self.delay, self.op)

class Queue:

    def __init__(self, capacity=50, decode = lambda msg: msg.set_op('nop')):
        self.buffer = []
        self.capacity = capacity
        self.decode = decode

    def enqueue(self, msg):
        assert not self.is_full() # should not be calling this if buffer at capacity
        # do decode step here
        self.decode(msg)
        self.buffer.append(msg)

    def dequeue(self):
        assert not self.is_empty()
        return self.buffer.pop(0)

    def is_empty(self):
        return len(self.buffer) == 0

    def is_full(self):
        return len(self.buffer) == self.capacity

    def dec_delays(self):
        # iterate through the messages in the buffer and decrement delay
        for i, msg in enumerate(self.buffer):
            msg.decrement_delay()

    def __repr__(self):
        return str(self.buffer)

    def req(self):
        if self.is_empty():
            return 'nop' # since this doesn't match the keys in the arbiter, it won't try to use it
        return self.buffer[0].op

    def ready(self):
        return self.is_empty()


class Router:
    """
    Class to define a router implementation.

    Contains:
        input link references
        output link references
        xbar instance
        selection/control logic/arbitration // handled by xbar
    """

    def __init__(self, router_id, keys=['north', 'east', 'south', 'west', 'local'], in_cap=50, pQ=False):
        self.router_id = router_id
        self.in_cap = in_cap
        self.arity = len(keys)
        self.keys = keys
        self.buffers = {}
        self.sink_refs = {}
        for key in keys:
            self.buffers[key] = Queue(capacity=in_cap, decode=self.decode)
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
        for buff in self.buffers:
            if r:
                r = buff.ready() # if false, will break next iteration
            else:
                break
        return r
        

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
                if (i > self.start_ind and self.resource_refs[key].req() == self.direction):
                    self.start_ind = i
                    msg = self.resource_refs[key].dequeue()
            if msg is None: # loop back around
                for i, key in enumerate(self.resource_refs.keys()):
                    if (i <= self.start_ind and self.resource_refs[key].req() == self.direction):
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

