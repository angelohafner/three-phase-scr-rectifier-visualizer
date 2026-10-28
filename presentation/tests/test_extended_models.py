"""Regression and physical-consistency tests for four educational DC loads."""
from __future__ import annotations
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from rectifier_load_extended import DCLoad, sample, valve_voltages


def test_six_scr_voltages_follow_electrical_nodes():
    phase=np.array([1.0,-0.5,-0.5])
    v=valve_voltages(phase,0)
    assert v['T1']==pytest.approx(0.0)
    assert v['T6']==pytest.approx(0.0)
    assert v['T3']==pytest.approx(-1.5)
    assert v['T2']==pytest.approx(-1.5)
    assert all(math.isnan(x) for x in valve_voltages(phase,-1).values())


@pytest.mark.parametrize('mode',['R','RL','LE','RLE'])
def test_loads_are_well_formed(mode):
    trace=sample(DCLoad(kind=mode,alpha_deg=70,emf_pu=-0.4))
    assert len(trace.theta)==1441
    assert np.isfinite(trace.current).all()
    assert np.all(trace.current>=0)
    assert set(trace.scr_voltage)=={'T1','T2','T3','T4','T5','T6'}
    for j in range(len(trace.theta)):
        idx=int(trace.pair[j])
        if idx<0:
            assert all(math.isnan(float(trace.scr_voltage[n][j])) for n in trace.scr_voltage)
        else:
            from rectifier_load_extended import SCRS
            assert all(abs(float(trace.scr_voltage[n][j]))<1e-7 for n in SCRS[idx])


def test_rl_and_rle_agree_when_emf_zero():
    a=sample(DCLoad(kind='RL',alpha_deg=45))
    b=sample(DCLoad(kind='RLE',alpha_deg=45,emf_pu=0))
    np.testing.assert_allclose(a.current,b.current,atol=1e-12)
    np.testing.assert_array_equal(a.pair,b.pair)


def test_inversion_requires_sustained_current_and_negative_bridge_power():
    trace=sample(DCLoad(kind='RLE',alpha_deg=110,resistance_ohm=.5,
                        inductance_mH=18,emf_pu=-1.0))
    assert trace.periodic
    assert trace.current.mean()>0.2
    assert np.mean(trace.voltage * trace.current)<-0.05


def test_undamped_le_does_not_claim_unique_steady_state():
    trace=sample(DCLoad(kind='LE',emf_pu=-.5))
    assert not trace.periodic
    assert 'no unique' in trace.details


def test_invalid_parameter_rejected():
    with pytest.raises(ValueError):
        DCLoad(kind='RLE',resistance_ohm=0)
    with pytest.raises(ValueError):
        DCLoad(kind='LE',inductance_mH=0)
