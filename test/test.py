# SPDX-License-Identifier: Apache-2.0
# MDA SRAM dry run: the design writes 16 words to the SRAM macro, rewrites the low bytes with a
# byte mask, reads everything back and reports on uo_out: bit0 = done, bit1 = pass, bit2 = fail.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


def bits(sig):
    # Binary string of the signal, MSB first, e.g. "00000011". Works for cocotb 1.x and 2.x.
    return str(sig.value)


@cocotb.test()
async def test_sram_dryrun(dut):
    dut._log.info("Start")
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())

    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    # The test takes about 70 cycles; allow plenty of margin.
    done = False
    for _ in range(500):
        await ClockCycles(dut.clk, 1)
        b = bits(dut.uo_out)
        if len(b) == 8 and "x" not in b.lower() and "z" not in b.lower() and b[-1] == "1":
            done = True
            break
    assert done, f"timeout: done never went high (uo_out={bits(dut.uo_out)})"

    b = bits(dut.uo_out)
    passed, failed = b[-2] == "1", b[-3] == "1"
    dut._log.info(f"done, pass={passed}, fail={failed}, uo_out={b}")
    assert passed and not failed, f"SRAM test failed (uo_out={b})"