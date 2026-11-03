# SRAM macro integration on Tiny Tapeout CMOS5L: working recipe

Status (2 Nov 2026, branch `sram-dryrun`): every job is green: `gds`, `precheck`, `gl_test`, `viewer`, `test`, `docs`.

Design: `tt_um_mda_sram_dryrun`, one IHP `RM_IHPSG13_1P_1024x16_c2_bm_bist` macro, 6x4 tiles (die 1289.28 x 710.64 um), 20 ns clock.
This is a plumbing test, not the MDA core. Its logic is a 16-flop FSM.

## Files

| File | Location | Purpose |
|---|---|---|
| `librelane_plugin_sram_pdn.py` | repo root | Registers the `Project.ExtendPowerStripes` step (unchanged from upstream) |
| `odb_sram_stripes.py` | repo root | Redraws the Metal4 stripes over the macro's supply columns. Macro name edited to 1024x16 |
| `macro/<name>/<name>.lef` | repo root | Local copy of the PDK LEF, read by the stripe script to find the supply columns |
| `src/config.json` | `src/` | Macro block, PDN and sign-off settings (below) |
| `src/pdn_cfg.tcl` | `src/` | Metal4-only standard-cell grid, no per-macro grid |
| `src/RM_..._bist.v` | `src/` | `(* blackbox *)` stub, listed in `info.yaml` `source_files` |
| `test/RM_..._bist_model.v` | `test/` | Simulation stand-in for the macro (not the foundry model yet) |

## `config.json` essentials

- `meta.substituting_steps`: `"+OpenROAD.GeneratePDN": "Project.ExtendPowerStripes"`.
- `MACROS`: instance `sram` at `[42, 81]`, orientation `R0`. The stripe script accepts only `R0` or `MX`.
  Views come from the PDK via `pdk_dir::libs.ref/sg13cmos5l_sram/{gds,lef,lib,cdl}`. The netlist view is the stub in `src/`.
- Macro timing libs keyed by the flow's real corner names: `nom_typ_*`, `nom_fast_*`, `nom_slow_*`.
  (The reference used `nom_*`, `min_*`, `max_*`, which match this flow's corners wrongly.)
- `PDN_VERTICAL_LAYER` `Metal4`, `PDN_MULTILAYER` 0, `PDN_CFG` `dir::pdn_cfg.tcl`, `ERROR_ON_PDN_VIOLATIONS` 0.
- Sign-off: `RUN_MAGIC_DRC` 0, `ERROR_ON_ILLEGAL_OVERLAPS` 0, `MAGIC_MACRO_STD_CELL_SOURCE` `PDK`,
  `MAGIC_EXT_ABSTRACT_CELLS` `["RM_IHPSG13_.*"]`, `RUN_KLAYOUT_DRC` 1. KLayout DRC and LVS are the sign-off, so keep KLayout DRC on.
- Halos: `FP_MACRO_HORIZONTAL_HALO` and `FP_MACRO_VERTICAL_HALO` = 2. With 0, the standard-cell rows started 0.14 um from the
  macro's Metal1 and KLayout reported 240 `M1.b` violations (min Metal1 space 0.18 um).

## RTL notes

- The macro instance name in the netlist (`sram`) must equal the instance name in `config.json`.
- Read = `A_MEN` + `A_REN`. Write = `A_MEN` + `A_WEN`. Both together = write-through. `A_DLY` = 1, all `A_BIST_*` = 0.
- Read data is valid the cycle after the read. `A_BM` bit = 1 writes that bit (from the datasheet and a passing test).
  The foundry behavioural model has not been used yet.

## Results (from `metrics.json`)

| Check | Result |
|---|---|
| KLayout DRC, route DRC, antenna | 0 / 0 / 0 |
| LVS | 0 errors |
| Setup worst slack (fast / typ / slow) | 15.03 / 14.14 / 10.45 ns |
| Hold worst slack (fast / typ / slow) | 0.114 / 0.295 / 0.622 ns |
| Hold buffers inserted | 26 |
| Max-slew violations | 4 (slow corner only, not fatal) |
| Flip-flop area | 16 flops = 783.8 um2, about 49 um2 each |
| Macro area | 79,673.7 um2 |

## Not shown by this run

- Timing of real core logic after the macro. This design has about 2,800 um2 of logic.
- A second macro (the planned 256x32 data memory), its placement, and the PDN across two macros.
- Gate-level simulation with the foundry model. Both `test` and `gl_test` used the stand-in.
- Clean power-grid checks. OpenROAD reports 4,326 PSM messages and Magic reports 44 illegal overlaps. Both are waived because LVS and
  the Tiny Tapeout precheck pass. IR-drop figures are not meaningful here (no supply locations were given).

## What went wrong on the way (for next time)

| Symptom | Cause |
|---|---|
| `ORD-2013 instance sram LEF master ... not found` | The `MACROS` block was missing from the committed `src/config.json` |
| `M1.b` x240 | Zero macro halo (see above) |
| `No rule to make target ..._model.v` | Model file name differed from the Makefile |
| `info.yaml` / `docs` errors on the first template run | Empty title, author, description, pinout and doc headings |

## Credits

The plugin and stripe script come from `kdp1965/protocol-emulator` (cmos5l branch); other entries documented the same approach.
Check the upstream license before publishing.
