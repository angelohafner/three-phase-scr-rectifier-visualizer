"""Electrical and vector regression tests for the half-wave SCR chapter."""
from __future__ import annotations
import json
import math
import subprocess
from pathlib import Path

import pytest
from halfwave_model import HalfWaveModel, HalfWaveSettings
from halfwave_figures import circuit_svg


@pytest.mark.parametrize('alpha',[0,30,65,90,150])
def test_pure_r_extinguishes_at_source_zero(alpha):
    m=HalfWaveModel(HalfWaveSettings(load='R',alpha_deg=alpha))
    assert m.beta_deg==180
    assert m.sample(181).i_A==0
    assert m.sample(181).vak_V<0
    for angle in (alpha+5,(alpha+180)/2,179.99):
        p=m.sample(angle)
        assert p.i_A==pytest.approx(p.vs_V/m.R,abs=1e-9)
        assert p.vak_V==0
    assert m.sample((alpha+180)/2).conducting


def test_rl_keeps_scr_on_beyond_voltage_zero_and_extinguishes_naturally():
    m=HalfWaveModel(HalfWaveSettings(load='RL',alpha_deg=50,resistance_ohm=12,inductance_mH=70))
    assert 225<m.beta_deg<280
    p=m.sample(205)
    assert p.vs_V<0<p.i_A
    assert p.vo_V<0
    assert p.vak_V==0
    assert p.vr_V>0
    assert p.vl_V==pytest.approx(p.vs_V-p.vr_V,abs=1e-12)
    assert m.sample(m.beta_deg-.2).i_A>0
    assert m.sample(m.beta_deg+.2).i_A==0
    assert m.sample(m.beta_deg+.2).vak_V<0
    assert m.sample(180).energy_J>0


def test_inductance_increases_beta_and_r_is_independent_of_inductor():
    def beta(l):return HalfWaveModel(HalfWaveSettings(inductance_mH=l)).beta_deg
    assert beta(5)<beta(35)<beta(100)
    assert HalfWaveModel(HalfWaveSettings(load='R',inductance_mH=99)).beta_deg==180


def test_load_energy_balance_over_full_conduction_interval():
    m=HalfWaveModel(HalfWaveSettings())
    series=m.series(.25)
    dt=math.radians(.25)/m.omega
    win=sum(p.vo_V*p.i_A*dt for p in series)
    wr=sum(m.R*p.i_A**2*dt for p in series)
    assert wr==pytest.approx(win,rel=.009)
    assert m.sample(360).i_A==0


def test_svg_uses_real_scr_geometry_and_complete_series_loop():
    from xml.etree import ElementTree as ET
    for load in ('R','RL'):
        for on in (True,False):
            tree=circuit_svg(load,on)
            svg=ET.tostring(tree.getroot(),encoding='unicode')
            assert 'schemdraw.elements.SCR' in svg
            assert 'source-ac' in svg and 'load-resistor' in svg
            assert ('load-inductor' in svg)==(load=='RL')
            assert ('current-path' in svg)==on
            assert 'text' in svg and 'tspan' in svg


def test_javascript_model_matches_python_when_node_is_available():
    root=Path(__file__).resolve().parents[1]
    js=root/'presentation/src/halfwave.js'
    code=js.read_text()+'''\nconsole.log(JSON.stringify(['R','RL'].map(load=>{
      const m=HalfWave.model({load,alpha:50,R:12,L:70,V:120,f:60});
      return {load,beta:m.beta,points:[55,90,180,205,240,300].map(a=>m.at(a))};
    })));'''
    try:
        completed=subprocess.run(['node','-e',code],check=True,capture_output=True,text=True,timeout=12)
    except FileNotFoundError:
        pytest.skip('Node.js is not installed')
    cases=json.loads(completed.stdout)
    for case in cases:
        m=HalfWaveModel(HalfWaveSettings(load=case['load']))
        assert case['beta']==pytest.approx(m.beta_deg,abs=1e-9)
        for angle,p in zip((55,90,180,205,240,300),case['points']):
            q=m.sample(angle)
            assert p['i']==pytest.approx(q.i_A,abs=1e-8)
            assert p['vo']==pytest.approx(q.vo_V,abs=1e-8)
            assert p['vak']==pytest.approx(q.vak_V,abs=1e-8)
            assert p['w']==pytest.approx(q.energy_J,abs=1e-8)


def test_halfwave_is_in_standalone_html():
    html=Path(__file__).resolve().parents[1]/'dist/lcc_hvdc_interactive.html'
    assert html.exists()
    text=html.read_text(encoding='utf-8')
    assert 'Why Does the SCR Remain ON After 180°?' in text
    assert 'halfwave_figures' in text
    assert 'function renderFundamentalsSlide' in text
    assert 'function scheduleStateAngleRefresh' in text
    assert 'http://fonts.googleapis.com' not in text
