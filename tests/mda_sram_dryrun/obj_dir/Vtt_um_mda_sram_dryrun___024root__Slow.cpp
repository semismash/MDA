// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtt_um_mda_sram_dryrun.h for the primary calling header

#include "Vtt_um_mda_sram_dryrun__pch.h"

void Vtt_um_mda_sram_dryrun___024root___ctor_var_reset(Vtt_um_mda_sram_dryrun___024root* vlSelf);

Vtt_um_mda_sram_dryrun___024root::Vtt_um_mda_sram_dryrun___024root(Vtt_um_mda_sram_dryrun__Syms* symsp, const char* namep)
 {
    vlSymsp = symsp;
    vlNamep = strdup(namep);
    // Reset structure values
    Vtt_um_mda_sram_dryrun___024root___ctor_var_reset(this);
}

void Vtt_um_mda_sram_dryrun___024root::__Vconfigure(bool first) {
    (void)first;  // Prevent unused variable warning
}

Vtt_um_mda_sram_dryrun___024root::~Vtt_um_mda_sram_dryrun___024root() {
    VL_DO_DANGLING(std::free(const_cast<char*>(vlNamep)), vlNamep);
}
