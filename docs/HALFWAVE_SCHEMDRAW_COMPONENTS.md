# Native Schemdraw symbols and inductance controls

The Python circuit renderer now instantiates standard Schemdraw elements
`schemdraw.elements.SCR`, `ResistorIEEE`, `Inductor`,
`SourceSin`, and `SourceV` when Schemdraw is installed.

The reusable `schemdraw_symbols.py` adapter renders those native element
segments as editable SVG groups, retaining the real electrical terminal
positions. Each component carries `data-symbol`, `data-terminal-start`,
`data-terminal-end` and `data-symbol-source` attributes.

For Python installations without Schemdraw, an explicitly labelled reference
geometry based on Schemdraw 0.23 permits offline preview generation. Reference
geometry is not a native-library instantiation. The GitHub Actions workflow
installs Schemdraw and generates native-element SVGs and the final offline HTML.

## Inductance controls

- **R:** Inductor slider disabled.
- **RL:** Inductor slider enabled.
- **LE:** Inductor slider enabled.
- **RLE:** Inductor slider enabled.
- **R-versus-RL and all-load comparisons:** Enabled because at least one
  displayed load contains a physical inductor.

The selected L value persists when switching modes. A disabled input cannot
modify the model. All sliders retain their DOM nodes and work with continuous
mouse dragging. When the half-wave RL model is active, L changes the current
waveform and the computed extinction angle beta.

## Generate locally

```bash
python -m pip install "schemdraw>=0.22,<0.24" -r requirements-waveforms.txt
python halfwave_figures.py --output-dir output_lcc/fundamentals
python lcc_converter.py --side both --alpha 145 --mu 15 --output-dir output_lcc
python hvdc_link.py --config config_hvdc.json --all --output-dir output_hvdc --png
python presentation/build_presentation.py --project . --output dist/lcc_hvdc_interactive.html
REQUIRE_NATIVE_SCHEMDRAW=1 python -m pytest -q tests presentation/tests
```

No PowerPoint output is generated.
