"""Electrical and SVG regression tests for the entire HVDC circuit."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from hvdc_link_model import CombinedSchedule, HVDCLinkTopology, LinkSettings
from hvdc_link_renderer import HVDCLinkRenderer, SECONDARY_NEUTRAL
from hvdc_link import main


@pytest.fixture
def settings() -> LinkSettings:
    return LinkSettings()


@pytest.fixture
def schedule(settings: LinkSettings) -> CombinedSchedule:
    return CombinedSchedule(settings)


@pytest.fixture
def topology() -> HVDCLinkTopology:
    return HVDCLinkTopology()


def test_24_joint_intervals_at_thirty_degrees(schedule: CombinedSchedule) -> None:
    assert len(schedule.intervals) == 24
    assert schedule.intervals[0].theta_start == 0
    assert schedule.intervals[-1].theta_end == 360
    assert all(a.theta_end == b.theta_start
               for a, b in zip(schedule.intervals, schedule.intervals[1:]))
    assert sum(s.theta_end-s.theta_start for s in schedule.intervals) == 360
    assert len({s.rectifier.number for s in schedule.intervals}) == 12
    assert len({s.inverter.number for s in schedule.intervals}) == 12


def test_specific_phase_shifted_states(schedule: CombinedSchedule) -> None:
    assert (schedule.at(7).rectifier.number, schedule.at(7).inverter.number) == (12, 11)
    assert (schedule.at(25).rectifier.number, schedule.at(25).inverter.number) == (1, 11)
    assert (schedule.at(36).rectifier.number, schedule.at(36).inverter.number) == (1, 12)
    assert (schedule.at(54).rectifier.number, schedule.at(54).inverter.number) == (1, 1)
    assert (schedule.at(66).rectifier.number, schedule.at(66).inverter.number) == (2, 1)


def test_bridge_diodes_cannot_reverse(topology: HVDCLinkTopology) -> None:
    thyristors = [e for e in topology.edges.values() if e.kind == 'scr']
    assert len(thyristors) == 12
    assert all(e.forward_only for e in thyristors)
    assert len([e for e in thyristors if e.id.startswith('R_')]) == 6
    assert len([e for e in thyristors if e.id.startswith('I_')]) == 6
    assert topology.edges['R_T1'].src == 'R_A'
    assert topology.edges['R_T1'].dst == 'R_DC_POS'
    assert topology.edges['I_T1'].src == 'I_DC_POS'
    assert topology.edges['I_T1'].dst == 'I_A'
    assert topology.edges['METALLIC_RETURN'].src == 'I_DC_NEG'
    assert topology.edges['METALLIC_RETURN'].dst == 'R_DC_NEG'


def test_all_complete_current_loops_are_contiguous(schedule: CombinedSchedule,
                                                    topology: HVDCLinkTopology) -> None:
    for state in schedule.intervals:
        h = topology.highlight(state)
        assert len(h['loops']) == (1 + int(state.rectifier_overlap)) * (1 + int(state.inverter_overlap))
        for loop in h['loops']:
            assert loop[0].start == loop[-1].end
            assert all(a.end == b.start for a, b in zip(loop, loop[1:]))
            assert {w.edge.id for w in loop if w.edge.kind == 'scr'} <= h['scrs']
            assert len([w for w in loop if w.edge.kind == 'scr']) == 4
            assert all(w.orientation == 1 for w in loop if w.edge.forward_only)
            assert {'L_DR','R_LINE','L_DI','METALLIC_RETURN'} <= {w.edge.id for w in loop}


def test_all_states_expected_active_scr_counts(schedule: CombinedSchedule,
                                               topology: HVDCLinkTopology) -> None:
    for state in schedule.intervals:
        h=topology.highlight(state)
        assert len(h['scrs']) == 4+int(state.rectifier_overlap)+int(state.inverter_overlap)
        assert {eid for eid in h['scrs'] if eid.startswith('R_')} == {
            'R_'+s for s in state.rectifier.scrs}
        assert {eid for eid in h['scrs'] if eid.startswith('I_')} == {
            'I_'+s for s in state.inverter.scrs}


def test_every_dc_loop_uses_only_secondary_winding_edges(topology: HVDCLinkTopology) -> None:
    assert all('primary' not in e.kind for e in topology.edges.values())
    assert len([e for e in topology.edges.values() if e.kind == 'transformer_secondary']) == 6
    loop=topology.conduction_loop(('a','c'),('a','b'))
    assert len([w for w in loop if w.edge.kind == 'transformer_secondary']) == 4
    assert not any('EARTH' in w.edge.id.upper() for w in loop)


def test_gamma_and_alpha_rules(settings: LinkSettings) -> None:
    assert settings.gamma == pytest.approx(20)
    with pytest.raises(ValueError,match='minimum'):
        replace(settings,alpha_inverter=156)
    with pytest.raises(ValueError,match='Rectifier delay'):
        replace(settings,alpha_rectifier=91)
    with pytest.raises(ValueError,match='Inverter delay'):
        replace(settings,alpha_inverter=88)
    with pytest.raises(ValueError,match='Overlap'):
        replace(settings,mu_inverter=60)
    with pytest.raises(ValueError,match='offset'):
        replace(settings,ac_phase_offset=360)
    with pytest.raises(ValueError,match='finite'):
        replace(settings,alpha_rectifier=float('nan'))


def test_overlapping_station_commutations_generate_four_loops(settings: LinkSettings,
                                                              topology: HVDCLinkTopology) -> None:
    schedule=CombinedSchedule(replace(settings,ac_phase_offset=6.0))
    simultaneous=[s for s in schedule.intervals if s.rectifier_overlap and s.inverter_overlap]
    assert simultaneous
    for state in simultaneous:
        h=topology.highlight(state)
        assert len(h['loops'])==4
        assert len(h['scrs'])==6


def test_zero_offset_is_supported(settings: LinkSettings,topology: HVDCLinkTopology) -> None:
    schedule=CombinedSchedule(replace(settings,ac_phase_offset=0))
    assert schedule.intervals
    for state in schedule.intervals:
        topology.highlight(state)


def test_angular_wrap_is_cyclic(schedule: CombinedSchedule) -> None:
    assert schedule.at(0)==schedule.at(360)
    assert schedule.at(-1)==schedule.at(359)
    assert schedule.at(720)==schedule.at(0)


def test_editor_svg_contains_graph_nodes(settings: LinkSettings,
                                         schedule: CombinedSchedule,
                                         topology: HVDCLinkTopology) -> None:
    renderer=HVDCLinkRenderer(settings,topology)
    state=schedule.at(65)
    root=renderer.render(state).getroot()
    text=ET.tostring(root,encoding='unicode')
    assert '<svg' in text or '<ns0:svg' in text
    assert 'inkscape' in text
    assert 'schemdraw.elements.SCR' in text
    assert 'GALVANIC' not in text.upper() or 'isolated' in text
    assert 'metallic return' in text.lower()
    edge_ids={e.get('data-edge-id') for e in root.iter() if e.get('data-edge-id')}
    assert {f'R_TR_{p}' for p in 'ABC'} <= edge_ids
    assert {'L_DR','L_DI','R_LINE','METALLIC_RETURN'} <= edge_ids
    valve_ids={e.get('data-scr') for e in root.iter() if e.get('data-scr')}
    assert len(valve_ids)==12
    selected={e.get('data-scr') for e in root.iter()
              if e.get('data-scr') and e.get('data-active')=='true'}
    assert selected==topology.highlight(state)['scrs']
    assert SECONDARY_NEUTRAL['I']>3107


def test_manifest_and_cli_generate_all_24(tmp_path: Path) -> None:
    output=tmp_path/'full'
    main(['--all','--output-dir',str(output)])
    files=list(output.glob('hvdc_joint_state_*.svg'))
    assert len(files)==24
    assert (output/'hvdc_normal.svg').exists()
    assert (output/'hvdc_rectifier_overlap.svg').exists()
    assert (output/'hvdc_inverter_overlap.svg').exists()
    assert (output/'hvdc_timeline.svg').exists()
    doc=json.loads((output/'hvdc_states.json').read_text())
    assert len(doc['states'])==24
    assert all(e['path_count'] in (1,2,4) for e in doc['states'])
    assert (output/'hvdc_states.csv').exists()


def test_cli_selects_angle_and_checks_invalid_parameters(tmp_path: Path) -> None:
    output=tmp_path/'one'
    main(['--theta','66','--output-dir',str(output)])
    assert len(list(output.glob('hvdc_joint_state_*.svg')))==1
    with pytest.raises(SystemExit):
        main(['--gamma-i','5','--gamma-min','10','--output-dir',str(output)])
    with pytest.raises(SystemExit):
        main(['--state','999','--output-dir',str(output)])


def test_all_with_same_phase_reference(tmp_path: Path) -> None:
    main(['--phase-offset','0','--output-dir',str(tmp_path/'zero')])
    assert (tmp_path/'zero'/'hvdc_states.json').exists()
    doc=json.loads((tmp_path/'zero'/'hvdc_states.json').read_text())
    assert len(doc['states'])>0
