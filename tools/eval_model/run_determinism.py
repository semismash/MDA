import sys, hashlib
sys.path.insert(0,'.')
from mda_sim import Sim
from mda_dev import SpiFlashSlave, uart_decode
N=80000
def run(fn, seed=None):
    sim=Sim(open(fn).read(), ncycles=N, init_random=seed)
    sim.add_device(SpiFlashSlave(cs=14, sck=11, mosi=8, miso=2, tco=1))
    sim.run()
    return sim
def sig(sim, pins):
    return {p: hashlib.sha256(bytes(sim.hist[p][:N])).hexdigest()[:12] for p in pins}
victim_pins=(10,8,11,14)
base=run('../../fw/determinism_parked.s')
print("baseline decoded UART:", bytes(b for _,b,_ in uart_decode(base,10,434)))
ref=sig(base,victim_pins)
print("baseline signatures :",ref)
res=[]
for name,fn,seed in (("noisy neighbour","../../fw/determinism_noisy.s",None),
                     ("noisy + random init (seed 1)","../../fw/determinism_noisy.s",1),
                     ("noisy + random init (seed 2)","../../fw/determinism_noisy.s",2),
                     ("parked + random init (seed 3)","../../fw/determinism_parked.s",3)):
    s=run(fn,seed)
    same = sig(s,victim_pins)==ref
    nf=len(s.faults)
    print(f"{name:30s}: pin waveforms identical to the cycle = {same} | neighbour raised {nf} faults, thread1 flags OVR/ERR={bool(s.th[1].flags&((1<<12)|(1<<3)))}, thread2 {bool(s.th[2].flags&((1<<12)|(1<<3)))}")
# how many cycles did the check cover and how many pin edges
print("edges compared:", {p: len(base.edges(p,0,N)) for p in victim_pins})
