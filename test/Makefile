# Makefile
# See https://docs.cocotb.org/en/stable/quickstart.html for more info

# defaults
SIM ?= icarus
FST ?= -fst # Use more efficient FST format
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../src
PROJECT_SOURCES = mda_pkg.sv \
    mda_isa_pkg.sv \
    mda_sync.sv \
    mda_sram_sim.sv \
    mda_imem.sv \
    mda_dmem.sv \
    mda_alu.sv \
    mda_regfile.sv \
    mda_regbank.sv \
    mda_pc.sv \
    mda_fetch.sv \
    mda_flags.sv \
    mda_cond.sv \
    mda_branch_unit.sv \
    mda_decoder.sv \
    mda_suffix.sv \
    mda_imm_gen.sv \
    mda_fault.sv \
    mda_lsu.sv \
    mda_wb.sv \
    mda_sched.sv \
    mda_id_ex.sv \
    mda_ex.sv \
    mda_core.sv \
    mda_top.sv \
    mda_tt_top.sv
# Stand-in simulation model of the SRAM macro (the stub in src/ is an empty blackbox).
# TODO: switch to the foundry behavioural model from the PDK once its path is confirmed.
MACRO_MODEL = $(PWD)/RM_IHPSG13_1P_1024x16_c2_bm_bist_model.v

ifneq ($(GATES),yes)

# RTL simulation:
SIM_BUILD				= sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))
VERILOG_SOURCES += $(MACRO_MODEL)

else

# Gate level simulation:
SIM_BUILD				= sim_build/gl
COMPILE_ARGS    += -DGL_TEST
COMPILE_ARGS    += -DFUNCTIONAL
COMPILE_ARGS    += -DSIM
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_io/verilog/sg13cmos5l_io.v
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/verilog/sg13cmos5l_udp.v
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/verilog/sg13cmos5l_stdcell.v

# this gets copied in by the GDS action workflow
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v
VERILOG_SOURCES += $(MACRO_MODEL)

endif

# Allow sharing configuration between design and testbench via `include`:
COMPILE_ARGS 		+= -I$(SRC_DIR)

# Include the testbench sources:
VERILOG_SOURCES += $(PWD)/tb.v
TOPLEVEL = tb

# List test modules to run, separated by commas and without the .py suffix:
COCOTB_TEST_MODULES = test

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim