from architecture import Chip

class ChipProgrammer:
    """
    Given a reference to a Chip object and a document that specifies network and simulation parameters, set up the network and simulation on the virtual chip
    """

    def __init__(self, simfile, chip_ref):
        self.chip