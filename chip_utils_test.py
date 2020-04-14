from chip_utils import Chip 

chip = Chip(x_dim=4, y_dim=4)
chip.program_cores('out4x4.csv')
chip.run()
