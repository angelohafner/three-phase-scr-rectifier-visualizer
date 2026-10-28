"""Physics-oriented and SVG-synchronization regression tests for LCC waveforms."""
from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET
import numpy as np
import pytest

from lcc_waveform_model import (CommutationCurrentModel, LCCWaveformModel,
                                SCR_ID, WaveformConfig, WaveformValidator,
                                station_state_windows, verify_joint_sync)
from hvdc_link_model import CombinedSchedule, LinkSettings
from rectifier_model import CommutationSequence

ROOT=Path(__file__).resolve().parents[1]
MODEL=LCCWaveformModel()


@pytest.mark.parametrize('side,alpha,mu',[('rectifier',15,15),('inverter',145,15)])
def test_kcl_and_dc_current_at_every_sample(side,alpha,mu):
    """Upper- and lower-group currents separately equal I_dc at every sample."""
    model=LCCWaveformModel(WaveformConfig(dc_current=1.25))
    c=model.station(side,alpha=alpha,mu=mu)
    WaveformValidator.validate_station(c,1.25)
    assert np.allclose(c.phase_v[0]+c.phase_v[1]+c.phase_v[2],0,atol=1e-12)
    assert np.allclose(c.line_v[0]+c.line_v[1]+c.line_v[2],0,atol=1e-12)


@pytest.mark.parametrize('side,alpha',[('rectifier',15),('inverter',145)])
@pytest.mark.parametrize('state_id',range(1,13))
def test_standalone_states_match_the_diagrams(side,alpha,state_id):
    """Midpoint SCR currents and original twelve-state schedule must agree."""
    c=MODEL.station(side,alpha=alpha,mu=15)
    for lo,hi in station_state_windows(state_id,15):
        WaveformValidator.verify_interval(c,state_id,lo,hi)


@pytest.mark.parametrize('joint_index',range(24))
def test_hvdc_joint_states_match_both_stations(joint_index):
    """Joint sheet interval agrees with both original 12-state schedules."""
    schedule=CombinedSchedule(LinkSettings())
    st=schedule.intervals[joint_index]
    r=MODEL.station('rectifier',alpha=15,mu=12)
    i=MODEL.station('inverter',alpha=145,mu=15,offset=30,gamma_min=10)
    WaveformValidator.verify_interval(r,st.rectifier.number,st.theta_start,st.theta_end)
    WaveformValidator.verify_interval(i,st.inverter.number,st.theta_start,st.theta_end)


def test_every_hvdc_joint_interval_is_covered():
    settings=LinkSettings()
    schedule=CombinedSchedule(settings)
    r=MODEL.station('rectifier',alpha=settings.alpha_rectifier,mu=settings.mu_rectifier)
    i=MODEL.station('inverter',alpha=settings.alpha_inverter,mu=settings.mu_inverter,
                    offset=settings.ac_phase_offset)
    verify_joint_sync(schedule,r,i)
    assert sum(s.theta_end-s.theta_start for s in schedule.intervals)==pytest.approx(360)


def test_current_transfer_linear_and_stationary_valve_stable():
    c=MODEL.station('rectifier',alpha=15,mu=15,theta=np.array([60,63.75,67.5,71.25,75]))
    np.testing.assert_allclose(c.scr_i[SCR_ID['T1']], [1,.75,.5,.25,0])
    np.testing.assert_allclose(c.scr_i[SCR_ID['T3']], [0,.25,.5,.75,1])
    np.testing.assert_allclose(c.scr_i[SCR_ID['T6']], [1,1,1,1,1])
    assert c.state_numbers.tolist()==[2,2,2,2,3]


def test_source_sign_conventions_are_explicit_and_power_direction_is_correct():
    r=MODEL.station('rectifier',alpha=15,mu=15)
    i=MODEL.station('inverter',alpha=145,mu=15)
    # Positive grid -> rectifier means the AC source delivers electrical power.
    pr=(r.phase_v*r.ac_i).sum(axis=0)
    pi=(i.phase_v*i.ac_i).sum(axis=0)
    assert pr.mean()>0
    assert pi.mean()<0
    assert r.dc_v_overlap.mean()>0 and i.dc_v_overlap.mean()>0
    assert i.gamma==pytest.approx(20)


@pytest.mark.parametrize('alpha,mu',[(170,15),(155,30),(180,5)])
def test_invalid_extinction_margin_is_rejected(alpha,mu):
    with pytest.raises(ValueError):
        MODEL.station('inverter',alpha=alpha,mu=mu,gamma_min=10)


def test_three_phase_source_phase_sequence_and_phasor_spacing():
    c=MODEL.station('rectifier',alpha=0,mu=15,theta=np.array([30.,90.,150.]))
    assert c.phase_v[0,0]>c.phase_v[1,0]>c.phase_v[2,0]
    assert c.phase_v[1,1]>c.phase_v[0,1]>c.phase_v[2,1]
    assert c.phase_v[1,2]>c.phase_v[2,2]>c.phase_v[0,2]


def test_wrap_state_12_is_consistent():
    c=MODEL.station('rectifier',alpha=15,mu=15)
    windows=station_state_windows(12,15)
    assert windows==((0.,15.),)
    WaveformValidator.verify_interval(c,12,*windows[0])


def test_config_disallows_nonpositive_current_or_source():
    with pytest.raises(ValueError): WaveformConfig(dc_current=0)
    with pytest.raises(ValueError): WaveformConfig(ac_peak=-2)
    with pytest.raises(ValueError): WaveformConfig(samples=10)


def test_all_48_files_and_manifests_exist_and_are_linked():
    for side,count in [('output_lcc/rectifier',12),('output_lcc/inverter',12),
                       ('output_hvdc',24)]:
        base=ROOT/side
        manifest=json.loads((base/'waveforms/manifest_waveforms.json').read_text())
        assert len(manifest['states'])==count
        for entry in manifest['states']:
            assert (ROOT/entry['svg']).is_file()
            assert (ROOT/entry['circuit']).is_file()
            assert (ROOT/entry['combined']).is_file()
            assert (ROOT/entry['svg']).with_suffix('.png').is_file()
            assert (ROOT/entry['combined']).with_suffix('.png').is_file()


@pytest.mark.parametrize('path',[
    'output_lcc/rectifier/sheets/estado_02.svg',
    'output_lcc/inverter/sheets/estado_04.svg',
    'output_hvdc/sheets/hvdc_joint_state_12.svg'])
def test_vector_sheets_keep_editable_subdrawings_and_unique_svg_ids(path):
    r=ET.parse(ROOT/path).getroot()
    ids=[e.get('id') for e in r.iter() if e.get('id')]
    assert len(ids)==len(set(ids))
    assert len(r.findall('.//{http://www.w3.org/2000/svg}svg'))>=2
    assert len(r.findall('.//{http://www.w3.org/2000/svg}text'))>12


@pytest.mark.parametrize('index',range(1,25))
def test_hvdc_circuit_has_no_invalid_line_coordinates(index):
    """Catches a previously missed diagonal neutral-wire drawing bug."""
    root=ET.parse(ROOT/f'output_hvdc/hvdc_joint_state_{index:02d}.svg').getroot()
    for line in root.iter('{http://www.w3.org/2000/svg}line'):
        for attr in ('x1','x2','y1','y2'):
            if line.get(attr) is not None:
                float(line.get(attr))
