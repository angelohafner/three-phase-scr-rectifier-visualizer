# LCC HVDC Interactive Presentation — Slide-by-Slide Physics Audit

Revision: 2026-10-28. Deliverable: 82-slide offline HTML presentation.

## Scope and conventions

All 82 slides were opened in offline Chromium. This is a conceptual teaching model, not an EMT or validation-grade transient solver. Source voltages remain sinusoidal on the AC side. The ideal DC current source is a simplifying current constraint, valid only when an SCR conduction path exists. Calculated commutation assumes two identical AC commutation reactors and a balanced three-phase source. The inverter extinguishing margin is based on the existing simplified angle convention.

The model uses illustrative bases **1 kV phase peak, 1 kA DC** (therefore 1 Ω base impedance) when relating current in p.u. to commutation inductance in mH.

The angular reference is synchronized to firing. Changing the firing delay rotates the AC source phase relative to that reference; the reference-state windows are not absolute grid phase angles. The stationary state slides retain user-assumed overlap and linear current transfer as an explicit pedagogical option.

## Issues and corrective actions

| ID | Slides | Finding | Correction | Verification |
|---|---|---|---|---|
| CS-01 | 38 and 39 | The overlap angle could be imposed independently of AC commutation inductance; changing Lc had no causal effect in manual mode. | The slide now fixes Idc=1.0 p.u., alpha_r=15°, and AC voltage base, enables only Lc and calculates mu_r from the two-phase commutation-voltage integral. | Monotonic mu(Lc), Python–JavaScript parity, browser drag. |
| CS-02 | 35–43 | Current-source-specific controls were shown even when they did not affect the selected lesson. | Declarative per-lesson control policy hides unused sliders, preserves relevant inputs, and displays computed mu as a result. | All nine source slides exercised in Chromium. |
| CS-03 | 42 | The inverter waveform could display rectifier SCR currents while the inverter circuit was selected. | Inverter mode uses inverter reference phase voltages, SCR current map, reverse AC current convention, and a common signed DC-voltage reference. | Browser station-selection and numerical reference parity. |
| CS-04 | 42 | The alpha slider continued editing rectifier delay after the inverter was selected. | The same slider is relabeled alpha_i and modifies alphaI for the inverter; valid inverter limits are enforced. | Browser test changes 145° to 140° and confirms state. |
| CS-05 | 41 | The averaged current-controller chart is plotted versus time but allowed an unrelated electrical-angle sweep. | The electrical-angle slider, state controls, and autoplay are disabled in the time-domain controller lesson. | Browser checks and source review. |
| CS-06 | 35, 36, 37, 40 | Introductory conduction/reference slides exposed an overlap control although the idealized examples do not model it. | Ideal source examples explicitly use mu=0; the RLE/source comparison retains load R, L, E and current-reference controls only where needed. | Per-lesson policy tests. |
| CS-07 | 23–34, 45–56 | Six-pulse slides were described as normal RL-load conduction even though the waveform engine imposes DC current. | Titles state approximate constant DC current. Manually selected overlap is labeled assumed, not Lc-derived. | All 24 per-station states rendered. |
| CS-08 | 58–81 | Users could mistake the timing intervals on the joint HVDC plots for physically computed overlap durations. | The assumptions are documented as imposed angular windows; phase timing remains relative to the firing-synchronized reference. | 24 joint diagrams and synchronized plots inspected in Chromium. |
| CS-09 | 3–22 | Global parameter settings offered controls from unrelated circuits. | Settings show the active physical model parameters and hide unrelated parameters; inductor and opposing-voltage controls are disabled where absent. | R/RL/LE/RLE and half-wave browser regression. |
| CS-10 | 38–43 | Reference-base conventions for mH and per-unit source quantities were implicit. | Python and JavaScript state explicit illustrative bases of 1 kV phase peak and 1 kA DC (Zbase=1 ohm) for the overlap relation. | Fixed-base Python–JavaScript parity and numeric mu sweep. |
| CS-11 | 38–43 | Operating interval shading could fail across the 360° boundary for the inverter with 30° reference offset. | Shading uses a set of valid wrapped angular windows instead of an unbounded rectangle. | Direct browser station toggle and SVG/Canvas inspection. |
| CS-12 | 1–82 | Lessons relied on slide-specific assumptions without an explicit control/validation inventory. | Added a slide-by-slide index recording model, enabled controls, graph, and assumptions; added browser-based 82-slide audit. | Saved slide_inventory.json and screenshots. |

## Individual slide inventory

Status descriptions: `reviewed` means accessible and rendered without missing circuit/waveform content; chapter/cover/end slides have no electrical controls. For state slides, `µ assumed` means overlap does not come from AC inductance.

| Slide | Chapter | Teaching subject | Interactive input(s) | Model status |
|---:|---|---|---|---|
| 1 | intro | HVDC LCCCurrent paths & commutation | none | navigation / chapter |
| 2 | intro | One conceptat a time. | none | navigation / chapter |
| 3 | fundamentals | How does an SCR turn off? | none | navigation / chapter |
| 4 | fundamentals | What Is a Thyristor? | hAlpha, hR, hV, fundθ | R/RL analytical extinction model |
| 5 | fundamentals | Half-Wave Rectifier with R Load | hAlpha, hR, hV, fundθ | R/RL analytical extinction model |
| 6 | fundamentals | R Load · Effect of Firing Angle | hAlpha, hR, hV, fundθ | R/RL analytical extinction model |
| 7 | fundamentals | Half-Wave Rectifier with RL Load | hAlpha, hR, hL, hV, fundθ | R/RL analytical extinction model |
| 8 | fundamentals | Why Does the SCR Remain ON After 180°? | hAlpha, hR, hL, hV, fundθ | R/RL analytical extinction model |
| 9 | fundamentals | Natural Current Extinction | hAlpha, hR, hL, hV, fundθ | R/RL analytical extinction model |
| 10 | fundamentals | R versus RL · Same Source, Different Current | hAlpha, hR, hL, hV, fundθ | R/RL analytical extinction model |
| 11 | fundamentals | Natural Extinction versus Line Commutation | hAlpha, hR, hL, hV, fundθ | R/RL analytical extinction model |
| 12 | rectifier | AC to DC | none | navigation / chapter |
| 13 | rectifier | RECTIFIER · R load and DC current dynamics | θ | R/RL/LE/RLE analytical model |
| 14 | rectifier | RECTIFIER · R load · firing angle 0° | θ | R/RL/LE/RLE analytical model |
| 15 | rectifier | RECTIFIER · R load · firing angle 30° | θ | R/RL/LE/RLE analytical model |
| 16 | rectifier | RECTIFIER · R load · firing angle 75° | θ | R/RL/LE/RLE analytical model |
| 17 | rectifier | RECTIFIER · R load · firing angle 90° | θ | R/RL/LE/RLE analytical model |
| 18 | rectifier | RECTIFIER · Comparing R and RL loads | θ | R/RL/LE/RLE analytical model |
| 19 | rectifier | RECTIFIER · RL load and DC current dynamics | θ | R/RL/LE/RLE analytical model |
| 20 | rectifier | RECTIFIER · LE load and DC current dynamics | θ | R/RL/LE/RLE analytical model |
| 21 | rectifier | RECTIFIER · RLE load and DC current dynamics | θ | R/RL/LE/RLE analytical model |
| 22 | rectifier | RECTIFIER · R / RL / LE / RLE comparison | θ | R/RL/LE/RLE analytical model |
| 23 | rectifier | RECTIFIER · Normal conduction with approximately constant DC current | θ | µ assumed / SVG reference, constant Idc |
| 24 | rectifier | RECTIFIER · Assumed commutation overlap | θ | µ assumed / SVG reference, constant Idc |
| 25 | rectifier | RECTIFIER · Normal conduction with approximately constant DC current | θ | µ assumed / SVG reference, constant Idc |
| 26 | rectifier | RECTIFIER · Assumed commutation overlap | θ | µ assumed / SVG reference, constant Idc |
| 27 | rectifier | RECTIFIER · Normal conduction with approximately constant DC current | θ | µ assumed / SVG reference, constant Idc |
| 28 | rectifier | RECTIFIER · Assumed commutation overlap | θ | µ assumed / SVG reference, constant Idc |
| 29 | rectifier | RECTIFIER · Normal conduction with approximately constant DC current | θ | µ assumed / SVG reference, constant Idc |
| 30 | rectifier | RECTIFIER · Assumed commutation overlap | θ | µ assumed / SVG reference, constant Idc |
| 31 | rectifier | RECTIFIER · Normal conduction with approximately constant DC current | θ | µ assumed / SVG reference, constant Idc |
| 32 | rectifier | RECTIFIER · Assumed commutation overlap | θ | µ assumed / SVG reference, constant Idc |
| 33 | rectifier | RECTIFIER · Normal conduction with approximately constant DC current | θ | µ assumed / SVG reference, constant Idc |
| 34 | rectifier | RECTIFIER · Assumed commutation overlap | θ | µ assumed / SVG reference, constant Idc |
| 35 | rectifier | Voltage-Driven versus Current-Driven DC Circuits | idc, alphaR, loadR, loadL, loadE, angle | µ ideal = 0 |
| 36 | rectifier | LCC Rectifier with Constant DC Current | idc, alphaR, angle | µ ideal = 0 |
| 37 | rectifier | Thyristor Currents with Constant DC Current | alphaR, angle | µ ideal = 0 |
| 38 | rectifier | Commutation with Constant DC Current | csLc, angle | µ calculated from Lc |
| 39 | rectifier | Effect of Commutation Inductance on Overlap | csLc, angle | µ calculated from Lc |
| 40 | rectifier | RLE versus Constant Current Source | idc, alphaR, loadR, loadL, loadE, angle | µ ideal = 0 |
| 41 | rectifier | Current-Controlled LCC Rectifier | idc, loadR, loadL, loadE | time-domain controller |
| 42 | rectifier | Current Direction in Rectifier and Inverter Operation | alphaR, angle | µ assumed, direction consistent |
| 43 | rectifier | From Current Source to the Complete HVDC Link | angle | µ assumed, direction consistent |
| 44 | inverter | DC to AC | none | navigation / chapter |
| 45 | inverter | INVERTER · Normal conduction with approximately constant DC current | θ | µ assumed / SVG reference, constant Idc |
| 46 | inverter | INVERTER · Assumed commutation overlap | θ | µ assumed / SVG reference, constant Idc |
| 47 | inverter | INVERTER · Normal conduction with approximately constant DC current | θ | µ assumed / SVG reference, constant Idc |
| 48 | inverter | INVERTER · Assumed commutation overlap | θ | µ assumed / SVG reference, constant Idc |
| 49 | inverter | INVERTER · Normal conduction with approximately constant DC current | θ | µ assumed / SVG reference, constant Idc |
| 50 | inverter | INVERTER · Assumed commutation overlap | θ | µ assumed / SVG reference, constant Idc |
| 51 | inverter | INVERTER · Normal conduction with approximately constant DC current | θ | µ assumed / SVG reference, constant Idc |
| 52 | inverter | INVERTER · Assumed commutation overlap | θ | µ assumed / SVG reference, constant Idc |
| 53 | inverter | INVERTER · Normal conduction with approximately constant DC current | θ | µ assumed / SVG reference, constant Idc |
| 54 | inverter | INVERTER · Assumed commutation overlap | θ | µ assumed / SVG reference, constant Idc |
| 55 | inverter | INVERTER · Normal conduction with approximately constant DC current | θ | µ assumed / SVG reference, constant Idc |
| 56 | inverter | INVERTER · Assumed commutation overlap | θ | µ assumed / SVG reference, constant Idc |
| 57 | hvdc | Connect the two stations | none | navigation / chapter |
| 58 | hvdc | HVDC LINK · Rectifier overlap | θ | µ assumed / SVG reference, constant Idc |
| 59 | hvdc | HVDC LINK · Normal at both stations | θ | µ assumed / SVG reference, constant Idc |
| 60 | hvdc | HVDC LINK · Inverter overlap | θ | µ assumed / SVG reference, constant Idc |
| 61 | hvdc | HVDC LINK · Normal at both stations | θ | µ assumed / SVG reference, constant Idc |
| 62 | hvdc | HVDC LINK · Rectifier overlap | θ | µ assumed / SVG reference, constant Idc |
| 63 | hvdc | HVDC LINK · Normal at both stations | θ | µ assumed / SVG reference, constant Idc |
| 64 | hvdc | HVDC LINK · Inverter overlap | θ | µ assumed / SVG reference, constant Idc |
| 65 | hvdc | HVDC LINK · Normal at both stations | θ | µ assumed / SVG reference, constant Idc |
| 66 | hvdc | HVDC LINK · Rectifier overlap | θ | µ assumed / SVG reference, constant Idc |
| 67 | hvdc | HVDC LINK · Normal at both stations | θ | µ assumed / SVG reference, constant Idc |
| 68 | hvdc | HVDC LINK · Inverter overlap | θ | µ assumed / SVG reference, constant Idc |
| 69 | hvdc | HVDC LINK · Normal at both stations | θ | µ assumed / SVG reference, constant Idc |
| 70 | hvdc | HVDC LINK · Rectifier overlap | θ | µ assumed / SVG reference, constant Idc |
| 71 | hvdc | HVDC LINK · Normal at both stations | θ | µ assumed / SVG reference, constant Idc |
| 72 | hvdc | HVDC LINK · Inverter overlap | θ | µ assumed / SVG reference, constant Idc |
| 73 | hvdc | HVDC LINK · Normal at both stations | θ | µ assumed / SVG reference, constant Idc |
| 74 | hvdc | HVDC LINK · Rectifier overlap | θ | µ assumed / SVG reference, constant Idc |
| 75 | hvdc | HVDC LINK · Normal at both stations | θ | µ assumed / SVG reference, constant Idc |
| 76 | hvdc | HVDC LINK · Inverter overlap | θ | µ assumed / SVG reference, constant Idc |
| 77 | hvdc | HVDC LINK · Normal at both stations | θ | µ assumed / SVG reference, constant Idc |
| 78 | hvdc | HVDC LINK · Rectifier overlap | θ | µ assumed / SVG reference, constant Idc |
| 79 | hvdc | HVDC LINK · Normal at both stations | θ | µ assumed / SVG reference, constant Idc |
| 80 | hvdc | HVDC LINK · Inverter overlap | θ | µ assumed / SVG reference, constant Idc |
| 81 | hvdc | HVDC LINK · Normal at both stations | θ | µ assumed / SVG reference, constant Idc |
| 82 | end | Explore further. | none | navigation / chapter |

## Regression evidence

- Python model and UI-related pytest checks, including checks for current conservation and µ increasing with AC inductance.
- Live Chromium validation of all 82 slides, plus pointer capture during drag across multiple commutation states.
- The current-controller slide disables the electrical-angle sweep because its charts use seconds on the time axis.
- Numerical current-source and inverter parity tests cross-check the JavaScript and Python/reference-model calculations.
- Screenshots of the key lessons were saved in the accompanying audit package.

## Explicit limitations / further work

- Manual µ settings in the existing reference-state chapter are identified as **assumed**. A full EMT-based commutation model with voltage harmonics, recovery dynamics and failures is not included.
- The inverter voltage reference and γ relation use a simplified convention. Do not interpret the plots as field-design limits.
- Current-source and RLE responses are distinct models; do not infer the current source describes DC-link transients.
- Manufacturer-specific corporate branding is not included; the document remains independent engineering teaching material.
