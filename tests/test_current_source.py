"""Electrical and schematic regression tests for constant DC current in LCC bridges."""
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pytest

from current_source_model import (CurrentSourceSettings, sample, full_cycle,
                                  overlap_degrees, transfer_fraction)
from current_source_figures import circuit

PROJECT=Path(__file__).resolve().parents[1]


def test_six_pulse_normal_and_overlap_states():
    settings=CurrentSourceSettings(mu_deg=15)
    assert sample(30,settings)['state']==1
    assert sample(62,settings)['state']==2
    assert sample(90,settings)['state']==3
    assert sample(125,settings)['state']==4
    assert sample(182,settings)['state']==6
    assert sample(0,settings)['state']==12


@pytest.mark.parametrize('mode',('manual','calculated'))
@pytest.mark.parametrize('theta',np.arange(0,360,2.5))
def test_valve_group_current_conservation_and_ac_kcl(theta,mode):
    cfg=CurrentSourceSettings(idc_pu=.8,overlap_mode=mode)
    point=sample(theta,cfg)
    val=point['scr']
    assert sum(val[t] for t in ('T1','T3','T5'))==pytest.approx(cfg.idc_pu,abs=1e-10)
    assert sum(val[t] for t in ('T2','T4','T6'))==pytest.approx(cfg.idc_pu,abs=1e-10)
    assert min(val.values())>=0
    assert abs(sum(point['ac']))<1e-10
    assert point['idc']==cfg.idc_pu
    if point['overlap']:
        out,enter,stay=point['outgoing'],point['incoming'],point['stationary']
        assert all([out,enter,stay])
        assert val[out]+val[enter]==pytest.approx(cfg.idc_pu,abs=1e-10)
        assert val[stay]==pytest.approx(cfg.idc_pu,abs=1e-10)


def test_first_upper_commutation_identity():
    point=sample(68,CurrentSourceSettings(mu_deg=12))
    assert point['outgoing']=='T1'
    assert point['incoming']=='T3'
    assert point['stationary']=='T6'
    assert point['scr']['T1']==pytest.approx(1/3)
    assert point['scr']['T3']==pytest.approx(2/3)
    assert point['scr']['T6']==pytest.approx(1)


def test_computed_overlap_increases_with_current_and_ac_inductance():
    base=CurrentSourceSettings(overlap_mode='calculated')
    mu0=overlap_degrees(base)
    mu1=overlap_degrees(CurrentSourceSettings(overlap_mode='calculated',idc_pu=1.3))
    mu2=overlap_degrees(CurrentSourceSettings(overlap_mode='calculated',commutation_inductance_mH=.28))
    assert 0<mu0<mu1<60
    assert mu0<mu2<60
    assert transfer_fraction(mu0,base,mu0)==1
    assert transfer_fraction(0,base,mu0)==0
    omega=2*math.pi*base.frequency_hz
    lhs=base.idc_pu
    rhs=(math.sqrt(3)*base.voltage_phase_peak_pu /
         (2*omega*base.commutation_inductance_mH/1000) *
         (math.cos(math.radians(base.alpha_deg))-
          math.cos(math.radians(base.alpha_deg+mu0))))
    assert lhs==pytest.approx(rhs,rel=1e-10)


def test_physically_impossible_current_is_not_faked():
    with pytest.raises(ValueError,match='60-degree sector|No possible'):
        overlap_degrees(CurrentSourceSettings(overlap_mode='calculated',
                                              idc_pu=3,commutation_inductance_mH=.80))


def test_zero_overlap_only_two_scrs_are_active():
    p=sample(65,CurrentSourceSettings(mu_deg=0))
    assert not p['overlap']
    assert len([x for x in p['scr'].values() if x>0])==2


def test_cycle_samples_are_all_finite_and_have_constant_current():
    data=full_cycle(CurrentSourceSettings())
    assert data['angle'].size==1441
    assert np.all(np.isfinite(data['dc']))
    assert np.allclose(data['idc'],1)
    assert len(data['scr'])==6


@pytest.mark.parametrize('side',('rectifier','inverter'))
def test_current_source_schematic_keeps_ac_sources_and_removes_rle(side):
    path=PROJECT/'output_lcc'/side/'estado_02.svg'
    new=circuit(path,inverter=side=='inverter').getroot()
    from xml.etree import ElementTree as ET
    g=ET.tostring(new,encoding='unicode')
    assert 'schemdraw.elements.SourceI' in g
    assert 'schemdraw.elements.SourceSin' in g
    assert 'schemdraw.elements.Inductor' in g  # AC reactors remain.
    assert 'symbol-base-r' not in g
    assert 'symbol-base-ldc' not in g
    assert 'data-terminal-start=' in g
    assert 'current-source-active' in g


@pytest.mark.parametrize('side',('rectifier','inverter'))
def test_native_symbols_have_matching_graphical_terminal_positions(side):
    from lxml import etree
    path=PROJECT/'output_lcc'/'current_source'/side/'circuits'/'estado_02.svg'
    root=etree.parse(str(path))
    ns={'s':'http://www.w3.org/2000/svg'}
    comps=root.xpath('//*[@data-symbol="schemdraw.elements.SourceI"]')
    assert len(comps)==2
    for el in comps:
        assert el.attrib.get('data-terminal-start')
        assert el.attrib.get('data-terminal-end')
        assert el.xpath('./s:circle',namespaces=ns)
        assert el.xpath('./s:polygon',namespaces=ns)
