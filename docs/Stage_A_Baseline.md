# MDA Stage A Baseline: First Hardening Result

Nov 6, 2026 · @auritro

## Summary

The Stage A core with both SRAM macros passed every signoff check in the second hardening run: 0 KLayout DRC errors, 0 LVS differences, 0 antenna violations and no setup or hold violations at the 20 ns (50 MHz) clock. All workflow jobs passed.

Standard cells and the two macros use 274,568 µm², 30.4% of the 902,417 µm² core, so 69.6% remains free for Stage B. The slow-corner setup slack of +3.86 ns corresponds to a clock limit of about 62 MHz (estimate).

The first run failed on 4,760 KLayout DRC errors, all in the power-grid via stacks over the data-memory macro. Snapping the stripe edges and via centres created by the stripe script to the 5 nm manufacturing grid removed all of them.

## Run configuration

The run hardened `tt_um_mda` on a 6x4-tile die with a 20 ns clock, from Verilog generated from the SystemVerilog sources.

| Item | Value |
| --- | --- |
| Flow | LibreLane Classic flow through Tiny Tapeout's `tt-gds-action` (ihp-cmos5l), PDK IHP SG13CMOS5L |
| Top module | `tt_um_mda` (`mda_tt_top.sv`) |
| Sources | 26 SystemVerilog files converted with sv2v into `src/mda_synth.v` (24 modules, 2,612 lines), macro variant selected with `MDA_SRAM_MACRO`; macro stubs listed separately |
| Die / core | 1289.28 × 710.64 µm (0.916 mm²) / 0.902 mm², 218 rows |
| Clock | `clk`, 20 ns (50 MHz) |
| Instruction memory | `RM_IHPSG13_1P_1024x16_c2_bm_bist`, 236.80 × 336.46 µm, instance `u_top.u_imem.u_sram` at (3.36, 3.78) µm, orientation FS |
| Data memory | `RM_IHPSG13_1P_256x32_c2_bm_bist`, 416.64 × 118.78 µm, instance `u_top.u_dmem.u_sram` at (250.64, 3.78) µm, orientation FS |
| Power grid | Metal4-only stripes (pitch 48.34 µm, width 2.1 µm); the `ExtendPowerStripes` step moves stripes onto the macro power columns |
| Signoff checks | KLayout DRC on, Magic DRC off, LVS on, Magic illegal overlaps non-fatal |

The two macro areas (79,673.7 µm² and 49,488.5 µm²) add up to 129,162 µm², matching the macro area in the flow metrics.

## Signoff results

Every physical and timing check passed in run 2; run 1 differed only in KLayout DRC.

| Check | Run 2 | Run 1 |
| --- | --- | --- |
| KLayout DRC | 0 errors | 4,760 errors |
| LVS | 0 device, net, property or pin differences | 0 |
| Antenna | 0 violating nets and pins (21 diodes inserted) | 0 (24 diodes) |
| Detailed routing DRC | 0 (converged in 8 iterations) | 0 (6 iterations) |
| Setup and hold timing | 0 violations in all three corners | 0 |
| Lint | 0 errors, 81 warnings | 0 errors, 81 warnings |
| Inferred latches, unmapped cells, floating nets | 0 | 0 |
| Magic DRC | Off by configuration; KLayout DRC and LVS are the physical signoff | Same |
| Magic illegal overlaps | 138, non-fatal by configuration | 138 |

## Area

Standard cells and macros occupy 274,568 µm², 30.4% of the 902,417 µm² core, leaving 627,849 µm² (69.6%) free.

| Item | Cells | Area (µm²) | Share of core |
| --- | --- | --- | --- |
| Macros (1024x16 and 256x32) | 2 | 129,162 | 14.3% |
| Standard cells | 10,452 | 145,406 | 16.1% |
| of which combinational (multi-input) | 6,887 | 65,139 | 7.2% |
| of which flip-flops | 1,016 | 49,773 | 5.5% |
| of which timing-repair buffers | 2,055 | 25,387 | 2.8% |
| of which clock buffers and inverters | 165 | 3,317 | 0.4% |
| of which inverters | 232 | 1,263 | 0.1% |
| of which antenna cells | 97 | 528 | 0.1% |
| Free core area |  | 627,849 | 69.6% |

Filler cells (54,083 cells, 624,607 µm²) fill the free area and are not counted as used.

## Timing

All three corners meet setup and hold at the 20 ns clock; the slow corner has the least margin, +3.86 ns, which corresponds to a clock limit of about 62 MHz.

| Corner | Setup slack (ns) | Shortest period (ns) | Equivalent clock (MHz) | Hold slack (ns) |
| --- | --- | --- | --- | --- |
| Fast (1.32 V, −40 °C) | +13.57 | 6.43 | 155.6 | +0.109 |
| Typical (1.20 V, 25 °C) | +10.00 | 10.00 | 100.0 | +0.291 |
| Slow (1.08 V, 125 °C) | +3.86 | 16.14 | 62.0 | +0.635 |

Shortest period = 20 ns − setup slack. The figure uses the flow's generic SDC (no I/O constraints) and does not model clock uncertainty, so it is an estimate. The limiting path has not been identified.

## Power and other metrics

The flow estimates 6.44 mW total power at the 20 ns clock, with default switching activity rather than measured activity.

| Metric | Value |
| --- | --- |
| Total power | 6.444 mW (internal 5.792, switching 0.612, leakage 0.040) |
| Flip-flops | 1,016 (the three register files hold 768 of them) |
| Clock tree | 126 clock buffers and 39 clock inverters; the clock net drives 1,019 terminals |
| Hold buffers / setup buffers | 1,143 / 0 |
| Routed nets | 10,365, total wirelength 498,266 µm, longest wire 1,238 µm |
| Vias | 70,270, all single-cut |
| Worst IR drop | 0.19 mV on VPWR (no supply locations were given, so the figure is not meaningful) |

## Warnings reviewed

None of the warnings below fails the flow; the three that bear on later work are the slew, capacitance and fanout counts.

| Warning | Count | Assessment |
| --- | --- | --- |
| Max slew violations | 35 slow / 17 typical / 6 fast corner | Non-fatal. Not addressed; review if the clock is raised |
| Max capacitance violations | 6 in every corner | Non-fatal. Not addressed |
| Max fanout violations | 156 in every corner | Non-fatal. Not addressed |
| GRT-0281 large clock fanout | 1 (1,019 terminals) | Expected for one flat clock domain |
| GRT-0115 global routing congestion | 1 | Detailed routing still converged with 0 violations |
| DRT-0418 macro pins off the routing grid | 49 | Routing completed; no DRC errors resulted |
| PSM-0038 / PSM-0039 and power-grid violations | 1,001 / 4 / 692,769 | The flow states these can be ignored when LVS passes; LVS passes. The grid check runs before `ExtendPowerStripes` joins the macro columns |
| Magic illegal overlaps | 138 | Non-fatal by configuration; Magic extracts the macros from their LEF abstract |
| Lint warnings | 81 | Non-fatal; 0 lint errors |
| Generic SDC, missing IR-drop supply locations, macro parasitics, ORD-0032, DRT-0349 | Informational | No action |

## History: run 1 and run 2

Run 1 failed on 4,760 KLayout DRC errors; run 2 passed after one change to the power-stripe script.

| Metric | Run 1 | Run 2 |
| --- | --- | --- |
| KLayout DRC errors | 4,760 | 0 |
| Standard cells | 10,455 | 10,452 |
| Standard-cell area (µm²) | 145,422 | 145,406 |
| Worst setup slack (ns) | +3.888 | +3.863 |
| Worst hold slack (ns) | +0.106 | +0.109 |
| Max slew violations (slow corner) | 34 | 35 |
| Antenna diodes | 24 | 21 |
| Routed vias | 70,330 | 70,270 |
| Detailed-route DRC errors at iteration 0 / iterations to reach 0 | 45 / 6 | 1,043 / 8 |
| Total power (mW) | 6.4435 | 6.4443 |

**Cause.** The stripe script drops a via stack on every same-net rail at the centre of each stripe it places on a macro column, without snapping the centre to the 5 nm manufacturing grid. A column whose width is an odd number of 5 nm steps has its centre 2.5 nm off the grid, which places the via cuts and the Metal2 and Metal3 pads off-grid. The errors were: Metal2 and Metal3 off-grid 156 each, Via1 to Via3 off-grid 780 each, V1.a, V2.a and V3.a 390 each, V1.b, V2.b and V3.b 312 each, Metal4 off-grid 2. The figure 390 equals 5 stripes × 78 rails above the 256x32 macro.

**Fix.** `odb_sram_stripes.py` now snaps stripe edges and via centres to the 5 nm grid and rounds LEF unit conversions. The diagnosis came from the error counts and the script source; the clean result in run 2 is the confirmation.

Run 2 also contained the ALU compare change (the all-ones result written as an explicit replication) and regenerated Verilog, which may account for the 3-cell difference. The routing differences are not attributed to a single cause.

## Implications for Stage B

Area does not limit the Stage B scope: about 318,500 µm² of additional standard cells fit before the core reaches the 60% placement-density target.

- **Area budget.** At 60% of the 773,255 µm² non-macro core, the core holds about 463,953 µm² of standard cells, 3.2 times the current 145,406 µm² (estimate; routability is not modelled).
- **Cost rule of thumb.** The flip-flops average about 49 µm² each (49,773 µm² for 1,016). Stage B proposals that add hardware (P2, P7 to P9) can be costed against this baseline.
- **Memory sizes.** The data-memory macro uses 5.5% of the core and the instruction-memory macro 8.8%, so the DMEM size decision is not forced by area.
- **Timing.** The slow-corner critical path takes 16.1 ns of the 20 ns period. Stage B logic that deepens that path consumes the 3.86 ns margin, and a clock above about 60 MHz would first require locating the limiting path.
- **Decision gate.** The 8 Dec go/no-go for Stage B hardware can use these figures as the Stage A reference.

## Open items and limitations

This baseline covers Stage A only, and six points limit how far its numbers can be trusted.

- **Gate-level test models.** The gate-level test uses stand-in simulation models of the two macros, not the foundry models. The foundry 256x32 model exists but also needs the PDK behavioural SRAM module, and has not been used.
- **Clock limit.** The 62 MHz figure is derived from slack with a generic SDC. The limiting path is unidentified and I/O timing is unconstrained.
- **Power.** The estimate uses default switching activity; no activity file from a real program was applied.
- **IR drop.** No supply locations were given to the analysis, so the IR-drop figures are not meaningful.
- **Equivalence.** The SystemVerilog is verified locally (decoder exhaustive, about 490 random three-thread programs against the independent simulator). The converted Verilog that was synthesized is covered by the CI cocotb test and the gate-level test, not by a formal equivalence check.
- **Physical signoff.** Magic DRC is off; physical signoff rests on KLayout DRC, LVS and the Tiny Tapeout precheck.

## Reproduction

The numbers come from the second CI run of the `gds` workflow, using the files below, and the same run saves its reports as the `reports` artifact.

| File | Role |
| --- | --- |
| `src/mda_synth.v` | Synthesis source, generated by `python3 tools/gen_synth.py` (sv2v) from the SystemVerilog listed in `rtl.f` |
| `src/config.json` | Flow configuration: two macros, `MDA_SRAM_MACRO` define, PDN settings |
| `odb_sram_stripes.py` | Stripe step with per-macro LEF lookup and 5 nm grid snapping |
| `info.yaml`, `test/` | Tiny Tapeout project file, cocotb test and macro stand-in models |
| `.github/workflows/gds.yaml` | Workflow with the report upload step |

Local checks that precede a push:

```
python3 tools/gen_synth.py --check
bash tools/lint.sh
python3 verif/harness_decoder.py
python3 verif/mda_e2e.py directed
python3 verif/mda_e2e.py fuzz --count 100
```

The metrics are in `runs/wokwi/final/metrics.json` of the run, and the DRC counts in the `klayout-drc` step folder.
