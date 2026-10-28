# Current-Source Representation of LCC Converters

## Teaching sequence

This HTML-only addition introduces **nine interactive slides** in the Rectifier chapter, after R/RL/LE/RLE and the original six-pulse states, and before the Inverter chapter:

1. Voltage-Driven versus Current-Driven DC Circuits
2. LCC Rectifier with Constant DC Current
3. Thyristor Currents with Constant DC Current
4. **Commutation with Constant DC Current** — circuit, outgoing/incoming currents and phase voltages side by side
5. Effect of DC Current on Commutation Overlap
6. RLE versus Constant Current Source
7. Current-Controlled LCC Rectifier
8. Current Direction in Rectifier and Inverter Operation
9. From Current Source to the Complete HVDC Link

The three panels on slide 4 are synchronized by a **single, continuously draggable electrical-angle slider**. The current-source panel uses the six-pulse SCR bridge with three voltage sources and AC commutation inductances; only its DC branch changes.

## Current source and commutation

The **ideal DC current source is a constraint**: its current is imposed only while a valid, controlled SCR conduction path exists. It has idealized unbounded voltage compliance and must not be interpreted as an independently operating converter without a conducting path. The rectifier DC branch shows a **current sink** in the positive DC-to-return direction; the inverter branch shows a DC current supply into the inverter equivalent. The common line-current sign is preserved.

For normal conduction, one upper and one lower SCR carry the same DC pole current `I_ref`; they change at 60° intervals and each valve conducts for 120° in ideal six-pulse operation.

During an upper- or lower-group commutation, the outgoing and incoming valves share the imposed current:

- `i_out + i_in = I_ref`
- `i_stationary = I_ref`
- Phase AC currents satisfy `i_a + i_b + i_c = 0`.

With manually imposed `mu`, the teaching transfer function is linear:

- `i_in = I_ref * delta / mu` for `0 <= delta <= mu`.

The **calculated overlap** alternative assumes two identical AC commutation inductances (`L_c` per phase), an ideal balanced three-phase source, a constant DC current, and no resistance in the commutation loop:

- `2 L_c * d(i_in)/dt = v_in - v_out`
- `I_ref = sqrt(3) V_phase,peak / (2 omega L_c) * [cos(alpha) - cos(alpha+mu)]`.

Within overlap, `i_in` follows the **normalized integral** of the commutating voltage rather than an arbitrary linear ramp. The model rejects parameters requiring `mu >= 60°`, or with no mathematically valid complete transfer, rather than silently inventing currents. The source-voltage peak and current use illustrative bases `V_base=1 V` and `I_base=1 A`, so numerical values are per-unit and the inductance value is given in mH at `60 Hz`.

The DC voltage during overlap is illustrated by the equal-reactance midpoint of the incoming/outgoing line voltages. This is not an EMT solution. The source voltage and phase-current reference follow the existing six-pulse teaching convention; `theta` is measured in the conduction-sector reference frame.

## RLE versus current source

The RLE load satisfies (within its valid conducting path):

`L_dc di_dc/dt + R_dc i_dc = v_dc - E`.

`i_dc` follows a dynamic, damped response; it is **not forced** to equal `I_ref`. The comparative graph uses the same selected rectifier firing angle for both the RLE and ideal-current-source branches, and explicitly shows the RLE mean current next to the fixed-source current. The values can differ. For a controlled RLE, a simple averaged PI algorithm adjusts the firing angle to track a step in current reference. It is an **averaged controller example**, not a transient simulation of gate pulses or AC-side commutation failure.

## Voltage, current and power conventions

Rectifier-orientated signed DC voltage is used for the new side-by-side comparison:

- Rectifier `P_dc,r = +V_dc,r * I_dc`.
- Inverter `P_dc,i = -V_dc,i(local pole drop) * I_dc`.

The original inverter station's local positive pole-to-return drop is converted to the common signed convention **before plotting the inverter DC voltage or calculating power**. In nominal operation, the rectifier's average signed power is positive and the inverter's average signed power is negative. The approximately unidirectional DC pole current is not reversed to change power direction.

## Schemdraw and editable vectors

`current_source_figures.py` reuses the graph-validated original bridge, including its actual `SCR`, `Inductor` and `SourceSin` geometries. The **DC current source** is constructed with `schemdraw.elements.SourceI` when the library is installed. `schemdraw_symbols.py` supplies a visibly marked reference primitive fallback for offline environments without Schemdraw. `data-symbol` and `data-symbol-source` attributes in the SVG document the source of each electrical component. Python regenerates SVG/PNG examples; HTML uses inline SVG to remain offline.

Native symbol regeneration: `python -m pip install 'schemdraw>=0.22,<0.24'`.

## Generate and validate

```bash
python current_source_figures.py
python presentation/build_presentation.py --project . --output dist/lcc_hvdc_interactive.html
python -m pytest -q tests presentation/tests
python presentation/tests/browser_current_source.py
```

The HTML output is self-contained and includes no external CDNs, fonts, scripts or remote image requests. Existing rectifier, inverter, half-wave fundamentals and full-link chapters remain intact. This training material has PTI-inspired independent styling but is **not an official Siemens publication**.
