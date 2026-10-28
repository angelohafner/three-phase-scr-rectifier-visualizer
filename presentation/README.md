# HVDC LCC Interactive Lecture — HTML Only

The **offline, standalone 73-slide HTML presentation** teaches line-commutated
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
