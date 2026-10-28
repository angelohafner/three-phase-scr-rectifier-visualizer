# Three-phase SCR rectifier — R versus RL teaching sequence

## Recommended order

1. Pure R load and six-pulse bridge: ideal voltage sources, no source/commutation inductances, no DC reactor.
2. R-load firing delays: α = 0°, 30°, 75°, and 90°.
3. Zero-current intervals and SCR extinction for α > 60°.
4. Same firing angle, R versus RL: source voltages and resistance kept identical.
5. RL load: differential current response, stored magnetic energy, and possible current continuity through short negative DC voltage intervals.
6. Introduce **AC-side commutation inductance** separately, so a nonzero overlap angle μ is not confused with the *DC-side smoothing inductance*.

## Angular reference and ideal R load

Positive-sequence balanced source voltages:

- `v_a = V_peak cos θ`
- `v_b = V_peak cos(θ − 120°)`
- `v_c = V_peak cos(θ + 120°)`

The natural commutation for pair T1/T6 is at θ = 0°. Firing instants occur at `θ = α + 60° k`. At these instants the six conducting pairs follow T1/T6, T3/T6, T3/T2, T5/T2, T5/T4 and T1/T4.

Under **ideal sources with no AC commutation inductance**, a pure resistive load satisfies `i_dc = v_dc / R` while conducting, and `i_dc = v_dc = 0` when SCRs have extinguished.

The maximum length of an R-load pulse is `min(60°, 120° − α)`, for `0° ≤ α < 120°`. Thus:

| α | Pulse duration | Zero-current interval every 60° |
|---|---:|---:|
| 0° | 60° | 0° |
| 30° | 60° | 0° |
| 75° | 45° | 15° |
| 90° | 30° | 30° |

For α > 60° the following firing event occurs after all SCRs have turned off. The drawings assume **double firing pulses (or sufficiently wide pulses)** for successful latching of both SCRs in the new pair. No nonexistent current path is highlighted during a blocked interval.

## Dynamic RL load

The RL load uses the piecewise differential equation `L di_dc/dt + R i_dc = v_dc` while SCRs conduct. A nonnegative current constraint and event-driven gating/extinction are imposed: SCR current cannot spontaneously reverse through a blocked valve. The generator numerically integrates the load current in a periodic steady-state approximation.

The RL example uses `L = 8 mH`, `R = 1 Ω` (equivalent illustrative units), and `f = 60 Hz`. It maintains current across a few intervals of negative `v_dc` at α = 75°. Other parameters can produce discontinuous conduction.

**This model does not calculate AC commutation overlap**. The introductory R/RL cases assume μ = 0°. The later LCC chapter contains separate, idealized overlap states with continuous DC-current approximation. The models are educational, not EMT simulations.

## Reproducible figures

```bash
python -m pip install -r requirements-waveforms.txt
python rectifier_loads.py --output-dir output_lcc/rectifier/resistive_load
```

Generated folders:

- `circuits/` — vector SCR path drawings, including all-OFF states.
- `waveforms/` — source/line voltages, DC voltage/current and six SCR currents.
- `sheets/` — circuit + waveforms in one editable SVG and PNG preview.
- `comparisons/` — identical-scale R versus RL plots.

Labels use STIX-style mathematical italic variables, upright physical units and upright descriptive subscripts; English code comments and figure annotations are used throughout.
