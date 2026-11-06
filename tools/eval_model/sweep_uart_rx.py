import sys
sys.path.insert(0,'.')
from run_uart_rx import trial
print("== baud sweep, back-to-back frames, zero baud error")
for name,div in (("115200",434),("230400",217),("460800",109),("460800(108)",108),("921600",54),("1 Mbaud",50),("1.25M",40),("1.67M",30)):
    ok,got,ferr,sim=trial(div)
    print(f"{name:12s} DIV={div:3d} ok={ok} ferr={ferr}")
print("== baud mismatch tolerance at 115200 (sender faster/slower by x%)")
res=[]
for e in (-0.06,-0.05,-0.04,-0.03,-0.02,-0.01,0.0,0.01,0.02,0.03,0.04,0.05,0.06):
    ok,*_ = trial(434, err=e)
    res.append((e,ok))
print(" ".join(f"{e*100:+.0f}%:{'ok' if ok else 'FAIL'}" for e,ok in res))
print("== 921600 with 1 stop-bit of idle between frames")
for g in (0,0.5,1,2):
    ok,got,ferr,sim=trial(54,gap=g)
    print(f"gap {g} bits: ok={ok} ferr={ferr}")
