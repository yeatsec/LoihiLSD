from chip_utils import Chip 

chip = Chip(x_dim=2, y_dim=2)
chip.program_cores('mock.csv')
chip.run()
