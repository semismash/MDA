import sys
sys.path.insert(0,'.')
from mda_sim import Sim
from mda_dev import SpiMaster
def run_frame(half, comp=0, idle=200, gap=0):
    src=open('../../fw/spi_slave_frame.s').read()
    frames=[[0x9F,0,0,0]]*3
    sim=Sim(src, ncycles=12000, comp=comp)
    m=SpiMaster(cs=4, sck=1, mosi=7, miso=10, frames=frames, half=half, start=1500, idle=idle, gap=gap)
    sim.add_device(m)
    sim.run(ncycles=m.end+300)
    res=m.results(sim)
    rx=int.from_bytes(sim.dmem[sim.prog.labels['rxframe']:sim.prog.labels['rxframe']+4],'little')
    ok = all(r==[0x00,0xEF,0x40,0x18] for r in res) and rx==0x9F000000
    return ok,res,rx,sim
def run_reg(half, cmds=range(0,32,3), idle=200, gap=0, comp=0, with_abort=True):
    src=open('../../fw/spi_slave_reg.s').read()
    frames=[]
    for c in cmds:
        frames.append([c,0x00])
    if with_abort:
        frames.insert(2,[0x05])       # aborted frame: CS rises after one byte
    sim=Sim(src, ncycles=40000, comp=comp)
    m=SpiMaster(cs=4, sck=1, mosi=7, miso=10, frames=frames, half=half, start=1500, idle=idle, gap=gap)
    sim.add_device(m)
    sim.run(ncycles=m.end+300)
    res=m.results(sim)
    exp=[]
    for f in frames:
        exp.append([0x00,0xA0+f[0]] if len(f)==2 else [0x00])
    # frame without response: master only sees the command phase (8 zero bits)
    ok = res==exp
    return ok,res,exp,sim
if __name__=='__main__':
    ok,res,rx,sim=run_frame(8)
    print("frame variant H=8 ok:",ok,res,hex(rx),"faults",sim.faults)
    ok,res,exp,sim=run_reg(40)
    print("reg variant H=40 ok:",ok,"faults",sim.faults,"\n got",res[:4],"\n exp",exp[:4])
