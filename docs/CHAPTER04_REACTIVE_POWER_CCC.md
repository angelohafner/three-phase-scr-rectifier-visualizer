# Chapter 04 — Reactive power and capacitor-commutated converters

## Scope and standards

The new 15-slide offline laboratory describes a **six-pulse** LCC converter and
its **capacitor-commutated (CCC)** counterpart. It follows the distinction in
IEC 60633:2019: a *CCC* has series capacitors **between the transformer and
valves**, not between the AC-filter bus and the grid. The implementation is
an educational **switching-level stiff-current source model**, not a full EMT
network/transformer simulation, a 12-pulse station or a commercial CCC design.

The canonical primary lesson is **How Series Capacitors Assist Thyristor
Commutation**: the phase circuits, capacitor voltage and SCR current transfer
are driven by exactly the same numerical switching state trajectory.

## Electrical quantities and equations

Three sinusoidal phase voltages are normalized to a 1 kV peak phase base and
currents to a 1 kA base, yielding a 1 Ω impedance base. A stiff external DC
current source imposes the pole current. For each phase (source-to-bridge
positive direction), with phase-specific series inductance, resistance and
capacitor:

- `e_k = v_valve,k + R*i_k + X_L*(di_k/dtheta) + v_c,k`
- `dv_c,k/dtheta = X_C*i_k`
- `X_L = omega*L/Z_base`, `X_C = 1/(omega*C*Z_base)`
- `i_a + i_b + i_c = 0`

During upper-group commutation, the incoming and outgoing currents sum to
`+I_dc`; during lower-group commutation they sum to `-I_dc`. The stationary
valve conducts the opposite total current. Because both commutating valves
connect to a common DC bus, subtracting their phase equations gives:

`2*X_L*(di_in/dtheta) = e_in-e_out - (v_c,in-v_c,out) - R*(i_in-i_out)`

The branch equations are integrated with RK4 at 0.2 electrical-degree
sampling intervals; the actual end of commutation is now resolved inside
each step by event bisection. The remainder of that step uses the new
conducting valve pair, avoiding artificial transfer-angle quantization. Six firing
commands are issued 60 electrical degrees apart; switching events complete
when incoming current reaches its full signed `I_dc`. Negative attempted SCR
current, missing forward commutating voltage or overlap crossing the next
firing event invalidate the operating point. The solver does not substitute
an empirical overlap angle. Non-overlap conduction charges the capacitors
according to current paths. A two-dimensional damped Newton shooting method
adjusts two initial capacitor voltages, with the third constrained to zero
sum, until the end-of-cycle mismatch falls below `1e-6 p.u.`. Failure to
converge is reported without fabricated waveforms.

For `C_series=0` the capacitors are bypassed and the corresponding LCC model
uses the same leakage inductance and firing constraints.

## Power and reactive power

The positive current reference is from the three-phase AC source toward the
converter. Fundamental voltage/current phasors are computed directly via
Fourier projection of all three switching waveforms over one complete cycle:

- `P_1 = 0.5 * sum Re(V1_k * conj(I1_k))`
- `Q_1 = 0.5 * sum Im(V1_k * conj(I1_k))`

Both P and Q are normalized to 1.5 MW on the chosen peak-voltage/current
bases. `Q_conv > 0` means reactive power drawn from the ideal AC grid. The
model also calculates the mean bridge DC power and series resistive losses;
periodic stored-energy balance requires `P_AC ≈ P_DC + P_loss`.

The shunt compensation calculation assumes a **fixed AC bus voltage**:
`Q_cap = B_cap * V_phase_peak^2`, with `B_cap` expressed as the normalized
nominal shunt reactive rating, and `Q_grid = Q_conv - Q_cap`. The shunt
capacitor affects the grid reactive-power balance, **not** the SCR switching
solution under the ideal stiff-bus assumption. Grid voltage recovery,
network short-circuit ratio and resonant harmonic filters are not solved.

The term *apparent power* in the chapter refers to **fundamental-frequency**
`S_1 = hypot(P_1,Q_1)` and therefore the reported power factor is the
*displacement factor*, not true total-harmonic apparent power factor.

## Validation and key limitations

- Six-pulse current conservation in every switching interval.
- Capacitor voltage continuity and periodic shooting convergence.
- The same X_L for LCC and CCC comparisons.
- AC fundamental P versus DC power plus resistive losses.
- The overlap angle responds physically to L and C; it is never assigned by a slider.
- Two deterministic FOCUS/FULL vertical plot ranges, neither autoscaling.
- No reverse SCR current and no invented waveform for invalid states.
- Numerical step sensitivity is tested at 0.2° and 0.1°.

A real HVDC-CCC additionally requires converter transformer magnetics,
12-pulse transformer groups, finite DC smoothing, valve recovery, surge
arresters, capacitor bypass and protection, finite grid Thevenin strength,
harmonic filtering and EMT-grade transient validation. The **rectifier
switching model only** is solved numerically here; explanations of inverter
behavior and weak-grid sensitivity are qualitative and specifically labeled.

## Research references

- IEC 60633:2019, *High-voltage direct current transmission — Vocabulary*;
  definition 5.11 of Capacitor-Commutated Converter.
  https://standards.iteh.ai/catalog/standards/iec/4d716d96-f618-4343-ab13-96244d4e9dd5/iec-60633-2019
- *Calculation of Main Circuit Steady-State Parameters for Capacitor Commutated Converter System*, Applied Sciences 13(2), 1171 (2023):
  https://www.mdpi.com/2076-3417/13/2/1171
- ABB Review, *Capacitor commutated converters for HVDC*, 1997:
  https://library.e.abb.com/public/58287671df8ab97ec1256e8a00505641/25-33%20ENG%209702.pdf
- *A Time-Domain Piecewise Analytical AC Harmonic Current Calculation Method Suitable for Capacitor Commutated Converter*, IEEE Transactions on Power Delivery 38(2), 2023:
  https://ieeexplore.ieee.org/document/9857663

## Development checks

```bash
node presentation/tests/chapter04_model_tests.js
python presentation/tests/chapter04_browser.py
python presentation/build_presentation.py --project . --output dist/lcc_hvdc_interactive.html
```
## Native Schemdraw components and topology provenance

All four selectable schematics (LCC, CCC, and their shunt variants) are
generated in Python by `presentation/chapter04_schemdraw.py` from actual
Schemdraw 0.23 component objects. There are no handmade SVG electrical
symbols. The native SCR, Transformer, SourceSin, SourceI, Inductor,
ResistorIEEE, Capacitor, Ground and Dot geometries are converted from
Schemdraw element segments, preserving provenance in each SVG group with
`data-symbol-source="native-instance"`.

The schematic shows three symbolic isolated transformers with a common
secondary star connection. Primary-side shunt capacitors are connected
across the AC bus; CCC series capacitors remain separate physical elements
after the leakage reactors, between transformer and six-SCR bridge.
The positive/negative DC rails are never shorted, but are joined through
a native DC current source and smoothing inductor. Native symbol generation
and connectivity are audited before each HTML build.

The transformer windings are **schematic topology**: the physical converter
model refers the AC source voltage to the transformer secondary and does not
simulate magnetic flux, winding saturation or a complete EMT grid.

The standalone HTML embeds the four authentic SVG variants and only uses
JavaScript to change SCR-conduction styling and numerical annotations.
The capacitor-voltage differential model remains unchanged.

Generate and validate with:
```bash
python presentation/chapter04_schemdraw.py
python presentation/tests/chapter04_native_symbols.py
python presentation/build_presentation.py --project . --output dist/lcc_hvdc_interactive.html
python presentation/tests/chapter04_browser.py
```

### Enlarged native schematic

Use the ENLARGE control in the Chapter 04 circuit panel to view the same
live-highlighted, real Schemdraw SVG in the existing full-screen diagram
viewer. Desktop and mobile interactions are regression tested.

## Independent physical verification (29 October 2026)

An independent numerical reference, `presentation/tests/chapter04_independent_reference.py`,
integrates the LCC and CCC branch equations using SciPy's adaptive
`solve_ivp`, with terminal events for outgoing/incoming valve current
transfer and `scipy.optimize.root` for periodic capacitor-voltage shooting.
It does not reuse the JavaScript RK4 integrator or its event logic.

For exactly matched AC voltage, DC current, firing angle, leakage
inductance, series resistance and base quantities, the independent
reference confirms that at the nominal point, CCC with 26 mF per
phase **shortens the overlap**, **increases the initial signed
commutating drive**, and **reduces fundamental converter Q**.
This conclusion is point-specific; it is not assumed for every feasible
CCC condition.

The central drive chart now includes the instantaneous series
capacitor contribution **and** the resistive redistribution term.
The shunt bank is included in the grid reactive-power balance only
on the lessons where it is actually drawn and connected.
The inverter comparison remains explicitly qualitative: only a
six-pulse rectifier switching problem has been solved dynamically.

Native Schemdraw capacitor symbols do not include conductor leads,
so both contact points are derived from their authentic segment
coordinates and explicit wires close the connections to actual circuit
terminals. Geometry regression validates the real lead endpoints.

## Side-by-side teaching comparison

The LCC/CCC comparison lesson now shows eight comparable measured quantities:
both commutation overlap angles, their signed difference, both fundamental
reactive powers, their difference, and the initial positive commutating
voltage available for the lower-group transfer T4 → T6. The topology selector
is disabled on that lesson, since both solvers already run simultaneously
with exactly identical electrical settings except for the presence/absence
of three native series capacitors. A user cannot inadvertently replace the
CCC reference with a second LCC curve.


## Current teaching interface

The original 15-lesson scope described above is historical. It has been superseded by four focused experiments described in [CHAPTER04_FOUR_LABS.md](CHAPTER04_FOUR_LABS.md). The dynamic CCC equations are unchanged; the Chapter 04 DC current is now an imposed boundary with no physically redundant Ldc/current-source symbols.

## Comparison with matched fundamental active power

The four-laboratory comparison now has a selectable **same-AC-active-power**
mode, in addition to **same-firing-settings** mode. In matched-P mode,
the CCC alpha is solved numerically against the physically calculated
fundamental AC P1 of the LCC reference, while I_dc, voltage, leakage
inductance and phase resistance are held identical. The CCC alpha may
differ and is explicitly shown. Q1, Q/P and displacement PF1 are reported
for each solution. Since equal P1 and equal alpha are different constraints,
the apparent reactive advantage of the CCC may change sign.

The solver has bounded alpha search (0°–90°), an active-power residual
tolerance of 5e-7 p.u., and fail-closed behavior for unavailable operating
points. It does not pretend the original same-alpha comparison was an
equal-power comparison. Additional Node and offline-browser regressions
verify equality of AC P1, conservation of imposed DC current and Q/P
consistency.
