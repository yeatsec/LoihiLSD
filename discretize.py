import numpy as np

# q bits for synapse accumulator
Q_BITS = 21
# u bits for current variable
U_BITS = 23

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

    assert np.issubdtype(out.dtype, np.integer)
    x1 = np.array(1, dtype=out.dtype)
    smask = np.left_shift(x1, bits)  # mask for the sign bit (2**bits)
    xmask = smask - 1  # mask for all bits <= `bits`

    # find whether we've overflowed
    overflowed = (out < -smask) | (out >= smask)

    zmask = out & smask  # if `out` has negative sign bit, == 2**bits
    out &= xmask  # mask out all bits > `bits`
    out -= zmask  # subtract 2**bits if negative sign bit
    if (overflowed):
        print("Overflowed!")

# modified to only operate on scalar values
def decay_int(x, decay, bits=12, offset=0):
    """Decay integer values using a decay constant.

    The decayed value is given by::

        sign(x) * floor(abs(x) * (2**bits - offset - decay) / 2**bits)
    """
    r = (2 ** bits - offset - np.int64(decay))
    return np.sign(x) * np.right_shift(np.abs(x) * r, bits)
