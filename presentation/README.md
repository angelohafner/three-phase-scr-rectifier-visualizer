# HVDC LCC — Interactive Lecture

This project includes an offline, self-contained HTML presentation for the three instructional stages of an LCC link: rectifier (12 reference states), inverter (12), and the complete HVDC circuit (24).

## Build

Run the generator from the repository root:

```bash
python presentation/build_presentation.py --project . --output dist/lcc_hvdc_interactive.html
```

Open `dist/lcc_hvdc_interactive.html` directly in a browser. It embeds the vector circuits, source waveforms, styles and JavaScript. No HTTP server or network is required.

**Outputs:** 54 slides, 48 waveform-reference states, 144 computed rectifier/inverter SCR-state combinations for the dynamically selected full-link circuit.

## Controls

Use Left/Right or Space to change slides; O for the 48-state overview; F for fullscreen; P to play/pause the angle sweep. The 0–360° slider selects the active state. Settings modify firing angles, overlap, voltage amplitude, DC current and animation speed. Switch between live plots and original reference SVGs; reference SVGs do not respond to updated settings.

The inverter extinction angle uses `gamma = 180 - alpha_i - mu_i` under the simplified angle convention, with `gamma >= 10` enforced.

## Models

The JavaScript source mirrors `lcc_waveform_model.py`: ideal SCRs, constant DC current, balanced sinusoidal sources, linear current transfer during commutation overlap, and an illustrative equal-reactance midpoint for overlap DC voltage.

**This is conceptual teaching software, not an EMT simulation.** No real commutation-failure prediction, DC load flow, transformer saturation, surge transient, or distributed DC-line physics is modeled. The relative 30-degree inter-station timing offset is illustrative and is not a calculated AC system phase shift.

## Source

- `src/waveforms.js`: 360° state schedules, SCR and voltage/current calculations.
- `src/charts.js`: interactive waveform plots.
- `src/presentation.js`: slide navigation, parameter controls, autoplay and responsive UI.
- `src/styles.css`: 16:9 visual design and responsive layouts.
- `src/template.html`: completely local HTML skeleton.
- `build_presentation.py`: source-SVG embedding and HTML build.

The standalone HTML is 17 MB because it contains all schematic and waveform vectors. A build artifact can be produced through GitHub Actions when the workflow is enabled.

## Validate

```bash
python -m pip install pytest
python -m pytest -q tests
python -m pytest -q presentation/tests
```

The conceptual browser waveforms have been compared numerically against the Python source at multiple electrical angles. The deck was exercised in Chromium with external HTTP(S) requests blocked. Browser automation in the authoring environment did not permit navigating to `file://` directly, but the final file contains no external fetches, scripts, fonts or image requests.
