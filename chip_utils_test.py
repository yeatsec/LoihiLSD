from chip_utils import Chip 

chip = Chip(x_dim=1, y_dim=1)
chip.program_cores('mock.csv')
chip.run()
