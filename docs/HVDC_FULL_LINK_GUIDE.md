# Stage 3 — Complete six-pulse LCC HVDC link

The **complete-link module** connects two *separate* six-pulse Graetz bridges into
one continuous DC circuit. It is intended for teaching conduction paths before
building a detailed HVDC operating-point or EMT model.

![Normal state: continuous current path](../output_hvdc/hvdc_normal.png)

## Electrical scope and deliberate simplifications

- **Rectifier (R):** three-phase AC grid, isolated two-winding Y/Y converter
  transformer, three equivalent leakage/commutation inductors, six SCRs.
- **Positive DC conductor:** rectifier smoothing reactor `L_DR`, lumped DC line
  resistance `R_LINE` (ANSI zigzag), inverter smoothing reactor `L_DI`.
- **Inverter (I):** six SCRs, three equivalent leakage/commutation inductors,
  isolated two-winding Y/Y transformer, independent three-phase AC grid.
- **Metallic return:** a second, continuous DC conductor runs from the inverter
  negative bus back to the rectifier negative bus. No ground-return path is
  inferred, and there is **no neutral/earth current** in the red DC loop.
- **Conventional DC current:** positive pole flows **R → I**; metallic return
  flows **I → R**. Within the isolated secondary windings, the AC current
  completes the corresponding station's conducting phase loop.

**Important:** a modern 12-pulse LCC station generally has **two** six-pulse
bridges series-connected on the DC side with Y/Y and Y/Δ transformer windings
producing a 30° phase displacement. This lesson uses one six-pulse bridge per
station on purpose. The `ac_phase_offset` in this project refers to two
independent grid reference angles; it does **not** represent the 30° phase
shift of a twelve-pulse converter transformer.

The arrows in the inverter are those of the chosen schematic **bridge current
orientation**. The inverter drawing uses the opposite vertical SCR orientation
from the rectifier so that the positively defined link current enters its
upper DC terminal, passes through an inverter valve, and leaves through the
lower terminal. Each SCR remains strictly forward-conducting on the graph.
The phase-to-phase voltage phasor and firing reference must be chosen
consistently with this representation; the software does not calculate those
values or implement firing pulse synchronization.

## Model architecture

`hvdc_link_model.py` reuses `CommutationSequence` and `ConductionState` from
`rectifier_model.py`. It supplies:

- `LinkSettings`: control-angle configuration and input validation.
- `CombinedSchedule`: shared 360° reference, one relative phase offset and
  the complete list of joint conduction intervals.
- `HVDCLinkTopology`: directed graph of all **12 SCRs**, transformer
  secondaries, three-phase commutation inductances, smoothing reactors, line
  resistance and metallic return.
- `conduction_loop`: four forward SCR traversals, two valve-side secondary
  loops and one complete link traversal; all vertices and edges are checked.
- `highlight`: union of valid conductive circuits. In overlap this shows
  both possible paths; it does **not** imply equal currents or solve current
  sharing between outgoing and incoming SCRs.

`hvdc_link_renderer.py` draws the circuit with `rectifier_art` primitives,
including the true `schemdraw.elements.SCR` geometry when the optional
Schemdraw package is installed. Otherwise it draws the same stored primitives.
The transformer primary and secondary windings are **never electrically
connected** in the graph or the vector diagram. Mathematical labels are
editable SVG text with STIX Math-compatible families.

`hvdc_link.py` provides CLI/JSON input, batch export and a precise time chart.

## Typical commands

Generate 24 joint intervals for the default demonstration:

```bash
python hvdc_link.py --config config_hvdc.json --all --output-dir output_hvdc
```

Generate PNG previews too (optional `cairosvg` package):

```bash
python -m pip install cairosvg
python hvdc_link.py --all --png --output-dir output_hvdc
```

Show the complete current path at global angle 66°:

```bash
python hvdc_link.py --theta 66 --output-dir output_hvdc
```

Change the inverter extinguishing angle *instead of* setting its delay angle:

```bash
python hvdc_link.py --alpha-r 15 --gamma-i 20 --mu-r 12 --mu-i 15 --phase-offset 30
```

Illustrate **simultaneous commutations** at the two ends:

```bash
python hvdc_link.py --phase-offset 6 --output-dir output_simultaneous
```

The number of joint intervals depends on the phase offset and both overlap
angles. It is **24 in the default example**, not necessarily 24 for arbitrary
parameter combinations.

For double-click generation on Windows, use `gerar_hvdc_completo.bat`.

## Default timing and gating assumptions

- Rectifier: `alpha_rectifier = 15°`, `mu_rectifier = 12°`.
- Inverter: `alpha_inverter = 145°`, `mu_inverter = 15°`.
- Inverter extinction-angle margin: `gamma = 180° − alpha_inverter − mu_inverter = 20°`.
- Required minimum: `gamma_min = 10°`.
- Station phase-reference offset: `ac_phase_offset = 30°` (illustrative only).

Each converter uses six normal two-SCR intervals and six three-SCR overlap
intervals. At the default offset, the union of all switching boundaries
contains **24 joint intervals** over 360°. Exactly four valves are conducting
when neither station overlaps, five when one station overlaps, and six when
both overlap. The graph enumerates 1, 2 or 4 potential complete conduction
loops respectively. These are **not** independent physical DC currents.

The sequence uses a relative electrical time origin at the overlap immediately
preceding the first normal interval. It does not derive actual firing instants
from AC voltage phasors or transformer phase shifts. Thus it must not be used
to claim an exact EMT temporal phase alignment between unrelated grids.

## Generated files

```text
output_hvdc/
  hvdc_normal.svg                     # both stations normally conducting
  hvdc_rectifier_overlap.svg          # rectifier overlap only
  hvdc_inverter_overlap.svg           # inverter overlap only
  hvdc_simultaneous_overlap.svg       # only when this timing case occurs
  hvdc_timeline.svg                   # joint-angle timing chart
  hvdc_joint_state_01.svg ...         # full joint conduction timeline
  hvdc_states.json                    # detailed graph-edge membership
  hvdc_states.csv                     # compact state table
  *.png                               # only when --png is enabled
```

For independent inspection, every SVG uses separate `<g>` layers and
`data-edge-id`, `data-scr`, and `data-active` attributes.

## Verification and limitations

Run `python -m pytest -q tests` to validate the old rectifier/inverter code
and the full HVDC current paths, SCR forward-only polarity, 360° partition,
transformer isolation, parameter checks and SVG metadata.

This module **does not** implement:

- EMT transients, physical current division during overlap, or fault studies;
- 12-pulse series valve groups, Y/Δ shifts, or twelve-pulse cancellation;
- control loops for constant `I_dc`, extinction-angle regulation or VDCOL;
- AC power flow, transformer saturation or grid-voltage harmonics;
- commutation failure, DC line capacitance, ground electrodes or a cable model;
- a solved voltage drop or operating-point solution.

The link resistance and smoothing inductors are **schematic symbols only**:
their numeric values are not required to highlight conductive pathways. A
follow-up engineering stage can add these dynamic or phasor-domain models
without rewriting the underlying drawing and conduction graph.

## Technical starting points

- [EMTP — LCC converter model](https://www.emtp.com/index.php/applications/HVDC):
  industrial twelve-pulse valve groups and the converter transformer shift.
- [MDPI Energies — LCC HVDC analysis](https://www.mdpi.com/1996-1073/15/3/1142):
  DC voltage, line-commutation reactance and smoothing behavior.


## Audit note: typography and angular reference

SVG notation now follows the project-wide engineering convention: italic scalar variables (including Greek), upright physical units and descriptive indices, and bold upright matrix names. SCR labels display `T₁`–`T₆` within the separate station panels. The legacy field name `ac_phase_offset` is an illustrative **relative commutation offset**, not an independently solved physical AC phase shift. The transformer primaries are symbolic AC-network interfaces and their currents are not computed.
