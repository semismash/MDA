// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Model implementation (design independent parts)

#include "Vtt_um_mda_sram_dryrun__pch.h"

//============================================================
// Constructors

Vtt_um_mda_sram_dryrun::Vtt_um_mda_sram_dryrun(VerilatedContext* _vcontextp__, const char* _vcname__)
    : VerilatedModel{*_vcontextp__}
    , vlSymsp{new Vtt_um_mda_sram_dryrun__Syms(contextp(), _vcname__, this)}
    , clk{vlSymsp->TOP.clk}
    , rst_n{vlSymsp->TOP.rst_n}
    , ui_in{vlSymsp->TOP.ui_in}
    , uo_out{vlSymsp->TOP.uo_out}
    , uio_in{vlSymsp->TOP.uio_in}
    , uio_out{vlSymsp->TOP.uio_out}
    , uio_oe{vlSymsp->TOP.uio_oe}
    , ena{vlSymsp->TOP.ena}
    , rootp{&(vlSymsp->TOP)}
{
    // Register model with the context
    contextp()->addModel(this);
}

Vtt_um_mda_sram_dryrun::Vtt_um_mda_sram_dryrun(const char* _vcname__)
    : Vtt_um_mda_sram_dryrun(Verilated::threadContextp(), _vcname__)
{
}

//============================================================
// Destructor

Vtt_um_mda_sram_dryrun::~Vtt_um_mda_sram_dryrun() {
    delete vlSymsp;
}

//============================================================
// Evaluation function

#ifdef VL_DEBUG
void Vtt_um_mda_sram_dryrun___024root___eval_debug_assertions(Vtt_um_mda_sram_dryrun___024root* vlSelf);
#endif  // VL_DEBUG
void Vtt_um_mda_sram_dryrun___024root___eval_static(Vtt_um_mda_sram_dryrun___024root* vlSelf);
void Vtt_um_mda_sram_dryrun___024root___eval_initial(Vtt_um_mda_sram_dryrun___024root* vlSelf);
void Vtt_um_mda_sram_dryrun___024root___eval_settle(Vtt_um_mda_sram_dryrun___024root* vlSelf);
void Vtt_um_mda_sram_dryrun___024root___eval(Vtt_um_mda_sram_dryrun___024root* vlSelf);

void Vtt_um_mda_sram_dryrun::eval_step() {
    VL_DEBUG_IF(VL_DBG_MSGF("+++++TOP Evaluate Vtt_um_mda_sram_dryrun::eval_step\n"); );
#ifdef VL_DEBUG
    // Debug assertions
    Vtt_um_mda_sram_dryrun___024root___eval_debug_assertions(&(vlSymsp->TOP));
#endif  // VL_DEBUG
    vlSymsp->__Vm_deleter.deleteAll();
    if (VL_UNLIKELY(!vlSymsp->__Vm_didInit)) {
        VL_DEBUG_IF(VL_DBG_MSGF("+ Initial\n"););
        Vtt_um_mda_sram_dryrun___024root___eval_static(&(vlSymsp->TOP));
        Vtt_um_mda_sram_dryrun___024root___eval_initial(&(vlSymsp->TOP));
        Vtt_um_mda_sram_dryrun___024root___eval_settle(&(vlSymsp->TOP));
        vlSymsp->__Vm_didInit = true;
    }
    VL_DEBUG_IF(VL_DBG_MSGF("+ Eval\n"););
    Vtt_um_mda_sram_dryrun___024root___eval(&(vlSymsp->TOP));
    // Evaluate cleanup
    Verilated::endOfEval(vlSymsp->__Vm_evalMsgQp);
}

//============================================================
// Events and timing
bool Vtt_um_mda_sram_dryrun::eventsPending() { return false; }

uint64_t Vtt_um_mda_sram_dryrun::nextTimeSlot() {
    VL_FATAL_MT(__FILE__, __LINE__, "", "No delays in the design");
    return 0;
}

//============================================================
// Utilities

const char* Vtt_um_mda_sram_dryrun::name() const {
    return vlSymsp->name();
}

//============================================================
// Invoke final blocks

void Vtt_um_mda_sram_dryrun___024root___eval_final(Vtt_um_mda_sram_dryrun___024root* vlSelf);

VL_ATTR_COLD void Vtt_um_mda_sram_dryrun::final() {
    contextp()->executingFinal(true);
    Vtt_um_mda_sram_dryrun___024root___eval_final(&(vlSymsp->TOP));
    contextp()->executingFinal(false);
}

//============================================================
// Implementations of abstract methods from VerilatedModel

const char* Vtt_um_mda_sram_dryrun::hierName() const { return vlSymsp->name(); }
const char* Vtt_um_mda_sram_dryrun::modelName() const { return "Vtt_um_mda_sram_dryrun"; }
unsigned Vtt_um_mda_sram_dryrun::threads() const { return 1; }
void Vtt_um_mda_sram_dryrun::prepareClone() const { contextp()->prepareClone(); }
void Vtt_um_mda_sram_dryrun::atClone() const {
    contextp()->threadPoolpOnClone();
}
