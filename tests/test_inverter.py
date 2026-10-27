"""Validate inverter current direction, SCR polarity, angles and gallery output."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import rectifier_art as art
from lcc_converter import InverterOperatingPoint, renderer_for, generate_stage
from rectifier_model import CircuitTopology, CommutationSequence, LOWER, UPPER
from rectifier_renderer import CircuitRenderer


@pytest.mark.parametrize('angle,mu,gamma', [(145,15,20),(130,20,30),(155,10,15)])
def test_angle_relationship(angle,mu,gamma):
    point=InverterOperatingPoint(alpha=angle,mu=mu,gamma_min=10)
    assert point.gamma == pytest.approx(gamma)
    assert point.alpha + point.mu + point.gamma == pytest.approx(180)


@pytest.mark.parametrize('a,mu,m', [(95,60,10),(80,15,10),(150,25,10),
                                   (170,15,1), (145,15,25), (145,15,-2)])
def test_invalid_inverter_operating_points(a,mu,m):
    with pytest.raises(ValueError):
        InverterOperatingPoint(alpha=a,mu=mu,gamma_min=m)


def test_inverter_currents_flow_from_dc_into_ac():
    rectifier=CircuitTopology('rectifier')
    inverter=CircuitTopology('inverter')
    states=CommutationSequence(15).states
    for state in states:
        iv=inverter.highlight(state)
        rv=rectifier.highlight(state)
        assert iv.thyristors == rv.thyristors
        assert iv.sources == rv.sources
        assert iv.paths == rv.paths
        assert iv.resistor is False
        assert iv.dc_source is True
        assert 'EDC' in inverter.edges
        assert 'R' not in inverter.edges
        assert iv.signed_edges()['EDC'] == -(1 if not state.is_overlap else 2)
        for edge in ('CARGA_POS_L','CARGA_L_R','CARGA_R_NEG',
                     'POS_T5_CARGA','NEG_T6_CARGA'):
            assert iv.signed_edges()[edge] == -rv.signed_edges()[edge]
        for high,low in state.pairs:
            loop=inverter.current_loop(high,low)
            assert loop[0].start == 'POS_LOAD'
            assert loop[-1].end == 'POS_LOAD'
            assert {w.edge.name for w in loop if w.edge.kind=='scr'}=={UPPER[high],LOWER[low]}
            assert all(w.direction==1 for w in loop if w.edge.kind=='scr')


def test_two_modes_require_different_scr_orientation(tmp_path):
    state=CommutationSequence(15).state(2)
    point=InverterOperatingPoint()
    rendered=[]
    for operation in ('rectifier','inverter'):
        r=renderer_for(operation,point)
        filename=tmp_path/f'{operation}.svg'
        r.save(r.render(r.topology.highlight(state),state),filename)
        data=filename.read_text()
        root=ET.parse(filename).getroot()
        groups={g.get('id'):g for g in root.iter(art.S+'g') if g.get('id')}
        rect=groups['base-t1']
        # The first polygon must have its tip at a different vertical endpoint.
        polygon=next(rect.iter(art.S+'polygon'))
        pts=[tuple(map(float,p.split(','))) for p in polygon.get('points').split()]
        rendered.append(pts)
        if operation=='inverter':
            assert 'E_dc' not in data  # Native mathematical tspan is used instead.
            assert 'selected-edc' in data
            assert 'selected-r' not in data
            visible=''.join(root.itertext())
            assert 'α = 145°' in visible
            assert 'γ = 20°' in visible
        else:
            assert 'selected-r' in data
            assert 'selected-edc' not in data
    assert rendered[0] != rendered[1]


def test_generated_inverter_gallery(tmp_path):
    point=InverterOperatingPoint()
    renderer, sequence=generate_stage('inverter',tmp_path,point)
    assert len(list(tmp_path.glob('estado_*.svg'))) == 12
    assert (tmp_path/'painel_12_estados.svg').exists()
    manifest=json.loads((tmp_path/'manifest_estados.json').read_text())
    assert manifest['operation']=='inverter'
    assert manifest['dc_element']=='EDC'
    assert manifest['gamma_deg']==20
    assert len(manifest['states'])==12
    assert all(s['file'].endswith('.svg') for s in manifest['states'])
    assert 'SIX-PULSE SCR INVERTER' in (tmp_path/'painel_12_estados.svg').read_text()


def test_cli_modes(tmp_path):
    script=BASE/'lcc_converter.py'
    def run(*args):
        return subprocess.run([sys.executable,str(script),*map(str,args)],
                              cwd=tmp_path,encoding='utf-8',capture_output=True)
    valid=run('--side','inverter','--state','2','--alpha','145','--mu','15',
              '--output-dir','inv')
    assert valid.returncode==0, valid.stderr
    assert (tmp_path/'inv/estado_02.svg').exists()
    gamma=run('--side','inverter','--state','1','--gamma','20','--mu','15','--output-dir','g')
    assert gamma.returncode==0, gamma.stderr
    assert 'α = 145°' in ''.join(ET.parse(tmp_path/'g/estado_01.svg').getroot().itertext())
    bad=run('--side','inverter','--state','2','--alpha','155','--mu','20')
    assert bad.returncode!=0 and 'gamma' in bad.stderr.lower()
    both=run('--side','both','--state','2','--output-dir','both')
    assert both.returncode==0, both.stderr
    assert (tmp_path/'both/lcc_two_stage_overview.svg').exists()
