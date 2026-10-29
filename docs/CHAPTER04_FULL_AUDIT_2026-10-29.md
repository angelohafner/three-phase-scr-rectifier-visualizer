# Chapter 04 — Comprehensive engineering audit

**Date:** 29 October 2026
**Scope:** The 15 interactive Chapter 04 lessons (slides 82–96), within the existing 97-slide standalone presentation.
**Model:** Six-pulse switched-rectifier LCC/CCC with imposed DC current, AC-side inductance and resistance, and dynamically solved series capacitor voltages.

## Issues identified and corrected

| Severity | Issue | Resolution |
|---|---|---|
| **High** | Native Schemdraw capacitor symbols lacked conductor leads, creating visually open circuits for both series and shunt components. | Construct actual conductor connections from each native capacitor plate contact to both electrical terminals. A regression now checks each SVG lead endpoint, not only symbol presence. |
| **Medium** | Commutation completion was assigned to the next 0.2° sample; the calculated overlap was systematically biased upward. | Resolve the SCR transfer event inside each integration step by bisection and integrate the remaining fraction using the new conducting pair. |
| **Medium** | Nominal shunt Q was included in the grid balance in slides without a connected shunt capacitor. | Apply Qshunt only to the two lessons whose circuit actually contains the shunt capacitor bank; disable unrelated shunt controls. |
| **Medium** | The plotted net commutating voltage omitted the R(i_in - i_out) term used by the physical differential equation. | Include the source, capacitor and resistor contributions consistently and identify the red trace as net drive including R. |
| **Medium** | The LCC–CCC comparison did not show both numerical Q and μ results. | Display matching LCC/CCC μ, fundamental Q, signed initial commutating drive, and their differences. Keep the CCC/LCC comparison fixed to two distinct solved topologies. |
| Low | LCC labels referred to an active series capacitor even with that capacitor bypassed. | Explicitly label the LCC capacitor as bypassed. |
| Low | The inverter-related lesson could suggest a solved inverter switching model. | State that only the rectifier waveforms are numerically solved, while inverter discussion is qualitative. |

## Independent benchmark — primary operating point

An independent SciPy adaptive solve_ivp and event-based shooting model was used, separate from the JavaScript RK4 algorithm.

Matched operating parameters: alpha=15°; I_dc=0.8 p.u.; V_phase,peak=1.0 p.u.; L_comm=0.24 mH per phase; R_phase=0.012 Ω; f=60 Hz; no shunt. The LCC capacitor is bypassed, whereas the CCC has C_series=26 mF per phase.

| Quantity (independent numerical result) | LCC | CCC | CCC − LCC |
|---|---:|---:|---:|
| Mean overlap μ | 13.059308° | 10.785080° | **−2.274228°** |
| Fundamental converter Q | 0.3315451 p.u. | 0.3117652 p.u. | **−0.0197799 p.u.** |
| Positive initial net commutating drive | 0.4578877 p.u. | 0.6206680 p.u. | **+0.1627803 p.u.** |
| Fundamental converter P | 0.8154466 p.u. | 0.8238246 p.u. | +0.0083780 p.u. |

In this modeled operating point, the series capacitors increase initial signed commutating drive by approximately 35.6%, decrease mean overlap by 2.27°, and reduce fundamental converter Q by approximately 5.97%.

**These effects are not guaranteed to be monotonic over all capacitances or operating conditions.** The initial capacitor-voltage state, current transfer and imposed AC waveform determine the result.

## Independent benchmark — second operating point

Matched parameters: alpha=30°; I_dc=1.0 p.u.; V_phase,peak=1.0 p.u.; L_comm=0.32 mH; R_phase=0.012 Ω; f=60 Hz; no shunt.

| Quantity | LCC, bypass C | CCC, C=26 mF |
|---|---:|---:|
| Mean overlap μ | 13.380882° | 11.368160° |
| Fundamental converter Q | 0.6623245 p.u. | 0.6452574 p.u. |
| Positive initial net commutating drive | 0.8780254 p.u. | 1.0812247 p.u. |

The reproducible independent test is at presentation/tests/chapter04_independent_reference.py. It numerically compares six matched cases against the actual JavaScript solver. The model's original 144-scenario operating-point sweep remains intact.

## Slide-by-slide audit coverage

| Slide | Topic | Special verification |
|---|---|---|
| 82 | Origins of reactive consumption | Fundamental Q, no disconnected shunt compensation |
| 83 | Firing angle | AC current phasor and switching dependency |
| 84 | Commutation overlap | Physical calculated μ and inductance influence |
| 85 | Voltage/current phasors | Fundamental Fourier P/Q, displacement factor |
| 86 | Rectifier vs inverter | Qualitative inverter claims accurately labeled |
| 87 | Shunt reactive compensation | Physically connected AC-bus bank and Q balance |
| 88 | AC filters | Fundamental compensation, no invented harmonic-filter EMT |
| 89 | Series C topology | Authentic Schemdraw contacts and electrical leads |
| 90 | Dynamic capacitor states | Capacitor voltage continuity and periodic solution |
| **91** | **How Series Capacitors Assist Thyristor Commutation** | **Net drive and currents derive from one ODE solution** |
| 92 | SCR current transfer | Event-resolved outgoing/incoming currents |
| 93 | CCC six-pulse converter | Six valves, six events and capacitor states |
| **94** | **LCC vs CCC, same conditions** | **Paired μ/Q/net-drive numerical metrics** |
| 95 | Grid voltage sensitivity | Fixed bus-source model, finite-grid physics not claimed |
| 96 | Operating limits | Invalid commutation and periodic-solution failures |

## Verification and acceptance

The intended CI verification runs:
1. Four native Schemdraw SVG topology cases and actual capacitor-lead endpoint geometry.
2. Full existing Python test suite, plus 144 JavaScript CCC parameter scenarios.
3. Independent adaptive SciPy event/shooting benchmark and fundamental Fourier P/Q comparison.
4. Entire 97-slide offline Chromium navigation and 15 Chapter 04 lessons, including mobile layout.
5. Fixed FOCUS/FULL plot domains, live slider behavior, and native-circuit zoom.

Check the linked GitHub Actions run for definitive test outcomes; passing results must not be inferred solely from this report.

## Remaining engineering limitations

This project models a **six-pulse rectifier with ideal externally imposed DC current**. It is not a full-scale EMT or commercial 12-pulse HVDC converter design. A realistic installation also needs magnetic transformer modeling, Y/Y and Y/Δ converter groups, finite smoothing-reactor behavior, grid Thevenin strength, harmonic resonance and filters, protection/bypass circuits, and full inverter/commutation-failure dynamics. Those systems have NOT been validated by these tests.

The reported Q, S, and power factor refer to fundamental-frequency displacement, not total harmonic apparent power or a complete loss/energy audit of an AC network. Fixed-source shunt Q assumptions are deliberate; the new capacitor series dynamics are solved explicitly.

The numerical results demonstrate model consistency, not physical hardware certification.
