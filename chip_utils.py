import numpy as np
from noc_utils import SpikeMsg, Queue, Router
from core_utils import Core
from chip_programmer import ChipProgrammer

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

    def get_tstep(self):
        return self.tstep
    
    def inc_tstep(self):
        assert self.tstep < self.tmax
        self.tstep += 1

    def set_tmax(self, value):
        self.tmax = value
        self.tstep = 0

    def conditional_run(self):
        return self.tstep < self.tmax

class Chip:
    """
    Class that maps cores to routers and defines the topology of the system
    """
    def __init__(self, x_dim=4, y_dim=4):
        self.controller = SimController()
        self.x_dim = x_dim
        self.y_dim = y_dim
        self.get_ind = lambda x, y: y + (x * self.y_dim) # for iterating x outer, y inner
        self.cores = []
        self.routers = []
        for x in range(self.x_dim):
            for y in range(self.y_dim):
                self.cores.append(Core((x, y), self.controller.get_tstep))
                self.routers.append(Router((x, y), in_cap=50))
        directions = ['north', 'east', 'south', 'west', 'local']
        self.buffers = {}
        self.sink_refs = {}
        for d in directions:
            self.buffers[d] = Queue(capacity=1) # TODO - if multi-chip, will need to make decode more flexible
            self.sink_refs[d] = Queue(capacity=1)
        for x in range(x_dim):
            for y in range(y_dim):
                i = self.get_ind(x, y)
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
                self.routers[i].set_sink_ref('local', self.cores[i].get_sink_ref())
                self.cores[i].set_sink_ref(self.routers[i].get_buffer_ref('local'))
            for router in self.routers:
                router.initialize_crossbar()
            # TODO - initialize cores appropriately
            # add neurons, synapses to cores

    def program_cores(self, filename):
        self.programmer = ChipProgrammer(filename, self)
        self.programmer.program()
        # call prepare_computation() on all the cores
        for core in self.cores:
            core.prepare_computation()

    def operate(self):
        if (self.controller.conditional_run()):
            while(not self.ready()):
                # first iterate through the matrix of cores and operate
                for core in self.cores:
                    core.operate()
                    print(core.voltage)
                # iterate through the routers and operate
                for router in self.routers:
                    router.operate()
                    print(router)
            self.controller.inc_tstep()
            for core in self.cores:
                core.advance_timestep()

    def run(self):
        while(self.controller.conditional_run()):
            print("tstep: {}".format(self.controller.get_tstep()))
            self.operate()
            
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

    