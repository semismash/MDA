import sys
sys.path.insert(0,'.')
from run_i2c_slave import run, SCRIPT
from mda_dev import i2c_analyze
def trial(**tm):
    sim,m=run(SCRIPT, **tm)
    ok = m.acks==[0,0,0,0,0,1,1,0,0,0] and m.reads==[0xDE,0xAD,0xBE,0x07] and list(sim.dmem[4:7])==[0xDE,0xAD,0xBE]
    return ok, m.late, sim, m
grades=[("100 kHz std", dict(tlow=235,thigh=200,tsusta=200,thdsta=200,tsusto=200,tbuf=235,tsudat=25,thddat=5)),
        ("400 kHz nominal", dict(tlow=70,thigh=55,tsusta=35,thdsta=35,tsusto=35,tbuf=70,tsudat=8,thddat=8)),
        ("400 kHz spec-min", dict(tlow=65,thigh=30,tsusta=30,thdsta=30,tsusto=30,tbuf=65,tsudat=5,thddat=3)),
        ("~480 kHz", dict(tlow=60,thigh=40,tsusta=30,thdsta=30,tsusto=30,tbuf=60,tsudat=5,thddat=3)),
        ("~620 kHz", dict(tlow=50,thigh=32,tsusta=30,thdsta=30,tsusto=30,tbuf=50,tsudat=5,thddat=3)),
        ("~800 kHz", dict(tlow=36,thigh=26,tsusta=30,thdsta=30,tsusto=30,tbuf=40,tsudat=5,thddat=3)),
        ("1 MHz (FM+)", dict(tlow=26,thigh=24,tsusta=13,thdsta=13,tsusto=13,tbuf=26,tsudat=3,thddat=2))]
for name,tm in grades:
    ok,late,sim,m=trial(**tm)
    per=(tm['tlow']+tm['thigh'])*20
    print(f"{name:18s} period {per:5d} ns: data/ack ok={ok}, late-SDA bits={late}")
