# Chapter 00 — Thyristor Fundamentals

This chapter is an introductory single-SCR half-wave exercise, placed before the
three-phase six-pulse LCC bridge. **It is educational, not an EMT simulation.**

## Circuit conventions

The circuit contains one sinusoidal voltage source, a conventional SCR, a series
R or RL load, and a closed metallic return. **There is no freewheeling diode.**
Positive voltage is the source's upper terminal relative to its lower terminal,
and current is positive from the source through the SCR and load to the return.

The gate pulse occurs at electrical angle **α** during the positive half-cycle.
The SCR turns on when it is forward-biased. The removal of the gate signal does
not turn off an already conducting conventional SCR.

## Pure R load

During conduction: `i_T = v_s/R` and `v_o=v_s`. The current reaches zero at
`180°`, the zero crossing of the source. Between `180°` and the next forward-
biased valid gate pulse, the SCR is blocked. The resistor has no stored energy.

## RL load

While the SCR conducts, the model solves

`L di_T/dt + R i_T = V_m sin(ωt)`.

For a pulse at `α` and zero initial current, the exact solution is:

`i_T(θ) = (V_m/Z) [sin(θ−φ) − sin(α−φ) exp(−(θ−α)/tan φ)]`,

where `φ=atan(ωL/R)` and `Z=sqrt(R²+(ωL)²)`. β is the **first
positive-current extinction zero after 180°**, obtained by bisection of this
analytical waveform; it is not manually shifted.

The magnetic energy is `W_L = L i_T²/2`. Between 180° and β the sinusoidal
source voltage is negative, **but the SCR current remains positive**. During
this interval, the inductor's stored energy supports conduction and is partly
returned to the source, while resistance dissipates energy. Voltage reversal
alone does not turn off the SCR.

## Markers and interaction

The essential teaching slide, *Why Does the SCR Remain ON After 180°?*, shows:

- The **fixed 180° marker** identifying the source-voltage zero crossing.
- A **calculated movable β marker** responding continuously to α, R, and L.
- An amber translucent band between 180° and β.
- A blue translucent negative-source-voltage lobe and a red positive-current
  region in the same interval.
- A separate movable instantaneous-angle cursor θ.

All four primary controls (α, R, L, source peak) and the θ slider remain mounted
while dragging. The circuit, current path, SCR terminal voltage, energy and
explanatory text are updated without recreating the controls.

## Simplifications and physical limits

- Ideal SCR and ideal sinusoidal source; zero switching loss.
- Holding current is approximated as zero; real SCRs require a holding-current
  threshold and sufficient reverse-recovery time for successful blocking.
- No freewheeling diode, commutation overlap, transformer leakage, snubber or
  source impedance is included in this introductory half-wave circuit.
- β is a natural **current-extinction angle**, not the inverter extinction
  margin γ, and not the LCC **commutation overlap** μ.
- R and RL figures use the same source and compatible plot scales for comparison.
- Physical units are V, A, Ω, mH and J; variable symbols are italic and numbers
  and units upright.

## Rebuild

```bash
python halfwave_figures.py --output-dir output_lcc/fundamentals
python presentation/build_presentation.py --project . --output dist/lcc_hvdc_interactive.html
python -m pytest -q tests presentation/tests
python presentation/tests/browser_fundamentals.py
```

The standalone HTML can be opened directly in a browser without a network
connection or local HTTP server. The inlined SVG graphics are editable source
assets; reference PNGs are for convenient previews.
