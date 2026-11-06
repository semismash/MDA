# MDA RTL source list. Single source of truth for info.yaml (source_files) and test/Makefile (PROJECT_SOURCES).
# Order matters: packages first. A trailing "# asic-only" keeps a file out of the RTL simulation Makefile.
# Regenerate the two lists with: python3 tools/sync_sources.py
src/mda_pkg.sv
src/mda_isa_pkg.sv
src/mda_sync.sv
src/mda_sram_sim.sv
src/mda_imem.sv
src/mda_dmem.sv
src/mda_alu.sv
src/mda_regfile.sv
src/mda_regbank.sv
src/mda_pc.sv
src/mda_fetch.sv
src/mda_flags.sv
src/mda_cond.sv
src/mda_branch_unit.sv
src/mda_decoder.sv
src/mda_suffix.sv
src/mda_imm_gen.sv
src/mda_fault.sv
src/mda_lsu.sv
src/mda_wb.sv
src/mda_sched.sv
src/mda_id_ex.sv
src/mda_ex.sv
src/mda_core.sv
src/mda_top.sv
src/mda_tt_top.sv
src/RM_IHPSG13_1P_1024x16_c2_bm_bist.v   # asic-only
src/RM_IHPSG13_1P_256x32_c2_bm_bist.v    # asic-only
