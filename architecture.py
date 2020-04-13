import numpy as np
from noc_utils import SpikeMsg, Queue, Router
from core_utils import Core

opp_map = {
    'north': 'south',
    'east': 'west',
    'west': 'east',
    'south': 'north',
    'local': 'local'
}
class SimController:

    def __init__(self):
        self.tmax = None
        self.tstep = 0
    
    def inc_tstep(self):
        assert self.tstep < self.tmax
        self.tstep += 1

    def set_tmax(self, value):
        self.tmax = value
        self.tstep = 0

class Chip:
    """
    Class that maps cores to routers and defines the topology of the system
    """
    def __init__(self, x_dim, y_dim):
        self.controller = SimController()
        self.x_dim = x_dim
        self.y_dim = y_dim
        self.cores = []
        self.routers = []
        for x in range(self.x_dim):
            for y in range(self.y_dim):
                self.cores.append(Core((x, y)))
                self.routers.append(Router((x, y), in_cap=50))
        directions = ['north', 'east', 'south', 'west', 'local']
        self.buffers = {}
        self.sink_refs = {}
        for d in directions:
            self.buffers[d] = Queue(capacity=1) # TODO - if multi-chip, will need to make decode more flexible
            self.sink_refs[d] = Queue(capacity=1)
        for x in range(x_dim):
            for y in range(y_dim):
                i = y + (x * self.y_dim)
                if (x == 0):
                    self.routers[i].set_sink_ref('west', self.sink_refs['east'])
                else:
                    self.routers[i].set_sink_ref('west', self.routers[i-self.y_dim].get_buffer_ref('east'))
                if (x == x_dim-1):
                    self.routers[i].set_sink_ref('east', self.sink_refs['west'])
                else:
                    self.routers[i].set_sink_ref('east', self.routers[i+self.y_dim].get_buffer_ref('west'))
                if (y == 0):
                    self.routers[i].set_sink_ref('south', self.sink_refs['north'])
                else:
                    self.routers[i].set_sink_ref('south', self.routers[i-1].get_buffer_ref('north'))
                if (y == y_dim-1):
                    self.routers[i].set_sink_ref('north', self.sink_refs['south'])
                else:
                    self.routers[i].set_sink_ref('north', self.routers[i+1].get_buffer_ref('south'))
                self.routers[i].set_sink_ref('local', self.cores[i].get_buffer_ref())
            for router in self.routers:
                router.initialize_crossbar()

    def operate(self):
        advance_timestep = True
        # first iterate through the matrix of cores and operate
        for core in self.cores:
            flag = core.operate()
            if advance_timestep:
                advance_timestep = flag
        # iterate through the routers and operate
        for router in self.routers:
            flag = router.operate()
            if advance_timestep:
                advance_timestep = flag
        if advance_timestep:
            self.controller.inc_tstep()
            
    def ready(self):
        is_ready = True
        for core in self.cores:
            if is_ready:
                is_ready = core.ready()
        if is_ready:
            for router in self.routers:
                if is_ready:
                    is_ready = router.ready()
        return is_ready

    