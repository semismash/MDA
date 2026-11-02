// Verilator driver for the MDA SRAM dry run (replaces test/tb.v, needs no --timing).
// Put this file in test/ and build from the project root, see the command below.
//
//   verilator --cc --exe --build -Wno-fatal --top-module tt_um_mda_sram_dryrun \
//     src/project.v test/RM_IHPSG13_1P_1024x16_c2_bm_bist_model.v test/tb_main.cpp -o sim
//   ./obj_dir/sim
//
// Exit code 0 = PASS, 1 = FAIL.

#include "Vtt_um_mda_sram_dryrun.h"
#include "verilated.h"

#include <cstdio>

// The Verilator runtime calls this when the model is built without --timing or SystemC.
double sc_time_stamp() { return 0; }

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vtt_um_mda_sram_dryrun* dut = new Vtt_um_mda_sram_dryrun;

    dut->ui_in  = 0;
    dut->uio_in = 0;
    dut->ena    = 1;
    dut->clk    = 0;
    dut->rst_n  = 0;
    dut->eval();

    // One full clock period: rising edge, then falling edge.
    auto tick = [&]() {
        dut->clk = 1;
        dut->eval();
        dut->clk = 0;
        dut->eval();
    };

    for (int i = 0; i < 5; i++) tick();  // reset held for 5 cycles
    dut->rst_n = 1;

    int cycles = 0;
    while (!(dut->uo_out & 0x01) && cycles < 1000) {  // uo[0] = done
        tick();
        cycles++;
    }

    const bool done = dut->uo_out & 0x01;
    const bool pass = dut->uo_out & 0x02;  // uo[1]
    const bool fail = dut->uo_out & 0x04;  // uo[2]

    int rc = 1;
    if (!done)
        std::printf("FAIL: timeout, done was never set\n");
    else if (pass && !fail) {
        std::printf("PASS: finished after %d cycles\n", cycles);
        rc = 0;
    } else
        std::printf("FAIL: done, but pass=%d fail=%d\n", (int)pass, (int)fail);

    dut->final();
    delete dut;
    return rc;
}