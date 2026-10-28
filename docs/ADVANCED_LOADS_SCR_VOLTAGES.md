# Advanced LCC load equivalents and thyristor-voltage visualization

## Educational progression

The interactive lecture now introduces four DC load equivalents in this order:

1. **R:** pure resistance. The instantaneous current follows the conducting line voltage; for sufficiently delayed firing there are genuine all-valves-blocking intervals.
2. **RL:** the DC inductor stores energy and can keep the current positive even when the instantaneous bridge voltage is negative.
3. **LE:** a smoothing inductor with an **opposing voltage source E**. This models an inverter-side DC voltage equivalent without pretending to resolve the inverter switches at this introductory stage.
4. **RLE:** R models DC resistance, L smooths current, and E opposes the rectifier DC voltage. Its conceptual dynamic equation is `L di_dc/dt + R i_dc = v_dc - E`.

LE is explicitly an **initial-value problem**, not an artificial periodic steady-state solution. With R=0 and sustained conduction, the inductor's volt-seconds must balance for a periodic current to exist. An initial-current control is available.

All four DC load studies neglect AC-side commutation overlap (`mu=0`) so that **DC smoothing inductance** is not confused with **AC source commutation inductance**. The independent rectifier/inverter/HVDC chapters retain their own idealized nonzero overlap models.

## Thyristor voltages

The graph selector includes **SCR voltages** and **SCR voltage & current**. The SCR selector can emphasize one of T1–T6. All valve voltages use the **anode-to-cathode convention** `v_AK = v_anode - v_cathode`.

In the ideal six-pulse rectifier:

- Positive-side SCR anode = phase terminal; cathode = DC positive bus.
- Negative-side SCR anode = DC negative bus; cathode = phase terminal.

The inverter drawings employ the **opposite valve orientation**, so their voltage signs are reversed.

At ideal conduction, the anode–cathode voltage is **zero**. Blocking voltage is evaluated from the AC phase potentials and defined DC bus nodes. During overlap, a midpoint-bus approximation represents equal source reactances. This is explicitly **an illustrative approximation**, not a detailed AC-reactor transient or a guarantee of exact terminal voltage for blocked SCRs.

**When all SCRs block and the DC bus common-mode potential is floating**, the individual valve voltages cannot be resolved from the ideal circuit: the program returns **NaN**, breaks the plotted trace, and displays the limitation. It does not assign fictitious blocking voltages.

## Continuous controls and plotting

Slider increments are small (typically 0.1 degrees or 0.01 p.u.). The angular cursor uses 0.01 degrees, the active state window is shaded semitransparently, and cross-cycle intervals are handled by splitting the 0/360-degree boundary. Curves use unique dash patterns, colors, and partial opacity; selected SCRs receive stronger contrast.

All numerals and physical units are upright. Variables, including Greek mathematical symbols, are italic; descriptive subscripts are upright; matrices are bold upright. The offline HTML implements this with semantic HTML spans and dedicated Canvas label routines. Python SVGs use Matplotlib mathtext with `mathtext.fontset='stix'`.

## Scope and attribution

The light technical-document style is **inspired by the restrained presentation conventions of power-system consulting reports**. It does not use Siemens logos and is **independent educational material, not an official Siemens PTI publication**.

All waveforms are conceptual and should not be used for device sizing, protection, or EMT design.

## Build

```bash
python lcc_advanced_figures.py --output-dir output_lcc/rectifier/advanced_loads
python presentation/build_presentation.py --project . --output dist/lcc_hvdc_interactive.html
python -m pytest -q tests presentation/tests
```

Only an HTML presentation is produced by this release. No PowerPoint output is generated.
