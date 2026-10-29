# Chapter 04 · Series Capacitors and Commutation — physical and visual sensitivity audit

**Date:** 29 October 2026  
**Scope:** Laboratory 03 of the 86-slide standalone HTML presentation  
**Model:** Six-pulse CCC rectifier with imposed DC current and three dynamically integrated series-capacitor voltage states.

## Diagnosis

The previous slide did recalculate the capacitor voltage and commutation overlap as C was moved. The weak visual response arose mainly from the presentation, not from a missing capacitor term in the ODE:

1. The current-transfer interval was typically 5–18 electrical degrees, but the chart displayed a fixed 60-degree interval, compressing the interval into the left side of the panel.
2. The commutation-drive chart used a broad symmetric voltage domain, masking the small capacitor contribution at higher capacitance.
3. Individual instantaneous capacitor voltages were not visible, only an already-summed commutation-drive trace.
4. The slide did not overlay two *solved* capacitance values at the same electrical conditions.
5. At high firing angles and large capacitances, fundamental Q really is relatively insensitive, despite changes in capacitor voltage and overlap.

**No amplification or arbitrary scaling of model results is allowed.**

## Electrical model checks

The original physical differential equations remain unchanged. With phase current into the bridge and an externally imposed DC current:

- Series-capacitor state: `d(v_C,k)/d(theta) = X_C i_k`, with `X_C=1/(omega C Z_base)`.
- Series commutating reactor: `X_L=omega L_c/Z_base`.
- During a valid two-valve transfer: `2 X_L d(i_in)/d(theta) = e_in-e_out - (vC_in-vC_out) - R (i_in-i_out)`.
- The inverter and finite DC-reactor dynamics are not simulated here.
- Capacitor stored energy: `E_C(t) = 0.5 C sum(v_C,k(t)^2)`, after conversion from the explicitly documented 1 kV phase-peak voltage base.
- The reference solution, current and reference voltage traces use the same phase voltage, DC current, firing angle, leakage inductance, resistance and frequency. Only `C_series` differs.

At 60 Hz, with `L_c=0.24 mH`, `X_L≈0.0905 Ω`. For C=12 mF, `X_C≈0.221 Ω` (ratio `X_C/X_L≈2.44`); at C=100 mF, `X_C≈0.0265 Ω` (ratio ≈0.293). Therefore a smaller capacitance can produce a much more noticeable dynamic voltage contribution. This is a physical sensitivity observation, **not** a proposal to replace the capacitor by equivalent negative leakage reactance.

## Computed sensitivity — nominal case

Settings: `alpha=15°`, `I_dc=0.8 p.u.`, `V_phase,peak=1 p.u.`, `L_c=0.24 mH`, `R=0.012 Ω`, `f=60 Hz`, no shunt.

| C (mF) | X_C/X_L | Peak |v_C| (p.u.) | RMS v_C (p.u.) | Capacitor contribution at 0° (p.u.) | Net commutating drive at 0° (p.u.) | μ (°) | Q₁ (p.u.) | Mean capacitor energy (J) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | 3.665 | 0.2778 | 0.2069 | 0.5376 | 0.9955 | 7.533 | 0.28524 | 513.6 |
| 12 | 2.443 | 0.1852 | 0.1379 | 0.3561 | 0.8140 | 8.851 | 0.29577 | 342.2 |
| 26 | 1.128 | 0.0855 | 0.0636 | 0.1628 | 0.6207 | 10.785 | 0.31177 | 157.8 |
| 50 | 0.586 | 0.0444 | 0.0331 | 0.0842 | 0.5421 | 11.792 | 0.32039 | 82.0 |
| 73 | 0.402 | 0.0304 | 0.0226 | 0.0576 | 0.5154 | 12.170 | 0.32368 | 56.2 |
| 100 | 0.293 | 0.0222 | 0.0165 | 0.0420 | 0.4998 | 12.401 | 0.32570 | 41.0 |

From 12 to 100 mF, μ increases by ≈3.55°, and the peak capacitor voltage decreases by a factor of roughly 8.3. In this specific case Q₁ increases by ≈0.0299 p.u. The reference selector can show any of the six listed capacitances; the default is C_ref=100 mF.

## Computed sensitivity — higher firing angle

Settings: `alpha=60°`, `I_dc=0.75 p.u.`, `V_phase,peak=0.85 p.u.`, `L_c=0.32 mH`, `R=0.012 Ω`, `f=60 Hz`.

| C (mF) | Peak |v_C| (p.u.) | Capacitor contribution at 0° (p.u.) | Net drive at 0° (p.u.) | μ (°) | Q₁ (p.u.) |
|---:|---:|---:|---:|---:|---:|
| 8 | 0.2604 | 0.5084 | 1.7924 | 5.690 | 0.62528 |
| 12 | 0.1736 | 0.3381 | 1.6221 | 6.269 | 0.62686 |
| 26 | 0.0801 | 0.1555 | 1.4395 | 7.033 | 0.62892 |
| 50 | 0.0417 | 0.0807 | 1.3647 | 7.402 | 0.62991 |
| 73 | 0.0287 | 0.0551 | 1.3391 | 7.537 | 0.63027 |
| 100 | 0.0209 | 0.0403 | 1.3243 | 7.618 | 0.63048 |

This explains the user's original observation: changing C from **73 to 100 mF** changes Q₁ by only **≈0.00021 p.u.**, yet the physical capacitor contribution to the commutation drive changes from ≈0.0551 to ≈0.0403 p.u., and μ changes by ≈0.081°. The small reactive-power change is real for this operating point, not a display failure.

## Computed sensitivity — higher DC current

Settings: `alpha=30°`, `I_dc=1 p.u.`, `V_phase,peak=1 p.u.`, `L_c=0.32 mH`, `R=0.012 Ω`, `f=60 Hz`.

| C (mF) | Peak |v_C| (p.u.) | Capacitor contribution at 0° (p.u.) | μ (°) | Q₁ (p.u.) |
|---:|---:|---:|---:|---:|
| 8 | 0.3472 | 0.6698 | 8.374 | 0.62028 |
| 12 | 0.2315 | 0.4440 | 9.611 | 0.63055 |
| 26 | 0.1068 | 0.2032 | 11.368 | 0.64526 |
| 50 | 0.0556 | 0.1052 | 12.264 | 0.65283 |
| 73 | 0.0381 | 0.0719 | 12.599 | 0.65566 |
| 100 | 0.0278 | 0.0525 | 12.802 | 0.65739 |

These selected operating points show one direction of the C response; the teaching app must **not assume monotonicity in every feasible condition**.

## Implemented teaching improvements

- The first voltage subpanel exposes each *instantaneous* `v_C,a`, `v_C,b`, and `v_C,c` over one commutation interval.
- The second voltage subpanel exposes source drive, capacitor assistance, physically computed total drive (including series resistance), and the total drive for the separately solved reference capacitance.
- The third panel shows outgoing/incoming SCR currents, imposed `I_dc`, and the incoming SCR current from the reference capacitance.
- FOCUS uses a **fixed 0°–30°** commutation window and purpose-specific vertical limits. FULL uses a **fixed 0°–60°** window; neither changes automatically when sliders move.
- A reference capacitor selector offers 8/12/26/50/73/100 mF under the same electrical conditions.
- A collapsible sensitivity table includes `X_C/X_L`, capacitor peak and RMS voltage, stored energy, net commutating drive, μ and Q₁.
- Numerical readouts report instantaneous capacitor voltages, capacitive contribution and net drive at the angular cursor, as well as the actual difference in μ and Q₁ relative to the reference.
- The validated current range has been widened from 12–100 mF to **8–100 mF**. A 432-combination parameter sweep with C=8/12/26/100 mF and alpha/I_dc/L_c/V_phase extrema produced valid switching solutions; this is a model-validity check, not equipment sizing guidance.

## Independent numerical verification

The repository's independent SciPy solver uses adaptive `solve_ivp`, event-triggered SCR transfer and periodic capacitor shooting instead of the JavaScript RK4/event implementation. In addition to the existing comparisons of fundamental P/Q and μ, it now checks capacitor-voltage peak, RMS, energy and the instantaneous capacitor contribution for multiple capacitances at three operating points. Tolerances and model assumptions are stated explicitly in the regression.

The GitHub Actions result—not this report—is the definitive record of test execution.

## Limitations

This model represents a six-pulse rectifier with externally imposed DC current and a stiff AC voltage source. It does not include 12-pulse transformer groups, finite network/grid strength, DC current dynamics, inverter CCC recovery, capacitor protection or harmonic-filter resonance. Capacitor RMS/energy values are based on the illustrative 1 kV / 1 kA unit system, not a real HVDC station's ratings.

**Never interpret a change in an educational normalized C value as a direct recommendation for a commercial HVDC equipment rating.**
