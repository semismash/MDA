import sys
sys.path.insert(0,'.')
from mda_sim import Sim
from mda_dev import UartSender
from mda_util import with_equ
base=open('../../fw/uart_rx.s').read()
PAT=[0x55,0xAA,0x00,0xFF,0x12,0x34,0xF0,0x0F,0x81,0x7E,0xC3,0x3C,0xA5,0x5A,0x99,0x66]
def trial(div, err=0.0, gap=0.0, dl=None, verbose=False):
    dl = dl if dl is not None else max(3, int((div/2-10)//3*3))
    src=with_equ(base, DIV=div, WAITDL=dl)
    sim=Sim(src, ncycles=int(3000+ (10+gap)*div*len(PAT)+2000))
    tx=UartSender(0, PAT, div*(1+err), start=2000, gap_bits=gap)
    sim.add_device(tx)
    sim.run()
    base_addr=sim.prog.labels['rxbuf']
    got=list(sim.dmem[base_addr:base_addr+len(PAT)])
    ferr=sim.th[0].regs[0]
    return got==PAT, got, ferr, sim
if __name__=='__main__':
    ok,got,ferr,sim=trial(434)
    print("115200 ok:",ok,"ferr:",ferr,"faults:",sim.faults, "OVR:",bool(sim.th[0].flags & (1<<12)))
    print(got)
