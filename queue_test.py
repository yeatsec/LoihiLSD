from noc_utils import Queue, SpikeMsg

q = Queue(capacity=5, pQ=True)
q.enqueue(SpikeMsg((0, 0), [3], delay=4))
q.enqueue(SpikeMsg((0, 0), [3], delay=3))
q.enqueue(SpikeMsg((0, 0), [3], delay=2))
#q.enqueue(SpikeMsg((0, 0), [3], delay=1))

print(q)
print('IsReady: {}'.format(q.ready()))
q.dec_delays()
print(q)