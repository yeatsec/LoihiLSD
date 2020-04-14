from chip_utils import Chip 
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.animation as animation
from matplotlib.colors import hsv_to_rgb

util_arr = []
dim = (4, 4)
chip = Chip(x_dim=dim[0], y_dim=dim[1], util_arr=util_arr)
chip.program_cores('out4x4.csv')
chip.run()
last_nrn_vs = chip.get_last_nrn_vs()
tmax = chip.controller.tmax

# def plot_util(_util_arr, _dim):
#     fig = plt.figure()
#     ims = []
#     for i, frame in enumerate(_util_arr):
#         img = np.empty((_dim[0]*3, _dim[1]*3), dtype=float)
#         for r, r_img in enumerate(frame):
#             coor = chip.get_coor(r)
#             print(r_img)
#             img[(_dim[1]-1-coor[1])*3:(_dim[1]-coor[1])*3, (coor[0]*3):(coor[0]+1)*3] = r_img
#             im = plt.imshow(img, animated=True, vmin=0.0, vmax=1.0)
#             ims.append([im])

#     ani = animation.ArtistAnimation(fig, ims, interval=50, blit=True,
#                                 repeat_delay=1000)
#     #ani.save('test.mp4')
#     plt.show()

# plot_util(util_arr, dim)

for i, last_nrn_v in enumerate(last_nrn_vs[:10]):
    plt.figure()
    plt.title('Core #{} Core_ID: {}'.format(i, chip.get_coor(i)))
    plt.plot(range(tmax), last_nrn_v, linewidth=2)
    plt.ylim((0, np.amax(last_nrn_vs[:10])+100))
    plt.xlabel('Timesteps')
    plt.ylabel('Voltage')
    plt.savefig('.\\figures\\{}.png'.format(i), dpi=100)
    plt.show()

for i, last_nrn_v in enumerate(last_nrn_vs[10:]):
    plt.figure()
    plt.title('Core #{} Core_ID: {}'.format(i, chip.get_coor(i)))
    plt.plot(range(tmax), last_nrn_v, linewidth=2)
    plt.ylim((0, np.amax(last_nrn_vs[10:])+100))
    plt.xlabel('Timesteps')
    plt.ylabel('Voltage')
    plt.savefig('.\\figures\\spikes.png', dpi=100)