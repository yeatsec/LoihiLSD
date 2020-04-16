import numpy as np
import matplotlib.pyplot as plt

buffer_sizes = [10, 50, 100, 500, 1000]

reg_cyc = [49858, 48164, 48516, 48570, 48570]

prio_cyc = [46824, 36757, 33639, 28905, 28507]


plt.figure()
plt.title('Cycle Count Comparison for Inference Task Tmax=160')
plt.ylabel('Cycle Count')
plt.xlabel('Buffer Size')
plt.plot(buffer_sizes, reg_cyc, label='Regular Queues', color='b', linewidth=2)
plt.plot(buffer_sizes, prio_cyc, label='Priority Queues', color='r', linewidth=2)
plt.legend()
plt.savefig('comparison.png', dpi=200)
plt.show()

for i, reg in enumerate(reg_cyc):
    prio_cyc[i] = 1/(float(prio_cyc[i])/reg)

plt.figure()
plt.bar([1, 2, 3, 4, 5], prio_cyc)
plt.title('Speedup Normalized to Regular Queue Impl')
plt.ylabel('Speedup')
plt.xticks(ticks=[1, 2, 3, 4, 5], labels=[10, 50, 100, 500, 1000])
plt.xlabel('Buffer Size')
plt.savefig('speedup.png', dpi=200)
plt.show()