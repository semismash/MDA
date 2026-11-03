import sys
sys.path.insert(0,'.')
from run_spi_master import trial
print("max SCLK = 50 MHz / (2*DIV). Entries: ok/FAIL for slave clock-to-MISO delay tco (cycles, 20 ns each)")
for comp in (0,2):
    print(f"--- engine sample compensation = {comp} cycles")
    print("DIV  SCLK(MHz) | tco=1  tco=2  tco=3  tco=4")
    for div in (8,6,5,4,3,2,1):
        row=[]
        for tco in (1,2,3,4):
            ok=trial(div,tco=tco,comp=comp)[0]
            row.append('ok  ' if ok else 'FAIL')
        print(f"{div:3d}  {25/div:7.2f}   | "+"   ".join(row))
