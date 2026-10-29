# Chapter 04 — Four focused laboratories

The previous 15 small lessons have been replaced by **four focused interactive laboratories**. The first 82 slides are unchanged, for **86 slides in total**.

| Laboratory | Adjustable parameters | Physical observations |
|---|---|---|
| 1. Reactive Power in LCC | Firing angle, imposed DC current, AC phase voltage, commutation inductance | Fundamental current phasor, AC currents, Q1, P1, displacement PF and computed overlap |
| 2. Shunt Compensation | Shunt capacitor rating and converter operating parameters | Q absorbed by converter, Q injected by capacitor, Q supplied by grid, unchanged intrinsic SCR currents at fixed voltage |
| 3. Series Capacitors and Commutation | Series C, Lc, firing angle, current and voltage | Dynamic capacitor contribution, net commutating drive and incoming/outgoing SCR current transfer |
| 4. LCC versus CCC | Identical source, current, firing, leakage and resistance; vary series C | LCC/CCC circuits side by side, synchronized current transfer, direct Q1 and overlap differences |

A minimal common presentation structure is used: electrical schematic, two
physically linked plots, a short group of relevant sliders and quantitative
readouts. The FOCUS and FULL chart axes remain fixed while parameters vary.

## Important DC-model distinction

The six-pulse switching calculation imposes DC current as an **external
operating condition**. Displaying a smoothing reactor in series with an ideal
current source was misleading, because the ideal source already fixes the
current and the reactor has zero voltage in that particular calculation.
Therefore Chapter 04 now shows **open positive/negative DC terminal boundaries**
and labels the imposed I_dc, with no redundant source or Ldc.

This is not a claim that industrial HVDC links lack smoothing reactors. The
earlier complete HVDC link chapter retains its physical DC-side components.

## Model and operating limits

The CCC still integrates the dynamic voltages on the three AC-side series
capacitors and determines periodic steady state and current-transfer events
from the switching equations. It does not replace capacitance by a simple
reactance correction.

The model is a six-pulse rectifier with stiff external current and AC bus.
It is not an EMT model of a 12-pulse CCC station, a finite AC grid or a
CCC inverter during a commutation failure.

## Validation

The repository pipeline checks the four Schemdraw topologies, zero DC-source/
smoothing-reactor symbols within this chapter, 144 switched-model parameter
scenarios, six independent LCC/CCC benchmark cases, fixed axes, old chapter
regressions and four-lab browser control interaction.

Build with:
`python presentation/build_presentation.py --project . --output dist/lcc_hvdc_interactive.html`

## Fair reactive-power comparison (additional comparison mode)

The fourth laboratory now offers two clearly labeled calculation modes:

- **Same firing settings:** LCC and CCC use identical phase voltage, imposed
  DC current, leakage reactor, phase resistance, and firing angle. Their AC
  fundamental active powers are permitted to differ.
- **Same fundamental active power P1 (default):** The LCC firing angle remains
  the user-controlled reference. The CCC firing angle is numerically adjusted
  until its fundamental AC active power agrees with the LCC within
  5e-7 p.u. The DC current, phase voltage, leakage inductance, series
  resistance and capacitor value are otherwise held fixed. The matched CCC
  firing angle may lie between 0° and 90°, while the reference LCC slider
  is limited to 0°–60°. No additional circuit dynamics is fabricated.

The comparison displays P1, Q1, Q/P, the *fundamental displacement* PF1,
both firing angles, both calculated commutation overlaps, and the signed
difference in Q. Q/P is the ratio of fundamental AC powers at the supply
reference; it is **not** the ratio of total apparent power or the DC-side
power factor. If power matching cannot find a valid periodic CCC point,
the lab explicitly reports that matching is unavailable instead of
displaying invented waveforms.

A physically important teaching result: at the nominal 15°/0.8 p.u. LCC
operating point, the earlier same-angle CCC comparison reduces Q1, but
matching AC P1 instead moves CCC alpha to approximately 16.86° and can
make its Q1 **slightly greater** than the LCC value. The CCC is therefore
not guaranteed to have lower reactive demand for the same active power.

The matching method and its model/feasibility regression tests are in
presentation/src/ccc_power_match.js and
presentation/tests/chapter04_equal_power.js.

The matched-power solver is now accurate to 5e-7 p.u. (fundamental AC P1) so nominal LCC and CCC active-power readings agree even at four displayed decimal places. The circuit viewer restores the complete native Schemdraw topology when enlarged; the smaller comparison tiles focus on the valves and commutation components.

## Series-capacitance sensitivity laboratory improvements

The third laboratory now prioritizes three synchronized physical views:
the six-pulse electrical circuit with native Schemdraw capacitors; **full
360° instantaneous capacitor phase voltages** above the net source+capacitor+
resistance commutating drive; and a 30° (FOCUS) / 60° (FULL) zoomed
incoming/outgoing SCR current transfer. The latter two graphs overlay a
separately solved reference capacitance, selected from 8/12/26/50/73/100 mF.
All charts use fixed documented axes.

A collapsed sensitivity table provides C, Xc/Xl, phase-voltage peak and RMS,
initial net commutating drive, measured overlap, fundamental Q1 and mean
stored capacitor energy. The active capacitance slider spans 8–100 mF.
A 432-combination corner sweep with C=8/12/26/100 mF and extremes of
alpha, I_dc, L_c and V_phase was valid within this educational model.
This does not establish commercial equipment ratings.

See [series-C technical sensitivity audit](CHAPTER04_SERIES_CAPACITOR_AUDIT_2026-10-29.md)
for the physical explanation and three independent parameter sweeps.
