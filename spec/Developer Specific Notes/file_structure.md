# MDA File Structure

## Expected File Structure

```txt
info.yaml                                  # template
docs/                                      # template
test/                                      # template
.github/                                   # template
spec/                                      # mda-only
fw/                                        # mda-only
tools/                                     # mda-only
verif/                                     # mda-only
rtl.f                                      # A
src/mda_pkg.sv                             # A
src/mda_isa_pkg.sv                         # A (generated from isa.yaml)
src/mda_tt_top.sv                          # A (IO stubbed)
src/mda_top.sv                             # A (IO stubbed)
src/mda_core.sv                            # A
src/mda_sched.sv                           # A
src/mda_fetch.sv                           # A
src/mda_pc.sv                              # A
src/mda_if_id.sv                           # A
src/mda_id_ex.sv                           # A
src/mda_decoder.sv                         # A (decodes all 35 instructions)
src/mda_regfile.sv                         # A (X)
src/mda_ex.sv                              # A
src/mda_alu.sv                             # A (X)
src/mda_shifter.sv                         # A
src/mda_branch_unit.sv                     # A
src/mda_lsu.sv                             # A
src/mda_wb.sv                              # A
src/mda_spatial.sv                         # A (stub), completed in B
src/mda_cfg_unit.sv                        # B
src/mda_events.sv                          # B
src/mda_flags.sv                           # A (Z/N/C), event flags added in B
src/mda_doorbell.sv                        # B
src/mda_cond.sv                            # A (jof/joc), shared with waitev in B
src/mda_sleep.sv                           # B
src/mda_timer.sv                           # B
src/mda_io.sv                              # B
src/mda_pins.sv                            # B
src/mda_pin_in.sv                          # B
src/mda_pin_cfg.sv                         # B
src/mda_pin_watch.sv                       # B
src/mda_pin_out.sv                         # B
src/mda_engine.sv                          # B
src/mda_eng_sched.sv                       # B
src/mda_eng_shift.sv                       # B
src/mda_imem.sv                            # A
src/mda_dmem.sv                            # A
src/mda_sram_sim.sv                        # A
src/mda_loader.sv                          # B
src/mda_crc16.sv                           # B
src/mda_sync.sv                            # A
src/RM_IHPSG13_1P_1024x16_c2_bm_bist.v     # A
src/RM_IHPSG13_1P_256x32_c2_bm_bist.v      # A
```
