# LCC learning sequence: rectifier first, inverter second

The generator models **two standalone six-pulse bridges**. These are didactic
subsystems. The comparison drawing does **not** electrically connect them to
form an entire HVDC system (no converter transformers, transmission line,
voltage/current control, harmonic filters or realistic back-to-back coupling).

## Stage 1: Rectifier (AC -> DC)

- The AC sources supply power; the DC resistor absorbs it.
- Each upper SCR conducts from its associated AC phase to the positive DC bus.
- Each lower SCR conducts from the negative DC bus to its associated AC phase.
- DC current goes from the positive bus through smoothing reactor and resistor
  to the negative bus.

## Stage 2: Inverter (DC -> AC)

- The **DC supply** provides power; the AC sources represent a receiving grid.
- Upper valves now point **from the positive DC bus toward the AC grid**.
- Lower valves point **from the AC grid to the negative DC bus**.
- Current in the *external DC supply* flows from its negative to positive
  terminal, as expected of a source delivering electrical power.
- The DC link current enters the inverter bridge at the positive DC bus. The
  red arrows and the SCR polarity are reversed compared with the rectifier.
- This convention matches the up/down thyristor-direction choice documented
  for the PSCAD six-pulse bridge model; it is an explicit drawing convention.

The same valve identifiers are retained for easier comparison: **T1, T3, T5**
form the upper row and **T2, T4, T6** form the lower row. Each 60-degree
firing-cycle sector replaces one of the two active valves. The same twelve
*topological* pairs/triples can therefore be displayed in both diagrams,
without asserting that their absolute grid-voltage phase angles are identical.

## Overlap and extinction angles

For the inverter, use the simple *steady-state textbook relation*:

    alpha + mu + gamma = 180 degrees

For example, alpha = 145 deg and mu = 15 deg imply gamma = 20 deg.
Set a positive gamma_min, e.g. 10 deg. Operating points for which gamma is
below the user-defined threshold are rejected by the command-line program.

**Important limitations:** these are connectivity illustrations, not EMT
simulation results. No instantaneous SCR current, overlap current sharing,
waveform, physical transformer leakage value, firing pulse synchronization,
commutation-failure transient or absolute valve firing phase reference is
calculated. Drawing a valve as conducting is not evidence that its instantaneous
voltage/current would permit turn-on under arbitrary source waveforms.

## Reproducible figure generation

```bash
# Generate both sets of twelve conduction diagrams and a two-stage overview
python lcc_converter.py --side both --alpha 145 --mu 15 --output-dir output_lcc

# Just the inverter's twelve states
python lcc_converter.py --side inverter --alpha 145 --mu 15 --output-dir output_lcc/inverter

# One inverter overlap state
python lcc_converter.py --side inverter --state 2 --gamma 20 --mu 15 --output-dir output_lcc/inverter

# Highlight SCRs and circuit components manually
python lcc_converter.py --side inverter --manual --thyristors T1,T6 --inductors LA,LC,LDC --sources VA,VC --dc-source on --output-dir output_lcc/inverter

# JSON-driven configuration
python lcc_converter.py --config config_inversor.json

# Run the regression suite
python -m pytest tests -q
```

## References

- PSCAD, [6-Pulse Bridge 2](https://www.pscad.com/webhelp-v502-ol/Master_Library_Models/HVDC_and_FACTS/6_Pulse_Bridge/6-Pulse_Bridge_2.htm) — SCR direction for rectifier/inverter.
- Chalmers University of Technology, [Principle Operation and Controls of the HVDC System](https://publications.lib.chalmers.se/records/fulltext/241111/241111.pdf) — alpha, mu and gamma relationship.
- European Power Electronics studies on [commutation failure and inverter currents](https://www.sciencedirect.com/science/article/pii/S0378779623002481).
