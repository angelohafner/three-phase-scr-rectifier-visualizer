#!/usr/bin/env python3
"""Conceptual LCC six-pulse LE and RLE loads with explicit valve voltages.

This model assumes ideal SCRs and zero AC-side commutation inductance.
An opposing DC voltage source represents a simplified inverter equivalent.
The inductive LE model is an initial-value problem, not a periodic steady state.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

import rectifier_art as art
from schemdraw_symbols import draw_dc_source
from rectifier_loads import (
    LoadParameters, LoadWaveforms, ResistiveCircuitRenderer, ResistiveInductiveLoad,
    ResistiveLoad, assemble, fired_pair, pair_voltage, phase_voltages,
)
from rectifier_model import PAIRS, UPPER, LOWER


@dataclass(frozen=True)
class AdvancedLoadParameters:
    """Normalized AC amplitude and physical DC load equivalent parameters."""
    alpha_deg: float = 75.0
    resistance_ohm: float = 1.0
    inductance_mH: float = 8.0
    source_voltage_pu: float = 0.2
    initial_current_pu: float = 0.5
    phase_peak_pu: float = 1.0
    frequency_hz: float = 60.0

    def __post_init__(self) -> None:
        v = (self.alpha_deg, self.resistance_ohm, self.inductance_mH,
             self.source_voltage_pu, self.initial_current_pu,
             self.phase_peak_pu, self.frequency_hz)
        if not all(isfinite(x) for x in v):
            raise ValueError('All load parameters must be finite')
        if not 0 <= self.alpha_deg < 120:
            raise ValueError('Firing angle must be in [0, 120) degrees')
        if self.resistance_ohm <= 0 or self.inductance_mH <= 0:
            raise ValueError('R and L must be positive for the RLE numerical model')
        if self.source_voltage_pu < 0 or self.initial_current_pu < 0:
            raise ValueError('DC source voltage and initial current cannot be negative')
        if self.phase_peak_pu <= 0 or self.frequency_hz <= 0:
            raise ValueError('Phase peak and frequency must be positive')


class VoltageSourceLoad:
    """Ideal thyristor bridge with LE or RLE DC circuit and natural extinction."""
    def __init__(self, parameters: AdvancedLoadParameters, mode: str):
        if mode not in ('LE', 'RLE'):
            raise ValueError('Mode must be LE or RLE')
        self.p = parameters
        self.mode = mode

    def sample(self, theta: np.ndarray, settling_cycles: int = 7) -> LoadWaveforms:
        a = np.asarray(theta, dtype=float)
        if a.ndim != 1 or len(a) < 2 or abs(a[0]) > 1e-8 or abs(a[-1]-360) > 1e-8:
            raise ValueError('Uniform theta must span 0 through 360 degrees')
        step = float(a[1] - a[0])
        if not np.allclose(np.diff(a), step, atol=1e-8, rtol=0):
            raise ValueError('Uniform angular steps are required')
        p = self.p
        # A lossless LE circuit cannot generally settle to a periodic waveform.
        cycles = 1 if self.mode == 'LE' else max(1, settling_cycles)
        R = p.resistance_ohm if self.mode == 'RLE' else 0.0
        L = p.inductance_mH * 1e-3
        dt = step / (360 * p.frequency_hz)
        fac = exp(-R * dt / L) if R > 0 else 1.0
        current = p.initial_current_pu
        pair = -1
        previous_sector = None
        n = len(a)
        currents = np.zeros(n)
        conduct = np.full(n, -1, dtype=int)
        output = np.full(n, p.source_voltage_pu)
        for cycle in range(cycles):
            previous_sector = None
            for j, angle in enumerate(a[:-1]):
                sector = int(np.floor((angle - p.alpha_deg + 1e-9) / 60))
                fire_pair = sector % 6
                if previous_sector != sector:
                    # Ideal wide/double gate pulses permit latching after a gap.
                    source_phase = phase_voltages(np.array([angle + 1e-9]), p.phase_peak_pu)
                    available = float(pair_voltage(source_phase, np.array([fire_pair]))[0])
                    if current > 1e-10 or available > p.source_voltage_pu:
                        pair = fire_pair
                    else:
                        pair = -1
                    previous_sector = sector
                if pair >= 0:
                    mid = phase_voltages(np.array([angle + step / 2]), p.phase_peak_pu)
                    supply = float(pair_voltage(mid, np.array([pair]))[0])
                    drive = supply - p.source_voltage_pu
                    if R > 0:
                        next_i = current*fac + (drive/R)*(1-fac)
                    else:
                        next_i = current + (drive/L)*dt
                    if next_i <= 1e-10:
                        current = 0.0
                        pair = -1
                    else:
                        current = next_i
                else:
                    current = 0.0
                if cycle == cycles-1:
                    currents[j] = current
                    conduct[j] = pair
                    if pair >= 0:
                        ph = phase_voltages(np.array([angle]), p.phase_peak_pu)
                        output[j] = float(pair_voltage(ph, np.array([pair]))[0])
                    else:
                        # E fixes the load differential voltage but not its
                        # absolute common mode relative to the AC star point.
                        output[j] = p.source_voltage_pu
        currents[-1] = currents[-2] if self.mode == 'LE' else currents[0]
        conduct[-1] = conduct[-2] if self.mode == 'LE' else conduct[0]
        output[-1] = output[-2] if self.mode == 'LE' else output[0]
        old = LoadParameters(alpha_deg=p.alpha_deg, resistance_ohm=p.resistance_ohm,
                             inductance_mH=p.inductance_mH,
                             frequency_hz=p.frequency_hz, phase_peak_pu=p.phase_peak_pu)
        return assemble(a, old, self.mode, currents, conduct, output)


def valve_voltages(phase_voltages_pu: np.ndarray, active_pairs: np.ndarray,
                   mode: str = 'rectifier') -> dict[str, np.ndarray]:
    """Ideal SCR vAK from node potentials; NaN denotes floating DC buses.

    Rectifier: upper SCR anode=phase, cathode=DC+, lower anode=DC-,
    cathode=phase. Inverter: the physical SCR polarity is reversed.
    """
    if mode not in ('rectifier','inverter'):
        raise ValueError('Mode must be rectifier or inverter')
    ph = np.asarray(phase_voltages_pu, dtype=float)
    prs = np.asarray(active_pairs, dtype=int)
    if ph.ndim != 2 or ph.shape[0] != 3 or prs.shape != (ph.shape[1],):
        raise ValueError('Mismatched phase-voltage and conducting-pair shapes')
    all_scr = {f'T{k}': np.full(ph.shape[1], np.nan) for k in range(1,7)}
    for index in np.where(prs >= 0)[0]:
        hi, lo = PAIRS[int(prs[index])]
        vp = ph[['a','b','c'].index(hi),index]
        vn = ph[['a','b','c'].index(lo),index]
        for phase, upper, lower in [('a','T1','T2'),('b','T3','T4'),('c','T5','T6')]:
            a = ph[['a','b','c'].index(phase),index]
            factor = -1 if mode == 'inverter' else 1
            all_scr[upper][index] = factor*(a-vp)
            all_scr[lower][index] = factor*(vn-a)
    return all_scr


def render_voltage_source_circuit(p: AdvancedLoadParameters, angle: float,
                                  pair: int | None, mode: str) -> ET.ElementTree:
    """Reuse the SCR bridge and add the opposing source in series with the DC coil."""
    if mode not in ('LE','RLE'):
        raise ValueError('Mode must be LE or RLE')
    previous = LoadParameters(alpha_deg=p.alpha_deg, resistance_ohm=p.resistance_ohm,
                              inductance_mH=p.inductance_mH, phase_peak_pu=p.phase_peak_pu)
    tree = ResistiveCircuitRenderer().render(previous, angle, pair, 'RL')
    root = tree.getroot()
    active = pair is not None
    for parent in root.iter():
        for child in list(parent):
            ident = child.get('id', '')
            if ident in ('base-carga_l_r','selected-carga_l_r') or (
                mode == 'LE' and ident in ('base-r','selected-r')):
                parent.remove(child)
            if mode == 'LE' and child.tag == art.S+'text' and child.text == 'R':
                parent.remove(child)
    base = root.find(f'.//{art.S}g[@id="components-base"]')
    selected = root.find(f'.//{art.S}g[@id="components-active"]')
    if base is None or selected is None:
        raise ValueError('Base circuit SVG is missing expected editable layers')
    for group, color, highlighted in ((base,art.C['ink'],False), (selected,art.C['active'],True)):
        if highlighted and not active:
            continue
        width = 4.8 if highlighted else 3.4
        art.line(group,1240,373,1240,385,color,width)
        art.line(group,1240,429,1240,443,color,width)
        draw_dc_source(group,(1240,429),(1240,385),color,width,
                       group_id='source-edc-'+('active' if highlighted else 'base'))
        if mode == 'LE':
            art.line(group,1240,443,1240,535,color,width)
    art.math_label(base,1280,405,'E',size=20)
    headings = root.find(f'.//{art.S}g[@id="headings"]')
    if headings is not None:
        for child in list(headings):headings.remove(child)
        art.txt(headings,65,78,'RECTIFIER · '+mode+' LOAD',size=30,bold=True)
        art.txt(headings,65,118,'Opposing DC voltage source · no AC commutation overlap',size=18,color=art.C['muted'])
    legend = root.find(f'.//{art.S}g[@id="legend"]')
    if legend is not None:
        for child in list(legend):legend.remove(child)
        art.math_formula(legend,74,767,[('α','variable'),(' = ','roman'),(f'{p.alpha_deg:.1f}','roman'),('°','unit'),(' · ','roman'),('E','variable'),(' = ','roman'),(f'{p.source_voltage_pu:.2f}','roman'),(' p.u.','unit')],size=20)
        art.txt(legend,74,806,'LE: initial-value trajectory; RLE: resistive damping.',size=16,color=art.C['muted'])
    return tree
