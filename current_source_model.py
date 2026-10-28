#!/usr/bin/env python3
"""Conceptual six-pulse LCC DC current source and commutation model.

Current source is a DC-side load constraint, not a replacement for the
balanced sinusoidal AC voltages that drive natural line commutation.

With equal AC phase inductances, 2 L_c di_in/dt = v_in - v_out.
For illustrative physical bases V_phase,peak=1 kV and I_base=1 kA, the overlap
relation is I_dc = sqrt(3)*V_phase,peak/(2*omega*L_c)
                    * (cos(alpha) - cos(alpha+mu)).
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np

PAIRS = ((0, 2), (1, 2), (1, 0), (2, 0), (2, 1), (0, 1))
UPPER = ('T1', 'T3', 'T5')
LOWER = ('T2', 'T4', 'T6')
SCRS = ('T1', 'T2', 'T3', 'T4', 'T5', 'T6')


@dataclass(frozen=True)
class CurrentSourceSettings:
    """Reference operating conditions with documented illustrative unit bases."""

    idc_pu: float = 1.0
    voltage_phase_peak_pu: float = 1.0
    alpha_deg: float = 15.0
    mu_deg: float = 15.0
    commutation_inductance_mH: float = 0.20
    frequency_hz: float = 60.0
    overlap_mode: str = 'manual'

    def __post_init__(self) -> None:
        if self.overlap_mode not in ('manual', 'calculated'):
            raise ValueError('overlap_mode must be manual or calculated')
        if not all(map(math.isfinite, (self.idc_pu, self.voltage_phase_peak_pu,
                self.alpha_deg, self.mu_deg, self.commutation_inductance_mH,
                self.frequency_hz))):
            raise ValueError('All parameters must be finite')
        if not (0 < self.idc_pu <= 10 and self.voltage_phase_peak_pu > 0):
            raise ValueError('Current and phase-voltage magnitudes must be positive')
        if not (0 <= self.alpha_deg <= 85 and 0 <= self.mu_deg < 60):
            raise ValueError('Rectifier firing angle or imposed overlap is invalid')
        if not (self.commutation_inductance_mH > 0 and self.frequency_hz > 0):
            raise ValueError('AC commutation inductance and frequency must be positive')


def overlap_degrees(settings: CurrentSourceSettings) -> float:
    """Return mu using a two-equal-inductance natural-commutation model.

    A missing 60-degree solution raises ValueError rather than silently
    displaying a physically impossible three-valve current waveform.
    """
    if settings.overlap_mode == 'manual':
        return settings.mu_deg
    alpha = math.radians(settings.alpha_deg)
    omega = 2 * math.pi * settings.frequency_hz
    l = settings.commutation_inductance_mH * 1e-3
    # Illustrative physical bases: 1 kV phase peak and 1 kA DC, Z_base = 1 ohm.
    phase_peak_v = settings.voltage_phase_peak_pu * 1000.0
    dc_a = settings.idc_pu * 1000.0
    cos_endpoint = math.cos(alpha) - (2 * omega * l * dc_a / (
        math.sqrt(3) * phase_peak_v))
    if not -1 <= cos_endpoint <= 1:
        raise ValueError('No possible complete commutation with these conditions')
    mu = math.degrees(math.acos(cos_endpoint) - alpha)
    if mu >= 60 - 1e-8 or mu < 0:
        raise ValueError('Commutation does not finish within one 60-degree sector')
    return mu


def transfer_fraction(local_angle: float, settings: CurrentSourceSettings,
                      mu: float) -> float:
    """Linear teaching profile, or normalized commutation-voltage integral."""
    if mu <= 0 or local_angle >= mu:
        return 1.0
    if local_angle <= 0:
        return 0.0
    if settings.overlap_mode == 'manual':
        return local_angle / mu
    a = math.radians(settings.alpha_deg)
    numerator = math.cos(a) - math.cos(a + math.radians(local_angle))
    denominator = math.cos(a) - math.cos(a + math.radians(mu))
    return max(0.0, min(1.0, numerator / denominator))


def sample(angle_deg: float, settings: CurrentSourceSettings) -> dict:
    """Topological DC-source currents and voltages over one 360-degree cycle."""
    mu = overlap_degrees(settings)
    angle = angle_deg % 360
    sector = int(angle // 60)
    local = angle - sector * 60
    old_idx, new_idx = (sector + 5) % 6, sector
    overlap = mu > 1e-10 and local < mu - 1e-10
    f = transfer_fraction(local, settings, mu) if overlap else 1.0
    scr = {name: 0.0 for name in SCRS}
    for pair_idx, fraction in ((old_idx, 1 - f if overlap else 0),
                               (new_idx, f if overlap else 1)):
        up, lo = PAIRS[pair_idx]
        scr[UPPER[up]] += settings.idc_pu * fraction
        scr[LOWER[lo]] += settings.idc_pu * fraction
    ac = [scr[UPPER[k]] - scr[LOWER[k]] for k in range(3)]
    source_angle = math.radians(angle + settings.alpha_deg)
    phase = [settings.voltage_phase_peak_pu * math.cos(source_angle - k*2*math.pi/3)
             for k in range(3)]
    upper_new, lower_new = PAIRS[new_idx]
    upper_old, lower_old = PAIRS[old_idx]
    v_new = phase[upper_new] - phase[lower_new]
    v_old = phase[upper_old] - phase[lower_old]
    # Equal-commutation-reactance, idealized midpoint voltage during overlap.
    dc = 0.5 * (v_old + v_new) if overlap else v_new
    return {
        'theta': angle,
        'state': (12 if sector == 0 else sector*2) if overlap else 2*sector+1,
        'sector': sector,
        'overlap': overlap,
        'mu': mu,
        'transfer': f,
        'scr': scr,
        'ac': ac,
        'phase': phase,
        'line': [phase[0]-phase[1], phase[1]-phase[2], phase[2]-phase[0]],
        'dc': dc,
        'idc': settings.idc_pu,
        'outgoing': list(scr for scr in (UPPER[upper_old], LOWER[lower_old])
                         if scr not in (UPPER[upper_new], LOWER[lower_new]))[0] if overlap else None,
        'incoming': list(scr for scr in (UPPER[upper_new], LOWER[lower_new])
                         if scr not in (UPPER[upper_old], LOWER[lower_old]))[0] if overlap else None,
        'stationary': list(scr for scr in (UPPER[upper_new], LOWER[lower_new])
                           if scr in (UPPER[upper_old], LOWER[lower_old]))[0] if overlap else None,
    }


def full_cycle(settings: CurrentSourceSettings, points: int = 1441) -> dict:
    """Sample phase voltages and every SCR current at common angular points."""
    angles = np.linspace(0, 360, points)
    samples = [sample(float(a), settings) for a in angles]
    return {
        'angle': angles,
        'idc': np.array([p['idc'] for p in samples]),
        'dc': np.array([p['dc'] for p in samples]),
        'scr': {name: np.array([p['scr'][name] for p in samples]) for name in SCRS},
        'ac': np.array([p['ac'] for p in samples]).T,
        'phase': np.array([p['phase'] for p in samples]).T,
    }
