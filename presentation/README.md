# HVDC LCC interactive lecture — R, RL, commutation, and complete link

The offline, standalone HTML contains **61 slides**: seven introductory R/RL slides followed by the original 48 LCC conduction/commutation states and chapter slides. It retains all original rectifier, inverter and HVDC features.

## New instructional progression

1. RECTIFIER — Normal conduction with R load.
2. Ideal firing delay α = 0°, 30°, 75°, 90°.
3. Discontinuous R-load current and all-SCRs-OFF intervals.
4. Comparison of R and RL under the same AC source and firing delay.
5. RECTIFIER — Normal conduction with RL load.
6. Existing twelve rectifier states, inverter states and complete HVDC link.

The introductory R and RL models use zero AC commutation inductance (μ = 0°). Load mode can be switched live; firing angle, resistance and DC inductance update the associated analytical waveforms, active SCR pair and circuit SVG. DC inductor and AC-side commutation inductance are treated separately.

## Build and test

From the repository root:

```bash
python -m pip install -r requirements-waveforms.txt
python rectifier_loads.py
python presentation/build_presentation.py --project . --output dist/lcc_hvdc_interactive.html
python -m pytest -q tests presentation/tests
```

Open `dist/lcc_hvdc_interactive.html` in Chrome, Edge or Firefox. No network or server is required. Keyboard arrows navigate slides; use O for the state overview and P for animation.

## PowerPoint

The PowerPoint is a **63-slide, clickable snapshot edition** (61 HTML slides + state overview + help). It preserves the circuit and waveform appearance and offers clickable navigation; live analytical sliders, actual parameter recomputation and continuous animation are available in the companion HTML only.

Build it using `presentation/pptx/capture_html.py` and `presentation/pptx/make_presentation.js`, or download the HTML/PPTX together from the GitHub Actions build artifact. The slides are presented as high-quality screenshots with native PowerPoint hyperlink hotspots and notes; they are not fully editable vector shapes.

## Further information

See [the R versus RL teaching guide](../docs/RECTIFIER_R_RL_TEACHING.md) and the existing LCC guides. No electromagnetic transient simulation is performed.
