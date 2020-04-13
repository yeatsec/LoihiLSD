from core_utils import SynapseState, Core
from noc_utils import Router, Queue, SpikeMsg

# set up the test
core = Core((0, 0))
router = Router((0, 0))
router.set_sink_ref('local', core.get_sink_ref())
core.set_sink_ref(router.get_buffer_ref('local'))
q = Queue()
router.set_sink_ref('north', q)
router.set_sink_ref('east', q)
router.set_sink_ref('south', q)
router.set_sink_ref('west', q)

router.initialize_crossbar()
# router should be ready

# set up neural simulation
core.add_neuron(0.5, 0.9, 100.0, bias=50.0)
core.add_axon_out(0, ((0, 0), [0], 1))
core.add_synapse_in(0, SynapseState(0, -50.0, 7))
core.prepare_computation() # core ready

# simulation loop
for tstep in range(100):
    opstep = 0
    while(not core.ready() or not router.ready()):
        print('tstep: {}\topstep: {}'.format(tstep, opstep))
        core.operate()
        #print('neuron v: {}'.format(core.voltage[0]))
        print(router)
        router.operate()
        opstep += 1
    core.next_timestep()

