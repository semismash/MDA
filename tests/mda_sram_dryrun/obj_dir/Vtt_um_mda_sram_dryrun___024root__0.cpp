// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtt_um_mda_sram_dryrun.h for the primary calling header

#include "Vtt_um_mda_sram_dryrun__pch.h"

void Vtt_um_mda_sram_dryrun___024root___eval_triggers_vec__act(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___eval_triggers_vec__act\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__VactTriggered[0U] = (QData)((IData)(
                                                    ((((~ (IData)(vlSelfRef.rst_n)) 
                                                       & (IData)(vlSelfRef.__Vtrigprevexpr___TOP__rst_n__0)) 
                                                      << 1U) 
                                                     | ((IData)(vlSelfRef.clk) 
                                                        & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__clk__0))))));
    vlSelfRef.__Vtrigprevexpr___TOP__clk__0 = vlSelfRef.clk;
    vlSelfRef.__Vtrigprevexpr___TOP__rst_n__0 = vlSelfRef.rst_n;
}

bool Vtt_um_mda_sram_dryrun___024root___trigger_anySet__act(const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___trigger_anySet__act\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        if (in[n]) {
            return (1U);
        }
        n = ((IData)(1U) + n);
    } while ((1U > n));
    return (0U);
}

void Vtt_um_mda_sram_dryrun___024root___nba_sequent__TOP__0(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___nba_sequent__TOP__0\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__Vdly__tt_um_mda_sram_dryrun__DOT__rst_pipe 
        = vlSelfRef.tt_um_mda_sram_dryrun__DOT__rst_pipe;
    vlSelfRef.__Vdly__tt_um_mda_sram_dryrun__DOT__rst_pipe 
        = ((IData)(vlSelfRef.rst_n) ? (1U | (2U & ((IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__rst_pipe) 
                                                   << 1U)))
            : 0U);
}

void Vtt_um_mda_sram_dryrun___024root___nba_sequent__TOP__1(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___nba_sequent__TOP__1\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*2:0*/ __Vdly__tt_um_mda_sram_dryrun__DOT__state;
    __Vdly__tt_um_mda_sram_dryrun__DOT__state = 0;
    CData/*3:0*/ __Vdly__tt_um_mda_sram_dryrun__DOT__idx;
    __Vdly__tt_um_mda_sram_dryrun__DOT__idx = 0;
    SData/*15:0*/ __VdlyVal__tt_um_mda_sram_dryrun__DOT__sram__DOT__mem__v0;
    __VdlyVal__tt_um_mda_sram_dryrun__DOT__sram__DOT__mem__v0 = 0;
    SData/*9:0*/ __VdlyDim0__tt_um_mda_sram_dryrun__DOT__sram__DOT__mem__v0;
    __VdlyDim0__tt_um_mda_sram_dryrun__DOT__sram__DOT__mem__v0 = 0;
    CData/*0:0*/ __VdlySet__tt_um_mda_sram_dryrun__DOT__sram__DOT__mem__v0;
    __VdlySet__tt_um_mda_sram_dryrun__DOT__sram__DOT__mem__v0 = 0;
    // Body
    __VdlySet__tt_um_mda_sram_dryrun__DOT__sram__DOT__mem__v0 = 0U;
    __Vdly__tt_um_mda_sram_dryrun__DOT__idx = vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx;
    __Vdly__tt_um_mda_sram_dryrun__DOT__state = vlSelfRef.tt_um_mda_sram_dryrun__DOT__state;
    if ((2U & (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__rst_pipe))) {
        if ((4U & (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state))) {
            __Vdly__tt_um_mda_sram_dryrun__DOT__state = 4U;
        } else if ((2U & (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state))) {
            if ((1U & (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state))) {
                vlSelfRef.tt_um_mda_sram_dryrun__DOT__fail 
                    = ((IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__fail) 
                       | (0U != ((IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__sram__DOT__dout_r) 
                                 ^ (0x00000a30U | (
                                                   ((IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx) 
                                                    << 0x0000000cU) 
                                                   | (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx))))));
                __Vdly__tt_um_mda_sram_dryrun__DOT__idx 
                    = (0x0000000fU & ((IData)(1U) + (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx)));
                vlSelfRef.tt_um_mda_sram_dryrun__DOT__dout_q 
                    = (0x0000000fU & (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__sram__DOT__dout_r));
                __Vdly__tt_um_mda_sram_dryrun__DOT__state 
                    = ((0x0fU == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx))
                        ? 4U : 2U);
            } else {
                __Vdly__tt_um_mda_sram_dryrun__DOT__state = 3U;
            }
        } else if ((1U & (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state))) {
            __Vdly__tt_um_mda_sram_dryrun__DOT__idx 
                = (0x0000000fU & ((IData)(1U) + (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx)));
            if ((0x0fU == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx))) {
                __Vdly__tt_um_mda_sram_dryrun__DOT__state = 2U;
            }
        } else {
            __Vdly__tt_um_mda_sram_dryrun__DOT__idx 
                = (0x0000000fU & ((IData)(1U) + (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx)));
            if ((0x0fU == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx))) {
                __Vdly__tt_um_mda_sram_dryrun__DOT__state = 1U;
            }
        }
    } else {
        __Vdly__tt_um_mda_sram_dryrun__DOT__state = 0U;
        __Vdly__tt_um_mda_sram_dryrun__DOT__idx = 0U;
        vlSelfRef.tt_um_mda_sram_dryrun__DOT__fail = 0U;
        vlSelfRef.tt_um_mda_sram_dryrun__DOT__dout_q = 0U;
    }
    if (vlSelfRef.tt_um_mda_sram_dryrun__DOT__mem_en) {
        if (vlSelfRef.tt_um_mda_sram_dryrun__DOT__mem_we) {
            __VdlyVal__tt_um_mda_sram_dryrun__DOT__sram__DOT__mem__v0 
                = vlSelfRef.tt_um_mda_sram_dryrun__DOT__sram__DOT__merged;
            __VdlyDim0__tt_um_mda_sram_dryrun__DOT__sram__DOT__mem__v0 
                = vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx;
            __VdlySet__tt_um_mda_sram_dryrun__DOT__sram__DOT__mem__v0 = 1U;
        }
        if ((2U == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state))) {
            vlSelfRef.tt_um_mda_sram_dryrun__DOT__sram__DOT__dout_r 
                = ((IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__mem_we)
                    ? (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__sram__DOT__merged)
                    : vlSelfRef.tt_um_mda_sram_dryrun__DOT__sram__DOT__mem
                   [vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx]);
        }
    }
    if (__VdlySet__tt_um_mda_sram_dryrun__DOT__sram__DOT__mem__v0) {
        vlSelfRef.tt_um_mda_sram_dryrun__DOT__sram__DOT__mem[__VdlyDim0__tt_um_mda_sram_dryrun__DOT__sram__DOT__mem__v0] 
            = __VdlyVal__tt_um_mda_sram_dryrun__DOT__sram__DOT__mem__v0;
    }
    vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx = __Vdly__tt_um_mda_sram_dryrun__DOT__idx;
    vlSelfRef.tt_um_mda_sram_dryrun__DOT__state = __Vdly__tt_um_mda_sram_dryrun__DOT__state;
    vlSelfRef.uo_out = (((IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__dout_q) 
                         << 4U) | (((IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__fail) 
                                    << 2U) | ((((~ (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__fail)) 
                                                & (4U 
                                                   == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state))) 
                                               << 1U) 
                                              | (4U 
                                                 == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state)))));
    vlSelfRef.tt_um_mda_sram_dryrun__DOT__sram__DOT__merged 
        = ((((0U == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state))
              ? (0x00000a05U | (((IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx) 
                                 << 0x0000000cU) | 
                                (0x000000f0U & ((~ (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx)) 
                                                << 4U))))
              : (0x0000ee30U | (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx))) 
            & (0x00ffU | (- (IData)((0U == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state)))))) 
           | (0xff00U & (vlSelfRef.tt_um_mda_sram_dryrun__DOT__sram__DOT__mem
                         [vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx] 
                         & (- (IData)((0U != (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state)))))));
    vlSelfRef.tt_um_mda_sram_dryrun__DOT__mem_we = 
        ((0U == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state)) 
         | (1U == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state)));
    vlSelfRef.tt_um_mda_sram_dryrun__DOT__mem_en = 
        ((2U == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state)) 
         | (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__mem_we));
}

void Vtt_um_mda_sram_dryrun___024root___nba_sequent__TOP__2(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___nba_sequent__TOP__2\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.tt_um_mda_sram_dryrun__DOT__rst_pipe 
        = vlSelfRef.__Vdly__tt_um_mda_sram_dryrun__DOT__rst_pipe;
}

void Vtt_um_mda_sram_dryrun___024root___eval_nba(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___eval_nba\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((3ULL & vlSelfRef.__VnbaTriggered[0U])) {
        vlSelfRef.__Vdly__tt_um_mda_sram_dryrun__DOT__rst_pipe 
            = vlSelfRef.tt_um_mda_sram_dryrun__DOT__rst_pipe;
        vlSelfRef.__Vdly__tt_um_mda_sram_dryrun__DOT__rst_pipe 
            = ((IData)(vlSelfRef.rst_n) ? (1U | (2U 
                                                 & ((IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__rst_pipe) 
                                                    << 1U)))
                : 0U);
    }
    if ((1ULL & vlSelfRef.__VnbaTriggered[0U])) {
        Vtt_um_mda_sram_dryrun___024root___nba_sequent__TOP__1(vlSelf);
    }
    if ((3ULL & vlSelfRef.__VnbaTriggered[0U])) {
        vlSelfRef.tt_um_mda_sram_dryrun__DOT__rst_pipe 
            = vlSelfRef.__Vdly__tt_um_mda_sram_dryrun__DOT__rst_pipe;
    }
}

void Vtt_um_mda_sram_dryrun___024root___trigger_orInto__act_vec_vec(VlUnpacked<QData/*63:0*/, 1> &out, const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___trigger_orInto__act_vec_vec\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        out[n] = (out[n] | in[n]);
        n = ((IData)(1U) + n);
    } while ((0U >= n));
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtt_um_mda_sram_dryrun___024root___dump_triggers__act(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag);
#endif  // VL_DEBUG

bool Vtt_um_mda_sram_dryrun___024root___eval_phase__act(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___eval_phase__act\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    Vtt_um_mda_sram_dryrun___024root___eval_triggers_vec__act(vlSelf);
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        Vtt_um_mda_sram_dryrun___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
    }
#endif
    Vtt_um_mda_sram_dryrun___024root___trigger_orInto__act_vec_vec(vlSelfRef.__VnbaTriggered, vlSelfRef.__VactTriggered);
    return (0U);
}

void Vtt_um_mda_sram_dryrun___024root___trigger_clear__act(VlUnpacked<QData/*63:0*/, 1> &out) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___trigger_clear__act\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        out[n] = 0ULL;
        n = ((IData)(1U) + n);
    } while ((1U > n));
}

bool Vtt_um_mda_sram_dryrun___024root___eval_phase__nba(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___eval_phase__nba\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*0:0*/ __VnbaExecute;
    // Body
    __VnbaExecute = Vtt_um_mda_sram_dryrun___024root___trigger_anySet__act(vlSelfRef.__VnbaTriggered);
    if (__VnbaExecute) {
        Vtt_um_mda_sram_dryrun___024root___eval_nba(vlSelf);
        Vtt_um_mda_sram_dryrun___024root___trigger_clear__act(vlSelfRef.__VnbaTriggered);
    }
    return (__VnbaExecute);
}

void Vtt_um_mda_sram_dryrun___024root___eval(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___eval\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ __VnbaIterCount;
    // Body
    __VnbaIterCount = 0U;
    do {
        if (VL_UNLIKELY(((0x00002710U < __VnbaIterCount)))) {
#ifdef VL_DEBUG
            Vtt_um_mda_sram_dryrun___024root___dump_triggers__act(vlSelfRef.__VnbaTriggered, "nba"s);
#endif
            VL_FATAL_MT("src\\project.v", 11, "", "DIDNOTCONVERGE: NBA region did not converge after '--converge-limit' of 10000 tries");
        }
        __VnbaIterCount = ((IData)(1U) + __VnbaIterCount);
        vlSelfRef.__VactIterCount = 0U;
        do {
            if (VL_UNLIKELY(((0x00002710U < vlSelfRef.__VactIterCount)))) {
#ifdef VL_DEBUG
                Vtt_um_mda_sram_dryrun___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
#endif
                VL_FATAL_MT("src\\project.v", 11, "", "DIDNOTCONVERGE: Active region did not converge after '--converge-limit' of 10000 tries");
            }
            vlSelfRef.__VactIterCount = ((IData)(1U) 
                                         + vlSelfRef.__VactIterCount);
            vlSelfRef.__VactPhaseResult = Vtt_um_mda_sram_dryrun___024root___eval_phase__act(vlSelf);
        } while (vlSelfRef.__VactPhaseResult);
        vlSelfRef.__VnbaPhaseResult = Vtt_um_mda_sram_dryrun___024root___eval_phase__nba(vlSelf);
    } while (vlSelfRef.__VnbaPhaseResult);
}

#ifdef VL_DEBUG
void Vtt_um_mda_sram_dryrun___024root___eval_debug_assertions(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___eval_debug_assertions\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if (VL_UNLIKELY(((vlSelfRef.ena & 0xfeU)))) {
        Verilated::overWidthError("ena");
    }
    if (VL_UNLIKELY(((vlSelfRef.clk & 0xfeU)))) {
        Verilated::overWidthError("clk");
    }
    if (VL_UNLIKELY(((vlSelfRef.rst_n & 0xfeU)))) {
        Verilated::overWidthError("rst_n");
    }
}
#endif  // VL_DEBUG
