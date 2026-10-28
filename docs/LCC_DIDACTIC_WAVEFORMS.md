# Conceptual waveform atlas for six-pulse LCC and HVDC

This extension produces **48 synchronized waveform figures** and **48 editable circuit+waveform sheets**, split into the existing three stages:

- `output_lcc/rectifier/waveforms/` and `output_lcc/rectifier/sheets/`: 12 rectifier states.
- `output_lcc/inverter/waveforms/` and `output_lcc/inverter/sheets/`: 12 inverter states.
- `output_hvdc/waveforms/` and `output_hvdc/sheets/`: 24 complete-link joint states.

The source circuits remain unchanged except for a correction to the transformer secondary neutral connection drawing in `hvdc_link_renderer.py`. A previous argument error had created invalid SVG line coordinates and long diagonal artifacts. The correction does not change electrical connectivity or commutation logic.

## Run

On Windows, run `gerar_formas_onda_lcc.bat`. Or:

```bash
python -m pip install -r requirements-waveforms.txt
python generate_lcc_waveforms.py --config config_waveforms.json --side all
python -m pytest -q tests
```

For one state (e.g. state 2 of the rectifier):

```bash
python generate_lcc_waveforms.py --side rectifier --state 2
```

For only the full link with a restricted set of signals:

```bash
python generate_lcc_waveforms.py --side hvdc --signals phase,scr,dc,idc
```

To avoid unnecessary regeneration for unchanged parameters, pass `--skip-existing`. Do not use this switch after changing configuration values, since it intentionally reuses existing files.

## Physical conventions and scope

1. Positive-sequence sinusoidal phase voltages of unit peak by default. The AC source phases are parameterized to place a rectifier firing event **after** the natural voltage crossover by the firing delay `alpha_r`, and an inverter firing event **before** the relevant reverse-polarity voltage crossover by the advance `beta_i = 180 deg - alpha_i`.
2. `I_dc` is a constant smoothed current. The linear commutation fraction is `s=(theta-theta_fire)/mu` from zero to one. During overlap, `i_out=I_dc(1-s)` and `i_in=I_dc*s`. Each SCR current remains nonnegative, and the upper and lower three-valve current sums each equal `I_dc`.
3. The DC waveform uses the currently selected **line-to-line** phase source voltage in normal conduction. During overlap, the arithmetic mean of the outgoing and incoming line-to-line voltages is used as a **qualitative equal-reactance approximation**. This is not obtained from a time-domain circuit solution, and cannot be used to infer a physical commutation notch's numerical amplitude.
4. The inverter's `v_dc` chart is a **positive pole-to-return potential difference in the local DC-side convention**. Its value is opposite to the negative voltage used in a signed rectifier-oriented converter-voltage convention. The inverter grid-to-converter AC currents are negative during delivery to the AC grid. Actual converter control and commutation reactance can modify values.
5. `gamma_i = 180 deg - alpha_i - mu_i`, with a configurable minimum. All angular ranges and highlighted valve groups are inherited directly from `CommutationSequence` and `CombinedSchedule`.
6. The inter-station `ac_phase_offset` in the pre-existing code is an illustrative relative shift between **valve-sequence timelines**, not a calculated phase difference between asynchronous AC grids, PLLs, or transformer vector groups.
7. The same illustrative `I_dc` is used at both stations; the generator **does not** solve AC/DC power flow, current-control dynamics, DC voltage balance, line losses or commutation-failure dynamics. Consequently, differences between the two station-voltage traces are **not** a solved line voltage drop.
8. The tool is a *conceptual waveform illustrator*, not PSCAD or an EMT replacement. Discrepancies between current sharing and simple voltage averaging are acknowledged independent teaching approximations.

## Diagram synchronization

Each chart displays one electrical cycle on a fixed `0°..360°` axis. The red shading shows exactly the diagram's state window, while the conducting SCRs' current traces are highlighted in red. For two-station HVDC, both converters are plotted on a common global angle axis. The joint-state window corresponds exactly to the pair of valve states in the existing source diagram.

All SVG waveform elements, axes, traces and text are vector objects. The combined SVG sheets contain the original circuit SVG and the Matplotlib SVG as separately editable nested SVGs; PNG previews are generated separately for presentations.

## Scientific typography

Mathematical symbols are typeset with STIX math glyphs. Scalar variables, including Greek letters, are italic; descriptive subscripts and physical units are upright; matrix and vector identifiers, when added, should be upright bold. Python code comments/docstrings and graphic labels are English.

## Validation

The test suite contains the original 73 tests plus additional waveform and drawing integrity tests covering all 48 waveform-to-diagram states, KCL/current transfer, power-sign conventions, XML editability and the neutral-wire drawing fix. Run `python -m pytest -q tests`.
