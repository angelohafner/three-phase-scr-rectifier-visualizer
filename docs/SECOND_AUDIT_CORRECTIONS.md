# Independent LCC HVDC presentation audit — corrections

**Date:** 28 October 2026. **Scope:** the 82-slide offline HTML lecture.
**Delivery:** source updates and regenerated self-contained HTML; no PPTX.

## Electrical reference — corrected

Use a **common positive DC current reference from rectifier to inverter** at
both converter terminals. The signed converter contributions follow:

| Converter | Common-reference DC voltage | Signed DC converter power | Interpretation |
|---|---|---|---|
| Rectifier | `Vdc,r > 0` | `Pdc,r = Vdc,r Idc > 0` | Delivering power into the DC link |
| Inverter | `Vdc,i < 0` | `Pdc,i = Vdc,i Idc < 0` | Absorbing power from the DC link and delivering to the AC system |

The two contributions do **not** represent two simultaneously imposed independent
ideal DC bus voltages. They are converter-side contributions on a common
current-direction reference; a complete physical link additionally has resistive
and inductive voltage drops and control dynamics. The waveform model remains
simplified and does not enforce instantaneous link voltage balance.

The former `LCC.sample('inverter')` returned a positive local bridge magnitude
while the current-source comparison negated it. The return values `dc` and
`dcIdeal` are now signed consistently in `LCC.sample`. The source comparison
uses those values without an additional sign inversion. The chart headings
explicitly say **signed DC voltages**.

## Visual corrections

1. The inverter `Timing model` fact box now wraps the longer angle expression
   and its value no longer extends beyond its allocated cell.
2. All technical fact boxes use constrained grid cells, wrapping rather than
   forcing an overflowing single line. The cover's decorative artwork is clipped.
3. At mobile width (390 px tested), state-slide viewers offer **Circuit** or
   **Waveforms**, with one selected waveform panel shown at full available height.
4. The current-source chapter offers a mobile choice of **Circuit / Graph 02 /
   Graph 03**; only the selected region is shown at full available height.
5. The joint HVDC overview no longer repeats the same DC-voltage panel twice.
   In mobile waveform mode, title and line-style legend occupy different rows.

## Build provenance and verification

- Existing model tests: **516 passed, 1 skipped** locally after correction.
- 82-slide Chromium scan at **1600 × 900**: **zero horizontal overflows**, zero
  missing circuit/graph panels, zero reported JavaScript exceptions.
- Focused slides 46 and 61 at **390 × 844**: a single selected waveform chart
  occupies > 400 px in height; circuit/graph switching remains functional.
- The constant-current commutation chapter's individual chart selection was tested.
- Numeric JavaScript comparison verifies signed inverter voltage and power are
  the same in the LCC and current-source model, with `Pdc,i < 0` for the sample case.
- The compile step creates a JSON manifest with per-source Git blob SHA-1,
  compiled HTML SHA-256 and a source revision when present.
- The bundled GitHub CI workflow includes the new browser/mobile regression.

## Limitations

The schematics and plots remain **conceptual 6-pulse LCC models**, not EMT
simulation, hardware ratings, or a solution for the full HVDC power-flow
operating point. The idealized commutation-overlap midpoint approximation and
assumed inter-station angular offset continue to be documented explicitly.
