# Fixed axes in the offline LCC HTML lecture

All interactive Canvas charts use deterministic horizontal and vertical domains,
derived from the **full permitted slider ranges**, never from the current
sampled waveform. These domains are centralized in
`presentation/src/fixed_axes.js` and used by half-wave, R/RL/LE/RLE, six-pulse
rectifier/inverter/HVDC, and constant-DC-current lessons.

The angular x-domain remains 0–360 electrical degrees. The averaged current
controller uses 0–0.35 seconds; the controller firing-angle chart uses 0–90°.
Voltages are symmetric about zero, and the positive current range is
consistent across SCR and pole-current plots.

The ideal LE model has no DC resistance and is not a damped periodic operating
point. Under the permitted minimum inductance its one-cycle current can be far
greater than currents in R, RL, and RLE. Therefore LE uses a distinct, fixed,
conservatively bounded current range rather than compressing every other
load-model current graph. Mixed DC-voltage/current load panels show **voltage on
the left axis** and **current on the right axis**, with independent fixed bounds
and distinct axis colors.

If user control limits or controller integration step change, update the
global extrema in `fixed_axes.js` and run:

```sh
node presentation/tests/fixed_axis_model_bounds.js
python presentation/tests/browser_fixed_axes.py
```

The browser test covers all 82 slides, compares axis ranges before and after
parameter variation, and asserts that all charts expose fixed-axis metadata.
The numerical test samples model corner cases and validates the ranges.
No physical model or conversion sign convention is changed by this feature.
