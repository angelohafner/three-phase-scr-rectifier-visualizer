#!/usr/bin/env python3
"""Conceptual, piecewise analytical waveforms tied to existing LCC schedules.

This module does NOT solve EMT differential equations. A linear SCR transfer
is paired with an illustrative equal-reactance voltage average during overlap.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal
import numpy as np

from rectifier_model import CommutationSequence, PAIRS, UPPER, LOWER
from hvdc_link_model import CombinedSchedule, LinkSettings

SCR_ORDER = ('T1', 'T2', 'T3', 'T4', 'T5', 'T6')
PHASES = ('a', 'b', 'c')
PHASE_ID = {'a': 0, 'b': 1, 'c': 2}
SCR_ID = {s: i for i, s in enumerate(SCR_ORDER)}
UPPER_NUM = np.array([SCR_ID[UPPER[h]] for h, _ in PAIRS], dtype=int)
LOWER_NUM = np.array([SCR_ID[LOWER[l]] for _, l in PAIRS], dtype=int)


@dataclass(frozen=True)
class WaveformConfig:
    """Illustrative nominal amplitudes and SVG/PNG output controls."""
    ac_peak: float = 1.0
    dc_current: float = 1.0
    samples: int = 1441
    png_dpi: int = 110
    show_phase: bool = True
    show_line: bool = True
    show_scr: bool = True
    show_dc: bool = True
    show_idc: bool = True
    combined: bool = True
    png: bool = True

    def __post_init__(self) -> None:
        if not (isfinite(self.ac_peak) and self.ac_peak > 0):
            raise ValueError('ac_peak must be positive and finite')
        if not (isfinite(self.dc_current) and self.dc_current > 0):
            raise ValueError('dc_current must be positive and finite')
        if not 721 <= self.samples <= 20001:
            raise ValueError('samples must lie between 721 and 20001')
        if not 72 <= self.png_dpi <= 220:
            raise ValueError('png_dpi must lie between 72 and 220')
        if not any((self.show_phase, self.show_line, self.show_scr,
                    self.show_dc, self.show_idc)):
            raise ValueError('At least one signal group must be enabled')


@dataclass(frozen=True)
class StationCurves:
    """Arrays sampled on an unchanged global 0..360-degree angle axis."""
    operation: Literal['rectifier', 'inverter']
    theta: np.ndarray
    local_theta: np.ndarray
    phase_v: np.ndarray             # shape (3, N), phase-to-star neutral
    line_v: np.ndarray              # shape (3, N), v_ab, v_bc, v_ca
    scr_i: np.ndarray               # shape (6, N), anode-to-cathode currents
    ac_i: np.ndarray                # shape (3, N), grid -> converter
    dc_i: np.ndarray                # shape (N,), smoothed pole current
    dc_v_ideal: np.ndarray          # shape (N,), instantaneous transfer
    dc_v_overlap: np.ndarray        # shape (N,), simplified equal-reactance voltage
    state_numbers: np.ndarray       # shape (N,), 1..12
    in_overlap: np.ndarray          # shape (N,)
    transfer: np.ndarray            # shape (N,), fraction of current transferred
    offset: float
    alpha: float
    mu: float
    beta: float | None = None
    gamma: float | None = None

    @property
    def label(self) -> str:
        return 'Rectifier' if self.operation == 'rectifier' else 'Inverter'


class CommutationCurrentModel:
    """Linear overlap current transfer between the old and the new SCR pair."""

    @staticmethod
    def compute(local_theta: np.ndarray, mu: float, dc_current: float
                ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Return currents (6,N), state numbers, overlap flags and transfer fractions."""
        rel = np.mod(local_theta, 360.0)
        sector = np.floor(rel / 60.0).astype(int)
        fraction = rel - sector * 60.0
        overlap = fraction < mu - 1e-10
        fraction_transfer = np.where(overlap, fraction / mu, 1.0)
        prev_sector = (sector - 1) % 6
        # Each state has exactly one active upper valve and one active lower valve.
        currents = np.zeros((6, rel.size), dtype=float)
        cols = np.arange(rel.size)
        old_weight = np.where(overlap, 1.0 - fraction_transfer, 0.0)
        new_weight = np.where(overlap, fraction_transfer, 1.0)
        np.add.at(currents, (UPPER_NUM[prev_sector], cols), dc_current * old_weight)
        np.add.at(currents, (LOWER_NUM[prev_sector], cols), dc_current * old_weight)
        np.add.at(currents, (UPPER_NUM[sector], cols), dc_current * new_weight)
        np.add.at(currents, (LOWER_NUM[sector], cols), dc_current * new_weight)
        state_ids = np.where(overlap, np.where(sector == 0, 12, 2*sector),
                             2*sector+1).astype(int)
        return currents, state_ids, overlap, fraction_transfer


class LCCWaveformModel:
    """Standalone rectifier/inverter models using the existing valve schedule."""

    def __init__(self, config: WaveformConfig | None = None):
        self.config = config or WaveformConfig()

    def station(self, operation: Literal['rectifier','inverter'], *,
                alpha: float, mu: float, offset: float = 0.0,
                gamma_min: float = 0.0,
                theta: np.ndarray | None = None) -> StationCurves:
        """Generate an entire cycle at fixed global electrical-angle samples.

        Rectifier: natural upper commutation precedes its trigger by alpha.
        Inverter: beta=(180-alpha) is the advance angle; the incoming reverse-
        oriented upper SCR commutates before the natural cathode crossover.
        Inverter DC voltage is the *positive pole-to-return* DC-side drop.
        In the conventional rectifier-oriented voltage sign, its value is -Vdi.
        """
        if operation not in ('rectifier', 'inverter'):
            raise ValueError('operation must be rectifier or inverter')
        CommutationSequence(mu)
        if not isfinite(alpha) or not isfinite(offset):
            raise ValueError('Angles must be finite')
        if operation == 'rectifier' and not 0 <= alpha < 90:
            raise ValueError('Rectifier alpha must lie within [0, 90) degrees')
        if operation == 'inverter' and not 90 < alpha < 180:
            raise ValueError('Inverter alpha must lie within (90, 180) degrees')
        beta = 180.0 - alpha if operation == 'inverter' else None
        gamma = (beta - mu) if operation == 'inverter' else None
        if gamma is not None and not (gamma >= gamma_min and gamma > 0):
            raise ValueError('Inverter gamma must be positive and >= gamma_min')
        angle = (np.linspace(0.0, 360.0, self.config.samples)
                 if theta is None else np.asarray(theta, dtype=float))
        if angle.ndim != 1 or not angle.size or not np.all(np.isfinite(angle)):
            raise ValueError('theta must be a finite, one-dimensional angle vector')
        local = np.mod(angle - offset, 360.0)
        currents, states, overlaps, transfer = CommutationCurrentModel.compute(
            local, mu, self.config.dc_current)
        if operation == 'rectifier':
            argument_deg = local + alpha
        else:
            argument_deg = local - beta
        argument = np.deg2rad(argument_deg)
        v = self.config.ac_peak * np.vstack((
            np.cos(argument),
            np.cos(argument - 2*np.pi/3),
            np.cos(argument + 2*np.pi/3),
        ))
        line = np.vstack((v[0]-v[1], v[1]-v[2], v[2]-v[0]))
        sector = np.floor(local / 60).astype(int)
        prev = (sector-1) % 6
        cols = np.arange(len(angle))
        hi_curr = np.array([PHASE_ID[h] for h, _ in PAIRS])[sector]
        lo_curr = np.array([PHASE_ID[l] for _, l in PAIRS])[sector]
        hi_prev = np.array([PHASE_ID[h] for h, _ in PAIRS])[prev]
        lo_prev = np.array([PHASE_ID[l] for _, l in PAIRS])[prev]
        v_new = v[hi_curr, cols] - v[lo_curr, cols]
        v_old = v[hi_prev, cols] - v[lo_prev, cols]
        # With equal commutation inductances, the phase-voltage midpoint gives
        # a qualitative commutation notch. It is not a solved current waveform.
        v_comm = np.where(overlaps, (v_new+v_old)/2.0, v_new)
        ac_curr = np.vstack([
            currents[SCR_ID[UPPER[p]]] - currents[SCR_ID[LOWER[p]]]
            for p in PHASES
        ])
        if operation == 'inverter':
            ac_curr *= -1.0  # Sign convention: positive grid -> converter.
        return StationCurves(operation, angle, local, v, line, currents,
                             ac_curr, np.full_like(angle, self.config.dc_current),
                             v_new, v_comm, states, overlaps, transfer,
                             offset, alpha, mu, beta, gamma)


class WaveformValidator:
    """Check KCL, schedule matching and elementary converter polarities."""

    @staticmethod
    def validate_station(c: StationCurves, dc_current: float) -> None:
        upper = [SCR_ID[x] for x in ('T1', 'T3', 'T5')]
        lower = [SCR_ID[x] for x in ('T2', 'T4', 'T6')]
        if not np.allclose(c.scr_i[upper].sum(axis=0), dc_current, atol=1e-9):
            raise AssertionError('Upper valve current is not conserved')
        if not np.allclose(c.scr_i[lower].sum(axis=0), dc_current, atol=1e-9):
            raise AssertionError('Lower valve current is not conserved')
        if np.min(c.scr_i) < -1e-10:
            raise AssertionError('Negative SCR current in forward conduction model')
        if not np.allclose(c.ac_i.sum(axis=0), 0, atol=1e-9):
            raise AssertionError('Three AC phase currents do not sum to zero')
        if not np.allclose(c.dc_i, dc_current):
            raise AssertionError('Nonconstant DC current in fixed-current model')
        if np.any(c.in_overlap & ~np.isin(c.state_numbers, [2,4,6,8,10,12])):
            raise AssertionError('Overlap incorrectly mapped to normal state')
        if np.any(~c.in_overlap & ~np.isin(c.state_numbers, [1,3,5,7,9,11])):
            raise AssertionError('Normal conduction incorrectly mapped to overlap')
        if c.operation == 'inverter' and not np.all(c.dc_v_overlap >= -1e-10):
            # Negative *instantaneous* line voltages are allowed near the edge of
            # extreme assumptions; inspect mean sign rather than pointwise sign.
            if np.mean(c.dc_v_overlap) <= 0:
                raise AssertionError('Inverter DC voltage mean must be positive in local pole-drop convention')

    @staticmethod
    def verify_interval(c: StationCurves, selected_state: int,
                        start: float, end: float) -> None:
        if not 1 <= selected_state <= 12:
            raise AssertionError('Invalid expected SCR state')
        mid = (start+end)/2.0
        nearest = np.argmin(np.abs(c.theta-mid))
        if int(c.state_numbers[nearest]) != selected_state:
            raise AssertionError(f'Waveform/schematic mismatch: expected state {selected_state} '
                                 f'but found {c.state_numbers[nearest]} at {mid:g} degrees')
        actual = frozenset(SCR_ORDER[k] for k in range(6) if c.scr_i[k,nearest]>1e-6)
        expected = CommutationSequence(c.mu).state(selected_state).scrs
        if actual != expected:
            raise AssertionError(f'Wrong SCR currents for diagram {selected_state}: '
                                 f'{actual} != {expected}')


def station_state_windows(state_number: int, mu: float
                          ) -> tuple[tuple[float,float], ...]:
    """Map a 12-state local interval onto an unwrapped full 360-degree cycle."""
    state = CommutationSequence(mu).state(state_number)
    lo,hi = state.theta_start,state.theta_end
    if lo >= 360:
        return ((0.0, hi-360.0),)
    if hi>360:
        return ((lo,360.0),(0.0,hi-360.0))
    return ((lo,hi),)


def settings_for_hvdc(config: dict) -> LinkSettings:
    """Recreate the existing combined scheduler without duplicated defaults."""
    return LinkSettings(**{k: float(v) for k,v in config.items()})


def verify_joint_sync(schedule: CombinedSchedule, rectifier: StationCurves,
                      inverter: StationCurves) -> None:
    """Assert joint-state midpoint currents match both original schematics."""
    for joint in schedule.intervals:
        WaveformValidator.verify_interval(rectifier, joint.rectifier.number,
                                          joint.theta_start, joint.theta_end)
        WaveformValidator.verify_interval(inverter, joint.inverter.number,
                                          joint.theta_start, joint.theta_end)
