"""Electrical and vector-regression tests for the introductory R/RL cases."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from rectifier_loads import (LoadParameters, ResistiveLoad, ResistiveInductiveLoad,
                             ResistiveCircuitRenderer, state_at_angle, state_at_pair)

THETA=np.linspace(0,360,1801)

@pytest.mark.parametrize('alpha,fraction',[(0,0.0),(30,0.0),(75,.25),(90,.5)])
def test_R_blocking_fraction(alpha, fraction):
    w=ResistiveLoad(LoadParameters(alpha_deg=alpha)).sample(THETA)
    assert abs(np.mean(w.blocked)-fraction)<.003
    assert np.all(w.dc_i>=-1e-12)
    assert np.all(w.dc_v>=-1e-12)
    assert np.allclose(w.dc_i,w.dc_v)

@pytest.mark.parametrize('alpha', [0,30,75,90])
def test_R_load_scr_currents_and_ac_kcl(alpha):
    w=ResistiveLoad(LoadParameters(alpha_deg=alpha)).sample(THETA)
    upper=w.scr['T1']+w.scr['T3']+w.scr['T5']
    lower=w.scr['T2']+w.scr['T4']+w.scr['T6']
    assert np.allclose(upper,w.dc_i)
    assert np.allclose(lower,w.dc_i)
    assert np.allclose(np.sum(w.phase_i,axis=0),0)
    for j in np.where(w.blocked)[0]:
        assert w.dc_i[j]==0
        assert all(w.scr[t][j]==0 for t in w.scr)


def test_R_zero_current_interval_has_no_active_SCRs():
    w=ResistiveLoad(LoadParameters(alpha_deg=75)).sample(THETA)
    assert state_at_angle(w,127.5)==(None,())
    i,active=state_at_angle(w,100)
    assert active==state_at_pair(i)


def test_R_new_pair_requires_double_pulse_after_gap():
    w=ResistiveLoad(LoadParameters(alpha_deg=90)).sample(THETA)
    assert w.dc_i[np.argmin(abs(THETA-90))]>0
    assert w.dc_i[np.argmin(abs(THETA-135))]==0
    assert w.dc_i[np.argmin(abs(THETA-150))]>0


def test_dynamic_RL_holds_current_and_negative_voltage():
    params=LoadParameters(alpha_deg=75,inductance_mH=8)
    r=ResistiveLoad(params).sample(THETA)
    rl=ResistiveInductiveLoad(params).sample(THETA)
    assert np.min(rl.dc_i)>0.05
    assert np.max(rl.dc_i)-np.min(rl.dc_i) < .2
    assert (rl.dc_v < -.1).any()
    assert np.any((rl.dc_v < -.1)&(rl.dc_i > .1))
    assert (r.blocked).any()
    assert not rl.blocked.any()


def test_zero_inductance_reverts_to_pure_resistor():
    params=LoadParameters(alpha_deg=75,inductance_mH=0)
    r=ResistiveLoad(params).sample(THETA)
    rl=ResistiveInductiveLoad(params).sample(THETA)
    assert np.array_equal(r.dc_v,rl.dc_v)
    assert np.array_equal(r.dc_i,rl.dc_i)


@pytest.mark.parametrize('bad',[-1,120,175])
def test_invalid_firing_angle_rejected(bad):
    with pytest.raises(ValueError):LoadParameters(alpha_deg=bad)


def test_R_circuit_has_no_reactors_or_inductor_annotation():
    p=LoadParameters(alpha_deg=75)
    doc=ResistiveCircuitRenderer().render(p,100,0)
    svg=ET.tostring(doc.getroot(),encoding='unicode')
    assert 'base-ldc' not in svg and 'selected-ldc' not in svg
    for name in ('la','lb','lc'):
        assert 'base-'+name not in svg
    assert 'schemdraw.elements.SCR' in svg
    assert 'selected-t1' in svg and 'selected-t6' in svg
    no_current=ET.tostring(ResistiveCircuitRenderer().render(p,127.5,None).getroot(),encoding='unicode')
    assert 'selected-t1' not in no_current
    assert 'ALL SCRs OFF' in no_current


def test_RL_circuit_preserves_dc_reactor_but_no_ac_reactors():
    doc=ResistiveCircuitRenderer().render(LoadParameters(),105,0,'RL')
    svg=ET.tostring(doc.getroot(),encoding='unicode')
    assert 'base-ldc' in svg and 'selected-ldc' in svg
    assert 'base-la' not in svg
    assert 'schemdraw.elements.SCR' in svg


def test_math_symbol_and_units_styles_are_well_formed():
    root=ResistiveCircuitRenderer().render(LoadParameters(alpha_deg=75),100,0).getroot()
    labels=[e for e in root.iter() if e.tag.endswith('text')]
    assert any(e.text=='R' and e.get('font-style')=='italic' for e in labels)
    assert any(e.text=='α' and e.get('font-style')=='italic' for e in root.iter() if e.tag.endswith('tspan'))
