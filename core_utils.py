from noc_utils import Queue
import numpy as np

MAX_DELAY = 64
MIN_DELAY = 1
COMPARTMENTS_PER_CORE = 1024

# ripped from nengo_loihi
def overflow_signed(x, bits=7, out=None):
    """Compute overflow on an array of signed integers.

    For example, the Loihi chip uses 23 bits plus sign to represent U.
    We can store them as 32-bit integers, and use this function to compute
    how they would overflow if we only had 23 bits plus sign.

    Parameters
    ----------
    x : array
        Integer values for which to compute values after overflow.
    bits : int
        Number of bits, not including sign, to compute overflow for.
    out : array, optional (Default: None)
        Output array to put computed overflow values in.

    Returns
    -------
    y : array
        Values of x overflowed as would happen with limited bit representation.
    overflowed : array
        Boolean array indicating which values of ``x`` actually overflowed.
    """
    if out is None:
        out = np.array(x)
    else:
        assert isinstance(out, np.ndarray)
        out[:] = x

    assert np.issubdtype(out.dtype, np.integer)

    x1 = np.array(1, dtype=out.dtype)
    smask = np.left_shift(x1, bits)  # mask for the sign bit (2**bits)
    xmask = smask - 1  # mask for all bits <= `bits`

    # find whether we've overflowed
    overflowed = (out < -smask) | (out >= smask)

    zmask = out & smask  # if `out` has negative sign bit, == 2**bits
    out &= xmask  # mask out all bits > `bits`
    out -= zmask  # subtract 2**bits if negative sign bit

    return out, overflowed


DTYPE = np.int32

class Core:
    """"""
    def __init__(self, core_id):
        self.core_id = core_id
        
        # variables
        self.input = np.zeros((MAX_DELAY, COMPARTMENTS_PER_CORE), dtype=DTYPE)


    # taken from nengo_loihi emulator
    def advance_input(self):
        self.input[:-1] = self.input[1:]
        self.input[-1] = 0



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