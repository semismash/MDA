// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vtt_um_mda_sram_dryrun.h for the primary calling header

#include "Vtt_um_mda_sram_dryrun__pch.h"

VL_ATTR_COLD void Vtt_um_mda_sram_dryrun___024root___eval_static(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___eval_static\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__Vtrigprevexpr___TOP__clk__0 = vlSelfRef.clk;
    vlSelfRef.__Vtrigprevexpr___TOP__rst_n__0 = vlSelfRef.rst_n;
}

VL_ATTR_COLD void Vtt_um_mda_sram_dryrun___024root___eval_initial(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___eval_initial\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.uio_out = 0U;
    vlSelfRef.uio_oe = 0U;
    vlSelfRef.tt_um_mda_sram_dryrun__DOT__sram__DOT__dout_r = 0U;
}

VL_ATTR_COLD void Vtt_um_mda_sram_dryrun___024root___eval_initial__TOP(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___eval_initial__TOP\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.uio_out = 0U;
    vlSelfRef.uio_oe = 0U;
    vlSelfRef.tt_um_mda_sram_dryrun__DOT__sram__DOT__dout_r = 0U;
}

VL_ATTR_COLD void Vtt_um_mda_sram_dryrun___024root___eval_final(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___eval_final\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtt_um_mda_sram_dryrun___024root___dump_triggers__stl(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag);
#endif  // VL_DEBUG
VL_ATTR_COLD bool Vtt_um_mda_sram_dryrun___024root___eval_phase__stl(Vtt_um_mda_sram_dryrun___024root* vlSelf);

VL_ATTR_COLD void Vtt_um_mda_sram_dryrun___024root___eval_settle(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___eval_settle\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ __VstlIterCount;
    // Body
    __VstlIterCount = 0U;
    vlSelfRef.__VstlFirstIteration = 1U;
    do {
        if (VL_UNLIKELY(((0x00002710U < __VstlIterCount)))) {
#ifdef VL_DEBUG
            Vtt_um_mda_sram_dryrun___024root___dump_triggers__stl(vlSelfRef.__VstlTriggered, "stl"s);
#endif
            VL_FATAL_MT("src\\project.v", 11, "", "DIDNOTCONVERGE: Settle region did not converge after '--converge-limit' of 10000 tries");
        }
        __VstlIterCount = ((IData)(1U) + __VstlIterCount);
        vlSelfRef.__VstlPhaseResult = Vtt_um_mda_sram_dryrun___024root___eval_phase__stl(vlSelf);
        vlSelfRef.__VstlFirstIteration = 0U;
    } while (vlSelfRef.__VstlPhaseResult);
}

VL_ATTR_COLD void Vtt_um_mda_sram_dryrun___024root___eval_triggers_vec__stl(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___eval_triggers_vec__stl\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__VstlTriggered[0U] = ((0xfffffffffffffffeULL 
                                      & vlSelfRef.__VstlTriggered[0U]) 
                                     | (IData)((IData)(vlSelfRef.__VstlFirstIteration)));
}

VL_ATTR_COLD bool Vtt_um_mda_sram_dryrun___024root___trigger_anySet__stl(const VlUnpacked<QData/*63:0*/, 1> &in);

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtt_um_mda_sram_dryrun___024root___dump_triggers__stl(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___dump_triggers__stl\n"); );
    // Body
    if ((1U & (~ (IData)(Vtt_um_mda_sram_dryrun___024root___trigger_anySet__stl(triggers))))) {
        VL_DBG_MSGS("         No '" + tag + "' region triggers active\n");
    }
    if ((1U & (IData)(triggers[0U]))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 0 is active: Internal 'stl' trigger - first iteration\n");
    }
}
#endif  // VL_DEBUG

VL_ATTR_COLD bool Vtt_um_mda_sram_dryrun___024root___trigger_anySet__stl(const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___trigger_anySet__stl\n"); );
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

VL_ATTR_COLD void Vtt_um_mda_sram_dryrun___024root___stl_sequent__TOP__0(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___stl_sequent__TOP__0\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
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

VL_ATTR_COLD void Vtt_um_mda_sram_dryrun___024root___eval_stl(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___eval_stl\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((1ULL & vlSelfRef.__VstlTriggered[0U])) {
        vlSelfRef.uo_out = (((IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__dout_q) 
                             << 4U) | (((IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__fail) 
                                        << 2U) | ((
                                                   ((~ (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__fail)) 
                                                    & (4U 
                                                       == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state))) 
                                                   << 1U) 
                                                  | (4U 
                                                     == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state)))));
        vlSelfRef.tt_um_mda_sram_dryrun__DOT__sram__DOT__merged 
            = ((((0U == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state))
                  ? (0x00000a05U | (((IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx) 
                                     << 0x0000000cU) 
                                    | (0x000000f0U 
                                       & ((~ (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx)) 
                                          << 4U))))
                  : (0x0000ee30U | (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx))) 
                & (0x00ffU | (- (IData)((0U == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state)))))) 
               | (0xff00U & (vlSelfRef.tt_um_mda_sram_dryrun__DOT__sram__DOT__mem
                             [vlSelfRef.tt_um_mda_sram_dryrun__DOT__idx] 
                             & (- (IData)((0U != (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state)))))));
        vlSelfRef.tt_um_mda_sram_dryrun__DOT__mem_we 
            = ((0U == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state)) 
               | (1U == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state)));
        vlSelfRef.tt_um_mda_sram_dryrun__DOT__mem_en 
            = ((2U == (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__state)) 
               | (IData)(vlSelfRef.tt_um_mda_sram_dryrun__DOT__mem_we));
    }
}

VL_ATTR_COLD bool Vtt_um_mda_sram_dryrun___024root___eval_phase__stl(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___eval_phase__stl\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*0:0*/ __VstlExecute;
    // Body
    Vtt_um_mda_sram_dryrun___024root___eval_triggers_vec__stl(vlSelf);
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        Vtt_um_mda_sram_dryrun___024root___dump_triggers__stl(vlSelfRef.__VstlTriggered, "stl"s);
    }
#endif
    __VstlExecute = Vtt_um_mda_sram_dryrun___024root___trigger_anySet__stl(vlSelfRef.__VstlTriggered);
    if (__VstlExecute) {
        Vtt_um_mda_sram_dryrun___024root___eval_stl(vlSelf);
    }
    return (__VstlExecute);
}

bool Vtt_um_mda_sram_dryrun___024root___trigger_anySet__act(const VlUnpacked<QData/*63:0*/, 1> &in);

#ifdef VL_DEBUG
VL_ATTR_COLD void Vtt_um_mda_sram_dryrun___024root___dump_triggers__act(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___dump_triggers__act\n"); );
    // Body
    if ((1U & (~ (IData)(Vtt_um_mda_sram_dryrun___024root___trigger_anySet__act(triggers))))) {
        VL_DBG_MSGS("         No '" + tag + "' region triggers active\n");
    }
    if ((1U & (IData)(triggers[0U]))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 0 is active: @(posedge clk)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 1U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 1 is active: @(negedge rst_n)\n");
    }
}
#endif  // VL_DEBUG

VL_ATTR_COLD void Vtt_um_mda_sram_dryrun___024root___ctor_var_reset(Vtt_um_mda_sram_dryrun___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vtt_um_mda_sram_dryrun___024root___ctor_var_reset\n"); );
    Vtt_um_mda_sram_dryrun__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    const uint64_t __VscopeHash = VL_MURMUR64_HASH(vlSelf->vlNamep);
    vlSelf->ui_in = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 9967284984545053805ull);
    vlSelf->uo_out = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 4898547878985855477ull);
    vlSelf->uio_in = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 1424820951596298123ull);
    vlSelf->uio_out = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 16185529977779244833ull);
    vlSelf->uio_oe = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 3840965624738958755ull);
    vlSelf->ena = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4194194277674688301ull);
    vlSelf->clk = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16707436170211756652ull);
    vlSelf->rst_n = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1638864771569018232ull);
    vlSelf->tt_um_mda_sram_dryrun__DOT__rst_pipe = VL_SCOPED_RAND_RESET_I(2, __VscopeHash, 1788447513045720112ull);
    vlSelf->tt_um_mda_sram_dryrun__DOT__state = VL_SCOPED_RAND_RESET_I(3, __VscopeHash, 17290760009735992167ull);
    vlSelf->tt_um_mda_sram_dryrun__DOT__idx = VL_SCOPED_RAND_RESET_I(4, __VscopeHash, 10835405562416778257ull);
    vlSelf->tt_um_mda_sram_dryrun__DOT__fail = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 6892755515155642840ull);
    vlSelf->tt_um_mda_sram_dryrun__DOT__dout_q = VL_SCOPED_RAND_RESET_I(4, __VscopeHash, 2833143559046585269ull);
    vlSelf->tt_um_mda_sram_dryrun__DOT__mem_we = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15334127718949444778ull);
    vlSelf->tt_um_mda_sram_dryrun__DOT__mem_en = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 14659178373383831380ull);
    for (int __Vi0 = 0; __Vi0 < 1024; ++__Vi0) {
        vlSelf->tt_um_mda_sram_dryrun__DOT__sram__DOT__mem[__Vi0] = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 16462941821452365812ull);
    }
    vlSelf->tt_um_mda_sram_dryrun__DOT__sram__DOT__dout_r = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 2347463692543114115ull);
    vlSelf->tt_um_mda_sram_dryrun__DOT__sram__DOT__merged = VL_SCOPED_RAND_RESET_I(16, __VscopeHash, 5330058199997276694ull);
    vlSelf->__Vdly__tt_um_mda_sram_dryrun__DOT__rst_pipe = 0;
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VstlTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VactTriggered[__Vi0] = 0;
    }
    vlSelf->__Vtrigprevexpr___TOP__clk__0 = 0;
    vlSelf->__Vtrigprevexpr___TOP__rst_n__0 = 0;
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VnbaTriggered[__Vi0] = 0;
    }
}
