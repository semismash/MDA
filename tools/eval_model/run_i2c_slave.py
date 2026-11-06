import sys
sys.path.insert(0,'.')
from mda_sim import Sim
from mda_dev import I2cMaster, i2c_analyze
def run(script, **timing):
    src=open('../../fw/i2c_slave.s').read()
    sim=Sim(src, ncycles=120000)
    m=I2cMaster(19,22,script,**timing)
    sim.add_device(m)
    sim.run(until=lambda s,t: m.done and t>m.now)
    return sim,m
SCRIPT=[('start',),('wr',0x54),('wr',0x04),('wr',0xDE),('wr',0xAD),('wr',0xBE),('stop',),
        ('start',),('wr',0xA0),('wr',0x11),('stop',),                     # other device: must be ignored
        ('start',),('wr',0x54),('wr',0x04),('rstart',),('wr',0x55),('rd',0),('rd',0),('rd',0),('rd',1),('stop',)]
if __name__=='__main__':
    sim,m=run(SCRIPT)
    print("acks (0=ACK):",m.acks,"  reads:",[hex(x) for x in m.reads])
    print("regs[4..6]:",[hex(x) for x in sim.dmem[4:7]],"faults:",sim.faults)
