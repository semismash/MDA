import sys
sys.path.insert(0,'.')
from mda_sim import Sim
from mda_dev import uart_decode, bit_widths
src=open('../../fw/uart_tx.s').read()
sim=Sim(src, ncycles=70000)
sim.run()
fr=uart_decode(sim,10,434)
print("decoded:", bytes(b for _,b,_ in fr), "stop ok:", all(s for *_,s in fr))
starts=[s for s,_,_ in fr]
print("frame period (cycles):", [b-a for a,b in zip(starts,starts[1:])][:6], "ideal", 10*434)
print("faults:", sim.faults, "listing size (halfwords):", sim.prog.size)
w=bit_widths(sim,10,starts[0]-1,starts[-1]+4340)
print("run widths not multiple of 434 (cycles):", sorted(set(x%434 for x in w)))
print("thread1 exec/wait slots:", sim.th[1].n_exec, sim.th[1].n_wait)
