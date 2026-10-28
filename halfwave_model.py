#!/usr/bin/env python3
"""Ideal single-SCR half-wave rectifiers with R and series RL loads.

The source is sinusoidal and the SCR is ideal. There is no freewheeling
path. During conduction, current is obtained analytically from the RL
first-order differential equation, and extinction is the first zero after
current has been established. Units: V, ohm, H, A, seconds, degrees.
"""
from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class HalfWaveSettings:
    load: str = 'RL'
    alpha_deg: float = 50.0
    resistance_ohm: float = 12.0
    inductance_mH: float = 70.0
    voltage_peak_V: float = 120.0
    frequency_Hz: float = 60.0

    def __post_init__(self) -> None:
        if self.load not in ('R', 'RL'):
            raise ValueError('Only R and RL are supported')
        for x in (self.alpha_deg, self.resistance_ohm, self.inductance_mH,
                  self.voltage_peak_V, self.frequency_Hz):
            if not math.isfinite(x):
                raise ValueError('Parameters must be finite')
        if not 0 <= self.alpha_deg < 180:
            raise ValueError('Firing angle must be in [0, 180) degrees')
        if self.resistance_ohm <= 0 or self.voltage_peak_V <= 0 or self.frequency_Hz <= 0:
            raise ValueError('R, source amplitude and frequency must be positive')
        if self.inductance_mH < 0:
            raise ValueError('Inductance cannot be negative')

    @property
    def inductance_H(self) -> float:
        return self.inductance_mH / 1000 if self.load == 'RL' else 0.0


@dataclass(frozen=True)
class HalfWavePoint:
    theta_deg: float
    vs_V: float
    vo_V: float
    vr_V: float
    vl_V: float
    vak_V: float
    i_A: float
    energy_J: float
    conducting: bool


class HalfWaveModel:
    """Exact continuous conduction trajectory for an ideal SCR and R/RL load."""

    def __init__(self, settings: HalfWaveSettings):
        self.config = settings
        self.alpha_rad = math.radians(settings.alpha_deg)
        self.omega = 2 * math.pi * settings.frequency_Hz
        self.L = settings.inductance_H
        self.R = settings.resistance_ohm
        self.V = settings.voltage_peak_V
        self.tau = self.L / self.R if self.L else 0.0
        self.phi = math.atan2(self.omega * self.L, self.R)
        self.impedance = math.hypot(self.R, self.omega * self.L)
        self.beta_deg = self._find_beta()

    def _unclamped_current(self, angle: float) -> float:
        if not self.L:
            return self.V * math.sin(angle) / self.R
        delta = angle - self.alpha_rad
        decay = math.exp(-delta * self.R / (self.omega * self.L))
        return (self.V / self.impedance) * (
            math.sin(angle - self.phi) -
            math.sin(self.alpha_rad - self.phi) * decay
        )

    def _find_beta(self) -> float:
        if not self.L:
            return 180.0
        lo, hi = math.pi, 2 * math.pi
        if self._unclamped_current(lo) <= 0:
            # Only possible in the limiting case of vanishing conduction.
            return 180.0
        if self._unclamped_current(hi) >= 0:
            raise ArithmeticError('The expected current-zero crossing was not bracketed')
        for _ in range(90):
            mid = (lo + hi) / 2
            if self._unclamped_current(mid) > 0:
                lo = mid
            else:
                hi = mid
        return math.degrees((lo + hi) / 2)

    def sample(self, theta_deg: float) -> HalfWavePoint:
        theta = theta_deg % 360.0
        angle = math.radians(theta)
        vs = self.V * math.sin(angle)
        on = (self.config.alpha_deg <= theta < self.beta_deg)
        current = max(0.0, self._unclamped_current(angle)) if on else 0.0
        if current < 1e-12:
            current = 0.0
            on = False
        vo = vs if on else 0.0
        vr = self.R * current
        vl = vs - vr if on and self.L else 0.0
        vak = 0.0 if on else vs
        return HalfWavePoint(theta, vs, vo, vr, vl, vak, current,
                             0.5 * self.L * current * current, on)

    def series(self, step_deg: float = 0.25) -> list[HalfWavePoint]:
        if step_deg <= 0 or 360 / step_deg != int(360 / step_deg):
            raise ValueError('Step must divide 360 degrees')
        return [self.sample(i * step_deg) for i in range(round(360 / step_deg) + 1)]

    def windows(self) -> list[tuple[float, float]]:
        return [(self.config.alpha_deg, self.beta_deg)]

    def delayed_extinction(self) -> tuple[float, float] | None:
        return (180.0, self.beta_deg) if self.beta_deg > 180.000001 else None


if __name__ == '__main__':
    import json
    model = HalfWaveModel(HalfWaveSettings())
    print(json.dumps({'alpha_deg': model.config.alpha_deg, 'beta_deg': model.beta_deg,
                      'at_180': model.sample(180).__dict__}, indent=2))
