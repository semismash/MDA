import sys
sys.path.insert(0,'.')
from mda_sim import Sim
from mda_dev import UartSender, SpiFlashSlave, uart_decode
class SpiRegDevice(SpiFlashSlave):
    """SPI device: reply byte = (command + 0x10) & 0xFF"""
    def out_byte(self):
        if self.byten == 1 and self.cur:
            return (self.cur[0] + 0x10) & 0xFF
        return 0
def run(msg=b"ABCD", gap=0.0, ncycles=None):
    src=open('../../fw/bridge.s').read()
    N=ncycles or int(4000+ (10+gap)*434*len(msg)+12000)
    sim=Sim(src, ncycles=N)
    tx=UartSender(0, list(msg), 434, start=2000, gap_bits=gap)
    sim.add_device(tx)
    sim.add_device(SpiRegDevice(cs=14, sck=11, mosi=8, miso=2, tco=1))
    sim.run()
    return sim, tx
if __name__=='__main__':
    for gap in (0.0, 20.0):
        sim,tx=run(gap=gap)
        out=uart_decode(sim,10,434)
        exp=bytes((b+0x10)&255 for b in b"ABCD")
        print(f"gap {gap:4.1f} bits: sent {b'ABCD'} -> got {bytes(b for _,b,_ in out)} expected {exp} | stop bits ok {all(s for *_,s in out)}")
        # latency: end of RX frame k (start + 10 bits) to TX start bit
        lat=[o[0]-(f[0]+10*434) for f,o in zip(tx.frames,out)]
        print("   latency RX-stop-bit-end -> TX start bit (cycles):",lat, "=", [round(l*0.02,1) for l in lat],"us")
        print("   faults:",sim.faults, " OVR flags t0/t1/t2:",[bool(sim.th[i].flags&(1<<12)) for i in range(3)], "framing errors:",sim.th[0].regs[0])
