# SPDX-License-Identifier: Apache-2.0
# MDA smoke test.
#
# RTL run: the instruction and data memories are loaded through the testbench (backdoor) while reset is held. After reset
# the wrapper releases all three threads at address 0, so the same program runs on every thread. It sums 10..1, builds a
# 24-bit constant with lli, stores and reloads words and bytes, and makes a call and a return. All three threads write the
# same values, so the data memory after the run is fixed; it was computed with the independent eval simulator and with
# the elaborated RTL (tools verif/mda_e2e.py). The whole data memory is compared.
#
# Gate-level run (GATES=yes): the hierarchy is flattened, so the memories cannot be reached by name. Only the invariants
# that do not depend on memory content are checked: reset completes and the bidirectional pins stay inputs and low.

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

GATES = os.environ.get("GATES", "no") == "yes"

# instruction memory, word address: halfword
PROGRAM = {0: 0x200E, 1: 0x414E, 2: 0x2540, 3: 0x4BE2, 4: 0x0F79, 5: 0x800E, 6: 0x108C, 7: 0xB57E, 8: 0xCDEF, 9: 0x12AC, 10: 0xD02B, 11: 0xF952, 12: 0x6568, 13: 0x6FEA, 14: 0x11CC, 15: 0xC147, 16: 0x13EC, 17: 0x5083, 18: 0x2540, 19: 0xA0AE, 20: 0x1495, 21: 0xC02E, 22: 0x0051, 23: 0xC04E, 24: 0x330C, 25: 0xFFD1, 26: 0xFCE2, 27: 0xB813}

# data memory after the program, word index: value (all other words are 0)
EXPECTED = {0: 0x00000037, 1: 0x00ABCDEF, 2: 0xFFFFFFFE, 3: 0x0ABCDEF3, 4: 0x00000001}

RUN_CYCLES = 1500


@cocotb.test()
async def test_mda_smoke(dut):
    dut._log.info("Start")
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())

    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0

    if not GATES:
        imem = dut.user_project.u_top.u_imem.u_sram.mem
        dmem = dut.user_project.u_top.u_dmem.u_sram.mem
        for i in range(1024):
            imem[i].value = PROGRAM.get(i, 0)
        for i in range(256):
            dmem[i].value = 0

    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, RUN_CYCLES)

    assert int(dut.uio_oe.value) == 0, f"uio_oe = {dut.uio_oe.value}"
    assert int(dut.uio_out.value) == 0, f"uio_out = {dut.uio_out.value}"

    if GATES:
        dut._log.info("gate level: reset and pin invariants checked")
        return

    bad = []
    for i in range(256):
        got = int(dmem[i].value)
        want = EXPECTED.get(i, 0)
        if got != want:
            bad.append(f"word {i}: got 0x{got:08X}, expected 0x{want:08X}")
    assert not bad, "data memory differs: " + "; ".join(bad[:8])
    dut._log.info("data memory image matches the reference")