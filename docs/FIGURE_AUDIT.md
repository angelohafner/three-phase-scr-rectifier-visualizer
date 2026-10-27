# Technical and typographic figure audit

## Corrections implemented

1. Full HVDC SCR IDs were incorrectly formed from the station prefix and the full device label (`T_RT1`); the SVG now displays clean mathematical device references `T₁` through `T₆`. The station remains identified separately by its heading and SVG data attributes (`R_T1`, `I_T1`).
2. Some angle annotations were plain upright prose or indiscriminately italicized. Greek variables and scalar variables now use italic STIX-style math, numerical values and physical units use upright text, and descriptor subscripts (`dc`, `line`, `r`, `i`) use upright style.
3. `ElementTree.indent` inserted whitespace between math `<tspan>` elements. A dedicated `indent_svg` routine removes formatting-only whitespace from mathematical labels while preserving XML indentation elsewhere.
4. Transformer secondary reactor labels are centered above their coils. Primary-side sinusoidal source labels `v_a`, `v_b`, and `v_c` were added in mathematical notation. Phase terminal designations `A`, `B`, `C` and star point `O` are upright identifiers.
5. The displayed angle-origin wording now explicitly distinguishes the **illustrative relative commutation offset** from a physically solved phase angle. The legacy `ac_phase_offset` configuration key remains unchanged for compatibility.

## Important electrical limitations

- The diagrams represent directed, graph-validated conduction connectivity: no device reverse-current paths are accepted.
- Transformer primary terminals and sources are schematic external AC network interfaces; they do not solve primary currents or electromagnetic coupling.
- The inverter is drawn with the valve-current polarity appropriate to the stated incoming-positive-conductor convention. These symbolic drawings are not claims of an EMT-model topology or a validated specific manufacturer station design.
- The voltage-sign and absolute firing-angle relationships of the two unsynchronized AC networks are **not solved** by the program. The relative commutation timeline is pedagogical. Do not infer power flow, voltage waveforms, or current sharing from the colors alone.
- Neither commutation current transfer nor extinction margin under disturbances is calculated.

## Regenerate and verify (Python 3.10+)

```bash
python -m pytest -q
python retificador_trifasico_inkscape.py --all-12 --mu 15 --output-dir output
python lcc_converter.py --side both --alpha 145 --mu 15 --output-dir output_lcc
python hvdc_link.py --config config_hvdc.json --all --png --output-dir output_hvdc
```

Use Inkscape to open the individual SVG files directly; these remain vector and editable.

## Math-text API

`math_label` typesets scalar symbols in italics with separate subscripts. `math_formula` supports tokens with the roles `variable`, `roman`, `unit`, `matrix`, `subscript-variable`, and `subscript-roman`. `angle_notation` formats values in degrees. `matrix_label` formats matrix symbols **upright and bold**, as specifically required by the project. SVG source retains `data-math-role` on the corresponding editable `<tspan>` elements.
