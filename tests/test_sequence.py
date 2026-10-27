"""Validate the 12 commutation states and graph-derived conductive loops."""
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
from rectifier_model import CircuitTopology, CommutationSequence, LOWER, UPPER, PAIRS
from retificador_trifasico_inkscape import selection_from_config
from rectifier_renderer import CircuitRenderer, build_panel

EXPECTED_STATES = [
    ('T1','T6'), ('T1','T3','T6'),
    ('T3','T6'), ('T2','T3','T6'),
    ('T2','T3'), ('T2','T3','T5'),
    ('T2','T5'), ('T2','T4','T5'),
    ('T4','T5'), ('T1','T4','T5'),
    ('T1','T4'), ('T1','T4','T6'),
]
EXPECTED_SWAP = [('T1','T3'),('T6','T2'),('T3','T5'),
                 ('T2','T4'),('T5','T1'),('T4','T6')]


@pytest.fixture(scope='module')
def topology():
    return CircuitTopology()


@pytest.fixture(scope='module')
def sequence():
    return CommutationSequence(mu=15)


def test_exact_sequence(sequence):
    assert len(sequence.states) == 12
    for state, expected in zip(sequence.states, EXPECTED_STATES):
        assert tuple(sorted(state.scrs)) == tuple(sorted(expected))
        assert state.is_overlap == (state.number % 2 == 0)
        assert len(state.pairs) == (2 if state.is_overlap else 1)


def test_correct_incoming_outgoing(sequence):
    assert [(state.outgoing, state.incoming) for state in sequence.states[1::2]] == EXPECTED_SWAP
    for state in sequence.states[1::2]:
        prev_set = sequence.states[state.number-2].scrs
        next_set = sequence.states[state.number % 12].scrs
        assert prev_set | next_set == state.scrs
        assert prev_set - next_set == {state.outgoing}
        assert next_set - prev_set == {state.incoming}


def test_time_windows_and_cycle(sequence):
    for i in range(6):
        normal=sequence.states[2*i]
        overlap=sequence.states[2*i+1]
        assert normal.theta_start == 60*i + 15
        assert normal.theta_end == 60*(i+1)
        assert overlap.theta_start == 60*(i+1)
        assert overlap.theta_end == 60*(i+1) + 15
        assert normal.theta_end == overlap.theta_start
        assert overlap.theta_end - overlap.theta_start == 15
    assert sequence.states[-1].theta_end % 360 == sequence.states[0].theta_start
    assert sequence.states[-1].pairs[-1] == sequence.states[0].pairs[0]


@pytest.mark.parametrize('mu', [-5, 0, 60, 80])
def test_invalid_overlap_angles(mu):
    with pytest.raises(ValueError):
        CommutationSequence(mu)


def test_all_paths_closed_and_directional(sequence,topology):
    for state in sequence.states:
        for high,low in state.pairs:
            path=topology.current_loop(high,low)
            assert path[0].start == path[-1].end
            for a,b in zip(path,path[1:]):
                assert a.end == b.start
            scrs={walk.edge.name for walk in path if walk.edge.kind=='scr'}
            assert scrs == {UPPER[high],LOWER[low]}
            for walk in path:
                if walk.edge.kind=='scr':
                    assert walk.direction==1


def test_expected_component_count(sequence,topology):
    for state in sequence.states:
        selected=topology.highlight(state)
        assert len(selected.thyristors)==(3 if state.is_overlap else 2)
        assert len(selected.sources)==(3 if state.is_overlap else 2)
        assert len(selected.inductors)==(4 if state.is_overlap else 3)
        assert selected.resistor is True
        assert 'LDC' in selected.inductors
        assert 'POS_T5_CARGA' in selected.paths
        assert 'NEG_T6_CARGA' in selected.paths
        assert {'CARGA_POS_L','CARGA_L_R','CARGA_R_NEG'} <= selected.paths
        assert selected.paths <= art.WIRE_IDS
        assert len(set(selected.directions)) == len(selected.directions)


def test_neutral_and_summed_currents(sequence,topology):
    first=topology.highlight(sequence.state(2))
    directions=first.signed_edges()
    assert {'VA','VB','VC'}==set(first.sources)
    assert directions['FASE_A'] == 1
    assert directions['FASE_B'] == 1
    assert directions['FASE_C'] == -2
    assert directions['NEUTRO_AB'] == -1
    assert directions['NEUTRO_BC'] == -2
    assert directions['POS_T3_T5'] == 2
    assert directions['LDC'] == 2
    second=topology.highlight(sequence.state(4)).signed_edges()
    assert second['FASE_A'] == -1
    assert second['FASE_B'] == 2
    assert second['FASE_C'] == -1
    assert second['NEUTRO_AB'] == 1
    assert second['NEUTRO_BC'] == -1


def test_no_reverse_current_through_scr(topology):
    with pytest.raises(ValueError):
        topology.shortest_path('CATHODE_T1','ANODE_T1',('DC',),('T1',))
    with pytest.raises(ValueError):
        topology.shortest_path('ANODE_T3','CATHODE_T3',('DC',),('T1',))


def test_reused_geometries():
    native=art.native_scr_segments()
    assert len(native)==3
    assert len(native[1][1])==3
    assert 'CARGA_L_R' in art.LOAD_WIRES
    assert art.TOP == UPPER
    assert art.BOTTOM == LOWER


def test_backward_compatible_selection():
    config=json.loads((BASE/'configuracao_retificador.json').read_text())
    selected=selection_from_config(config)
    assert {'T1','T6'}==set(selected.thyristors)
    assert {'VA','VC'}==set(selected.sources)
    assert 'LDC' in selected.inductors
    assert len(selected.paths)==15


def test_svg_structure_and_panel(tmp_path,topology,sequence):
    renderer=CircuitRenderer(topology)
    trees=[]
    for state in sequence.states:
        tree=renderer.render(topology.highlight(state),state)
        trees.append(tree)
        filename=tmp_path/f'state{state.number:02d}.svg'
        renderer.save(tree,filename)
        root=ET.parse(filename).getroot()
        allgroups=list(root.iter(art.S+'g'))
        scrs=[g for g in allgroups if g.get('data-symbol')=='schemdraw.elements.SCR']
        assert len(scrs)==6+len(state.scrs)
        assert sum(g.get('id','').startswith('selected-t') for g in scrs)==len(state.scrs)
        assert root.get('viewBox')=='0 0 1520 850'
        assert 'font-size="65%"' not in filename.read_text()
        if state.is_overlap:
            assert 'OUT' in filename.read_text()
            assert 'IN' in filename.read_text()
    panel=build_panel(sequence.states,renderer,tmp_path/'panel.svg')
    data=panel.read_text()
    root=ET.parse(panel).getroot()
    ids=[node.get('id') for node in root.iter() if node.get('id')]
    assert len(ids)==len(set(ids)), 'Duplicate IDs in panel!'
    assert len([node for node in root.iter() if node.get('id','').startswith('panel-state-')])==12
    assert data.count('marker-end="url(#st')>0
    assert 'STIX Math' in data


def test_cli_all_modes(tmp_path):
    script=BASE/'retificador_trifasico_inkscape.py'
    def run(*args):
        return subprocess.run([sys.executable,str(script),*map(str,args)],
                              cwd=tmp_path,text=True,capture_output=True)
    all12=tmp_path/'twelve'
    r=run('--all-12','--mu','15','--output-dir',all12)
    assert r.returncode==0, r.stderr
    assert len(list(all12.glob('estado_*.svg')))==12
    assert (all12/'painel_12_estados.svg').exists()
    assert (all12/'manifest_estados.json').exists()
    r=run('--state','4','--mu','20','--output','state4.svg')
    assert r.returncode==0, r.stderr
    assert '20°' in (tmp_path/'state4.svg').read_text()
    r=run('--all','--output-dir','ideal')
    assert r.returncode==0, r.stderr
    assert len(list((tmp_path/'ideal').glob('ideal_*.svg')))==6
    r=run('--config', BASE/'configuracao_retificador.json','--output','manual.svg')
    assert r.returncode==0, r.stderr
    assert (tmp_path/'manual.svg').exists()
    r=run('--all-12','--mu','60')
    assert r.returncode!=0 and 'mu' in r.stderr
    r=run('--manual','--thyristors','T99')
    assert r.returncode!=0 and 'unknown' in r.stderr
