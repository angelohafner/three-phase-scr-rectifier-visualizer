# Four DC loads and SCR anode-to-cathode voltage — engineering notes

This page documents the **independent educational** LCC HTML lecture. Its restrained layout is inspired by conventional Siemens PTI engineering presentations, but **it is not an official Siemens document**; no corporate logo is used.

## Sign convention

Current `i_dc >= 0` flows from the bridge positive pole through `L`, optional `R`, and signed source `E_dc` toward the bridge negative pole. The positive terminal of the signed ideal DC EMF is on the **upper** side; `E_dc > 0` opposes positive rectifier current and `E_dc < 0` is an active source supplying energy to the bridge. For the connected bridge:

`L di_dc/dt = v_bridge - R i_dc - E_dc`.

Use `L=0` to obtain `i_dc=max(0,(v_bridge-E_dc)/R)` during an eligible ideal conduction interval, not to divide by an absent reactor. The pure R and RL modes automatically set `E_dc = 0`; the LE mode sets `R = 0`. R/RL/RLE require positive R and LE/RLE require positive L. Unit bases in the simple per-unit curves are equivalent teaching quantities, not specified physical equipment ratings.

The model uses ideal 6-pulse switching with negligible AC commutation inductance. Gating is treated as a wide-pulse sequence. It can show discontinuous current, sustained current and inversion **only where current and transferred bridge power support it**. Alpha alone does not demonstrate inversion.

A pure LE source/inductor without damping does not generally have an asymptotically stable periodic current solution. The HTML labels such traces as initialization dependent, rather than presenting them as unique steady state.

## SCR A-K voltage measurement

Bridge valve positions remain:

- Upper: `T1` at phase A, `T3` at B, `T5` at C.
- Lower: `T2` at phase A, `T4` at B, `T6` at C.

For a conducting upper phase `u` and lower phase `l`, define `V+ = v_u` and `V- = v_l` in the ideal zero-overlap model. For upper valves, `v_AK = v_phase - V+`. For lower valves, `v_AK = V- - v_phase`. Thus both conducting valves have `v_AK = 0`, and blocked valves can have positive (forward blocking) or negative (reverse blocking) voltage. When the entire bridge is OFF, the absolute DC pole potentials cannot be determined without an explicit additional circuit reference: such voltage samples are `NaN` and render as **gaps**, not made-up zeros.

In the original rectifier/inverter/HVDC *overlap* chapters, current transfer is a simplified surrogate, not a nodal inductive network solution. Individual A-K voltages in overlap intervals are accordingly **unresolved and omitted**. Outside overlap, the same node-potential formulas apply with the inverter valve orientation reversed.

## Plotting and notation

Both Canvas and Python/Matplotlib charts use color **plus dash pattern**; lines have opacity below one and conduction intervals use low-opacity backgrounds. Numbers and physical units are upright. Scalar symbols and Greek variables are italic, with roman descriptor subscripts and roman numerical subscripts.

The HTML remains completely offline. It includes all inline circuit SVG assets and supports live sliders for alpha, L, R, signed E, voltage, overlap, current, and animation speed. PowerPoint generation is intentionally excluded from the HTML build workflow.

## Validate

```bash
python -m pytest -q tests presentation/tests
python presentation/build_presentation.py --project . --output dist/lcc_hvdc_interactive.html
python rectifier_load_extended.py --out output_lcc/extended
```

The first two source files of each graphical model are independent of the GUI, and the Python tests cross-check the equation and SCR voltage signs. The RLE current-integrator uses exponential stepping for R>0 and exact-slope stepping for R=0; figures remain conceptual, not EMT results.
