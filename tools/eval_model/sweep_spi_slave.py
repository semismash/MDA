import sys
sys.path.insert(0,'.')
from run_spi_slave import run_frame, run_reg
print("== preloaded-frame slave: SCLK = 50 MHz/(2*H)")
for H in (8,6,5,4,3,2,1):
    ok=run_frame(H)[0]
    print(f"H={H} SCLK={25/H:5.2f} MHz  {'ok' if ok else 'FAIL'}")
print("== register-read slave (decode between the command byte and the response)")
for H in (60,50,40,32,28,25,22,20,18,16,14,12,10,8):
    ok=run_reg(H)[0]
    print(f"H={H:3d} SCLK={25/H:5.2f} MHz  {'ok' if ok else 'FAIL'}")
print("== min CS-high time between frames (frame variant, H=8)")
for idle in (200,100,60,40,30,24,18,12,6):
    ok=run_frame(8, idle=idle)[0]
    print(f"idle={idle:3d} cycles ({idle*20} ns) {'ok' if ok else 'FAIL'}")
