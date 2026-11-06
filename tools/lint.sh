#!/usr/bin/env bash
# Lint the RTL with Verilator in both configurations: simulation RAM, and the SRAM macros (with the macro stubs).
# Run from anywhere: bash tools/lint.sh      Full output goes to lint.txt, a summary by warning type is printed.
cd "$(dirname "$0")/.." || exit 1

# waived everywhere: unused parameters and signals (Stage B placeholders), wildcard imports (the codebase style), tt_um_mda living in
# mda_tt_top.sv, and parameters named like package constants (DATA_WIDTH is overridden on purpose)
WAIVE="-Wno-UNUSEDPARAM -Wno-UNUSEDSIGNAL -Wno-IMPORTSTAR -Wno-DECLFILENAME -Wno-VARHIDDEN"
RTL=$(grep -v -e '^#' -e '^$' -e 'asic-only' rtl.f | awk '{print $1}' | tr -d '\r')
ALL=$(grep -v -e '^#' -e '^$' rtl.f | awk '{print $1}' | tr -d '\r')
rc=0
: > lint.txt

lint() {    # name, extra flags, files
    echo "== $1" | tee -a lint.txt
    verilator --lint-only -Wall $WAIVE $2 --top-module tt_um_mda $3 > lint_part.txt 2>&1 || rc=1
    cat lint_part.txt >> lint.txt
    grep -o -e '%Warning-[A-Z0-9]*' -e '%Error[-A-Z0-9]*' lint_part.txt | sort | uniq -c | sort -rn
    rm -f lint_part.txt
}

lint "RTL configuration (simulation RAM)" "" "$RTL"
# the macro stubs are black boxes (their outputs look undriven) and one of them carries a timescale, which makes every other module "miss" one
lint "macro configuration (-DMDA_SRAM_MACRO, with the macro stubs)" "-DMDA_SRAM_MACRO -Wno-UNDRIVEN -Wno-TIMESCALEMOD" "$ALL"

# the generated Verilog is what CI synthesizes: it must be fresh, and it is linted on its own with the macro stubs
echo "== generated Verilog (src/mda_synth.v, what CI synthesizes)" | tee -a lint.txt
if python3 tools/gen_synth.py --check | tee -a lint.txt | grep -q "up to date"; then
    lint_gen=1
else
    rc=1; lint_gen=0
fi
if [ $lint_gen -eq 1 ]; then
    # sv2v writes the zero fill '0 as the 1-bit signed constant 1'sb0, which Verilog sign-extends to zeros: correct, but WIDTHEXPAND reports it.
    # Real width problems are caught by the SystemVerilog lint above, so it is waived here.
    lint "generated Verilog lint" "-DMDA_SRAM_MACRO -Wno-UNDRIVEN -Wno-TIMESCALEMOD -Wno-WIDTHEXPAND" "src/mda_synth.v src/RM_IHPSG13_1P_1024x16_c2_bm_bist.v src/RM_IHPSG13_1P_256x32_c2_bm_bist.v"
fi

if [ $rc -eq 0 ]; then echo "lint clean"; else echo "see lint.txt"; fi
exit $rc