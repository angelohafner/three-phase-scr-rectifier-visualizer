# HVDC LCC Interactive Lecture — HTML Only

The **offline, standalone 82-slide HTML presentation** teaches line-commutated
converters progressively: first a single-phase half-wave SCR with R/RL loads,
then the three-phase rectifier, the inverter and the complete two-station HVDC
link. No PowerPoint is generated or required.

## Chapter 00 — Thyristor Fundamentals

Eight interactive technical slides follow the Chapter 00 cover:

1. What Is a Thyristor?
2. Half-Wave Rectifier with R Load
3. R Load: Effect of Firing Angle
4. Half-Wave Rectifier with RL Load
5. **Why Does the SCR Remain ON After 180°?**
6. Natural Current Extinction
7. R versus RL: Same Source, Different Current
8. From Natural Extinction to Line Commutation

Move the angular slider continuously while watching the SCR and its waveforms.
The **180° source-voltage reversal marker remains fixed**. The extinction
marker **β moves dynamically** as the firing angle, resistance and inductance
are changed, and the region between the markers shows negative source voltage
alongside positive SCR current. The analytical RL current is solved rather
than shifted manually. The native slider DOM is preserved during dragging.

The new section uses physical V, A, Ω, mH and J units with mathematical italic
variables and upright digits/units. Its SVG circuit uses the project's
Schemdraw SCR vector primitives and an American zigzag resistor.

## Retained chapters

- **01 Rectifier** — six-pulse bridge, R/RL/LE/RLE DC loads, twelve
  conducting/overlap states and SCR anode-cathode voltages.
- **02 Inverter** — natural commutation, extinction-angle margin, valve voltages.
- **03 Complete HVDC link** — 24 joint converter states and metallic return.

The total includes **48 reference LCC states**. Controls are interactive and
analytical rather than an EMT simulation. Figures are bundled within the HTML.

## Build and validate

```bash
python -m pip install -r requirements-waveforms.txt
python halfwave_figures.py --output-dir output_lcc/fundamentals
python presentation/build_presentation.py --project . --output dist/lcc_hvdc_interactive.html
python -m pytest -q tests presentation/tests
python presentation/tests/browser_fundamentals.py
```

Open the resulting HTML directly in Chrome/Edge/Firefox with no internet.
Keyboard: Left/Right for slides, O for the overview, F for fullscreen,
P for animation. All sliders support continuous drag on supporting devices.

See [Half-wave technical notes](../docs/HALFWAVE_FUNDAMENTALS.md).
No PPTX is part of this release.

## New: Current-source LCC teaching section

The presentation now includes **nine additional slides** on the DC current-source representation of LCC converters, with a dedicated three-panel **Commutation with Constant DC Current** slide and continuously draggable 0–360° cursor. The two transfer-current waveforms and relevant phase voltages are synchronized with a graph-validated circuit. Select manually imposed or physically calculated overlap; invalid commutation conditions are reported, not fabricated.

The comparison covers RLE load response, ideal DC current constraints and an averaged, bounded PI current controller. The inverter comparison converts the local inverter DC voltage drop to a common signed pole-voltage convention before calculating power. Current-source figures are under `output_lcc/current_source/`. See [Current-source technical guide](../docs/CURRENT_SOURCE_TEACHING.md).

Regenerate all new SVG/PNG figures with `python current_source_figures.py`; build the offline lecture with `python presentation/build_presentation.py --project . --output dist/lcc_hvdc_interactive.html`. Only HTML is generated for the presentation—no PPTX is generated.


## Teaching-control audit (2026-10-28)

The presentation was audited across **82 slides**. See [slide-by-slide report](../docs/SLIDE_PHYSICS_AUDIT.md). In the two principal commutation lessons, DC current and rectifier delay remain fixed and overlap is computed from AC-side commutation inductance. Inverter-side waveforms now follow the inverter station, and inapplicable controls are suppressed. The 6-pulse reference-state slides retain an explicitly assumed overlap model; they are not an EMT simulation.

## Technical audit revision — consistent DC polarity and mobile readability

**Signed DC reference:** pole current is positive from the rectifier toward the inverter.
Use this same current-direction reference at both converter stations.
The rectifier voltage/power is positive when the rectifier delivers DC power;
the inverter voltage/power is negative when the inverter absorbs DC-link power
and transfers it to its AC system. These signed values are converter contributions,
not the positive local magnitude of the voltage across the inverter terminals.

On narrow screens, the state viewer offers independent **Circuit/Waveforms**
buttons. The waveform view shows one selected panel at a time at full available
height. Current-source slides offer the same mobile focus choice between the
circuit and the two chart panels. The existing angular slider remains mounted
through changes in state. Long technical fact labels wrap inside their cards.

The HTML build emits a matching `lcc_hvdc_interactive.build.json` containing
the source Git blob fingerprints, source commit when available and HTML SHA-256.
The GitHub Actions downloadable artifact includes both HTML and the manifest.
See `docs/SECOND_AUDIT_CORRECTIONS.md` for the verification record.
