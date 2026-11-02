// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design internal header
// See Vtt_um_mda_sram_dryrun.h for the primary calling header

#ifndef VERILATED_VTT_UM_MDA_SRAM_DRYRUN___024ROOT_H_
#define VERILATED_VTT_UM_MDA_SRAM_DRYRUN___024ROOT_H_  // guard

#include "verilated.h"


class Vtt_um_mda_sram_dryrun__Syms;

class alignas(VL_CACHE_LINE_BYTES) Vtt_um_mda_sram_dryrun___024root final {
  public:

    // DESIGN SPECIFIC STATE
    VL_IN8(clk,0,0);
    VL_IN8(rst_n,0,0);
    VL_IN8(ui_in,7,0);
    VL_OUT8(uo_out,7,0);
    VL_IN8(uio_in,7,0);
    VL_OUT8(uio_out,7,0);
    VL_OUT8(uio_oe,7,0);
    VL_IN8(ena,0,0);
    CData/*1:0*/ tt_um_mda_sram_dryrun__DOT__rst_pipe;
    CData/*2:0*/ tt_um_mda_sram_dryrun__DOT__state;
    CData/*3:0*/ tt_um_mda_sram_dryrun__DOT__idx;
    CData/*0:0*/ tt_um_mda_sram_dryrun__DOT__fail;
    CData/*3:0*/ tt_um_mda_sram_dryrun__DOT__dout_q;
    CData/*0:0*/ tt_um_mda_sram_dryrun__DOT__mem_we;
    CData/*0:0*/ tt_um_mda_sram_dryrun__DOT__mem_en;
    CData/*1:0*/ __Vdly__tt_um_mda_sram_dryrun__DOT__rst_pipe;
    CData/*0:0*/ __VstlFirstIteration;
    CData/*0:0*/ __VstlPhaseResult;
    CData/*0:0*/ __Vtrigprevexpr___TOP__clk__0;
    CData/*0:0*/ __Vtrigprevexpr___TOP__rst_n__0;
    CData/*0:0*/ __VactPhaseResult;
    CData/*0:0*/ __VnbaPhaseResult;
    SData/*15:0*/ tt_um_mda_sram_dryrun__DOT__sram__DOT__dout_r;
    SData/*15:0*/ tt_um_mda_sram_dryrun__DOT__sram__DOT__merged;
    IData/*31:0*/ __VactIterCount;
    VlUnpacked<SData/*15:0*/, 1024> tt_um_mda_sram_dryrun__DOT__sram__DOT__mem;
    VlUnpacked<QData/*63:0*/, 1> __VstlTriggered;
    VlUnpacked<QData/*63:0*/, 1> __VactTriggered;
    VlUnpacked<QData/*63:0*/, 1> __VnbaTriggered;

    // INTERNAL VARIABLES
    Vtt_um_mda_sram_dryrun__Syms* vlSymsp;
    const char* vlNamep;

    // CONSTRUCTORS
    Vtt_um_mda_sram_dryrun___024root(Vtt_um_mda_sram_dryrun__Syms* symsp, const char* namep);
    ~Vtt_um_mda_sram_dryrun___024root();
    VL_UNCOPYABLE(Vtt_um_mda_sram_dryrun___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
