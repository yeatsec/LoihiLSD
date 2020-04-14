from collections import OrderedDict
from core_utils import Core, SynapseState
import csv
import numpy as np

DTYPE = np.float32

class ChipProgrammer:
    """
    Given a reference to a Chip object and a document that specifies network and simulation parameters, set up the network and simulation on the virtual chip
    file should look like:
    simcontroller <tmax> 
    neuron nrn_id, x_coor, y_coor, decay_u, decay_v, vth, bias=0, bias_delay=0, vmin=0, vmax=np.inf
    synapse src_nrn_id, dst_nrn_id, weight, delay_pre, delay_post, 
    """

    def __init__(self, simfile, chip_ref):
        self.chip_ref = chip_ref
        self.simfile = simfile
        self.chip_dim = (chip_ref.x_dim, chip_ref.y_dim)
        self.nrn_id_to_core_axon_map = {}

    def program(self):
        # open csv file
        fhandle = open(self.simfile, mode='r')
        csvfile = csv.reader(fhandle, delimiter=' ')
        for i, line in enumerate(csvfile):
            if i == 0:
                assert line[0] == 'simcontroller'
                self.chip_ref.controller.set_tmax(int(line[1]))
            elif line[0] == 'neuron': # neuron or synapse
                nrn_id = int(line[1])
                x_coor = int(line[2])
                y_coor = int(line[3])
                decay_u = DTYPE(line[4])
                decay_v = DTYPE(line[5])
                vth = DTYPE(line[6])
                print('vth: {}'.format(vth))
                bias = DTYPE(line[7])
                bias_delay = np.int32(line[8])
                vmin = DTYPE(line[9])
                vmax = np.inf # TODO - hard programmed - better solution?
                nrn_core_loc = self.chip_ref.cores[self.chip_ref.get_ind(x_coor, y_coor)].add_neuron(decay_u, decay_v, vth, bias=bias, bias_delay=bias_delay, vmin=vmin, vmax=vmax)
                self.nrn_id_to_core_axon_map[nrn_id] = {'nrn_core_loc': nrn_core_loc, 'core_id': (x_coor, y_coor), 'eff_axon_id': nrn_id, 'delay': None}
            elif line[0] == 'synapse': # at this point, the nrn ids
                src_nrn_id = int(line[1])
                dst_nrn_id = int(line[2])
                weight = DTYPE(line[3])
                delay_pre = int(line[4])
                delay_post = int(line[5])
                # must set up axon out in pre_core
                src_core_id = self.nrn_id_to_core_axon_map[src_nrn_id]['core_id']
                dst_core_id = self.nrn_id_to_core_axon_map[dst_nrn_id]['core_id']
                src_ind = self.chip_ref.get_ind(src_core_id[0], src_core_id[1])
                self.chip_ref.cores[src_ind].add_axon_out(self.nrn_id_to_core_axon_map[src_nrn_id]['nrn_core_loc'], (dst_core_id, [src_nrn_id], delay_pre))
                # must set up axon in in post_core
                dst_ind = self.chip_ref.get_ind(dst_core_id[0], dst_core_id[1])
                self.chip_ref.cores[dst_ind].add_synapse_in(src_nrn_id, SynapseState(
                    self.nrn_id_to_core_axon_map[dst_nrn_id]['nrn_core_loc'],
                    weight,
                    delay_post))
            else:
                pass
        # close csv file
        fhandle.close()