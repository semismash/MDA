import sys
sys.path.insert(0,'.')
from mda_sim import Sim
from mda_dev import SpiFlashSlave
from mda_util import with_equ
base=open('../../fw/spi_master.s').read()
def trial(div, tco=1, comp=0):
    sim=Sim(with_equ(base,DIV=div), ncycles=6000, comp=comp)
    dev=SpiFlashSlave(cs=14, sck=11, mosi=8, miso=2, tco=tco)
    sim.add_device(dev)
    sim.run()
    L=sim.prog.labels
    w=int.from_bytes(sim.dmem[L['result32']:L['result32']+4],'little')
    b=list(sim.dmem[L['result8']:L['result8']+4])
    ok = (w==0x00EF4018 and b==[0x00,0xEF,0x40,0x18] and dev.frames==[[0x9F,0,0,0]]*2)
    return ok,w,b,dev,sim
if __name__=='__main__':
    ok,w,b,dev,sim=trial(4)
    print("ok",ok,hex(w),[hex(x) for x in b],dev.frames,"faults",sim.faults)
    # timing of the SCLK: find rising edges of frame 2 to measure the byte gap
    e=sim.edges(11)
    rises=[t for t,v in e if v==1]
    fr2=[t for t in rises if t>rises[32]]
    gaps=[b_-a for a,b_ in zip(fr2,fr2[1:])]
    print("SCLK period in bytes mode:", sorted(set(gaps)), " largest (byte boundary gap, cycles):", max(gaps))
    print("32-bit frame SCLK period (cycles):", sorted(set(b_-a for a,b_ in zip(rises[:32],rises[1:32]))))
