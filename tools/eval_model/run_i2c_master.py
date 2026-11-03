import sys
sys.path.insert(0,'.')
from mda_sim import Sim
from mda_dev import I2cEeprom, i2c_analyze
from mda_util import with_equ
base=open('../../fw/i2c_master.s').read()
def run(stretch=0, **eq):
    sim=Sim(with_equ(base,**eq) if eq else base, ncycles=60000)
    dev=I2cEeprom(18,21,addr=0x50,stretch=stretch)
    sim.add_device(dev)
    sim.run()
    L=sim.prog.labels['results']
    res=list(sim.dmem[L:L+9])
    return sim,dev,res
if __name__=='__main__':
    sim,dev,res=run()
    print("results bytes:",[hex(x) for x in res], " device mem[0x10..0x11]:",[hex(x) for x in dev.mem[0x10:0x12]])
    print("faults:",sim.faults, " log:",[l[1:] for l in dev.log if l[1] in('START','STOP')][:6])
    t=i2c_analyze(sim,18,21)
    for k,(mn,mx,n) in t.items(): print(f"{k:8s} min {mn:7.0f} ns  max {mx:7.0f} ns  (n={n})")
