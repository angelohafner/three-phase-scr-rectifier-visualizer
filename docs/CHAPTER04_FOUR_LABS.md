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
