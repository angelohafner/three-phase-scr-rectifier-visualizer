"""Physical and graphical regression tests for R, RL, LE, RLE and SCR voltages."""
from __future__ import annotations

from dataclasses import replace
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from lcc_advanced_loads import (
    AdvancedLoadParameters, VoltageSourceLoad, valve_voltages,
    render_voltage_source_circuit,
)
from rectifier_loads import LoadParameters, ResistiveLoad, ResistiveInductiveLoad

THETA = np.linspace(0,360,1441)


@pytest.mark.parametrize('mode',['LE','RLE'])
def test_source_load_conduction_and_kcl(mode):
    curves=VoltageSourceLoad(AdvancedLoadParameters(),mode).sample(THETA)
    assert np.all(np.isfinite(curves.dc_i))
    assert (curves.dc_i>=0).all()
    assert np.allclose(curves.scr['T1']+curves.scr['T3']+curves.scr['T5'],curves.dc_i)
    assert np.allclose(curves.scr['T2']+curves.scr['T4']+curves.scr['T6'],curves.dc_i)
    assert np.allclose(curves.phase_i.sum(axis=0),0)
    assert (curves.dc_v<0).any()


def test_opposing_source_reduces_rle_current():
    parameters=AdvancedLoadParameters()
    low=VoltageSourceLoad(replace(parameters,source_voltage_pu=.05),'RLE').sample(THETA)
    high=VoltageSourceLoad(replace(parameters,source_voltage_pu=.75),'RLE').sample(THETA)
    assert np.mean(low.dc_i)>np.mean(high.dc_i)


def test_le_initial_condition_is_not_fictitious_periodic_steady_state():
    p=AdvancedLoadParameters(source_voltage_pu=.1,initial_current_pu=.3)
    w=VoltageSourceLoad(p,'LE').sample(THETA)
    assert abs(w.dc_i[-1]-w.dc_i[0])>.01


def test_valve_voltages_from_node_potentials_and_floating_state():
    p=AdvancedLoadParameters(source_voltage_pu=.9)
    w=VoltageSourceLoad(p,'RLE').sample(THETA)
    volts=valve_voltages(w.phase,w.conducting_pair)
    blocked=w.conducting_pair<0
    assert blocked.any()
    assert all(np.isnan(volts[t][blocked]).all() for t in volts)
    for pair,t in enumerate(['T1','T3','T3','T5','T5','T1']):
        j=np.where(w.conducting_pair==pair)[0]
        if len(j):assert np.allclose(volts[t][j],0)


def test_inverter_valve_voltage_polarties_reversed():
    r=np.zeros(12,dtype=int)
    phase=np.array([np.full(12,1.0),np.full(12,.1),np.full(12,-.6)])
    rect=valve_voltages(phase,r,'rectifier')
    inv=valve_voltages(phase,r,'inverter')
    for t in rect:assert np.allclose(rect[t],-inv[t])
    assert np.allclose(rect['T1'],0)
    assert np.allclose(rect['T6'],0)


@pytest.mark.parametrize('mode',['LE','RLE'])
def test_vector_figures_are_editable_and_show_opposing_source(mode):
    tree=render_voltage_source_circuit(AdvancedLoadParameters(),100,0,mode)
    root=tree.getroot()
    svg=ET.tostring(root,encoding='unicode')
    assert '<' in svg and 'selected-t1' in svg
    assert 'RECTIFIER' in svg and 'E' in svg
    assert 'schemdraw.elements.SCR' in svg
    assert 'font-style="italic"' in svg


def test_advanced_model_rejects_negative_source_or_initial_current():
    for field in ('source_voltage_pu','initial_current_pu'):
        with pytest.raises(ValueError): AdvancedLoadParameters(**{field:-.1})


def test_no_fictitious_negative_current_in_the_four_load_models():
    p=LoadParameters()
    curves=[ResistiveLoad(p).sample(THETA),ResistiveInductiveLoad(p).sample(THETA)]
    q=AdvancedLoadParameters()
    curves.extend([VoltageSourceLoad(q,m).sample(THETA) for m in ('LE','RLE')])
    for curve in curves:assert curve.dc_i.min()>=0
