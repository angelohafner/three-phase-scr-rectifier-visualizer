"""Regression tests for actual Schemdraw symbol geometry and terminal anchors."""
from __future__ import annotations

import os
from xml.etree import ElementTree as ET

import pytest

import rectifier_art as art
from halfwave_figures import circuit_svg
from schemdraw_symbols import NATIVE_NAMES, SCHEMDRAW_AVAILABLE, element_segments


def test_all_required_library_elements_supply_usable_segments():
    for name in NATIVE_NAMES:
        segments=element_segments(name)
        assert segments
        assert all(any(hasattr(segment,field) for field in ('path','verts','center'))
                   for segment in segments)


@pytest.mark.parametrize('load,names',[
    ('R',{'SCR','ResistorIEEE','SourceSin'}),
    ('RL',{'SCR','ResistorIEEE','Inductor','SourceSin'})
])
def test_halfwave_uses_standard_symbols_at_real_terminals(load,names):
    root=circuit_svg(load,True).getroot()
    groups=[g for g in root.iter(art.S+'g') if g.get('data-symbol')]
    actual={g.get('data-symbol').split('.')[-1] for g in groups}
    assert actual==names
    for group in groups:
        assert group.get('data-symbol-source')==(
            'native-instance' if SCHEMDRAW_AVAILABLE else 'schemdraw-0.23-reference')
        start,end=group.get('data-terminal-start'),group.get('data-terminal-end')
        assert start and end and start!=end
        assert any(x.tag in (art.S+'path',art.S+'polygon',art.S+'circle')
                   for x in group)
    assert ('load-inductor' in [g.get('id') for g in groups])==(load=='RL')


def test_ci_instantiates_real_schemdraw_components():
    if os.environ.get('REQUIRE_NATIVE_SCHEMDRAW')=='1':
        assert SCHEMDRAW_AVAILABLE,'Schemdraw must be installed in CI'
    if not SCHEMDRAW_AVAILABLE:
        pytest.skip('Local offline build uses documented reference geometry')
    import schemdraw.elements as elm
    for name in NATIVE_NAMES:
        assert len(element_segments(name))==len(getattr(elm,name)().segments)


def test_three_phase_uses_native_inductors_resistor_and_sources():
    from rectifier_model import CircuitTopology,CommutationSequence
    from rectifier_renderer import CircuitRenderer
    topo=CircuitTopology()
    state=CommutationSequence(15).states[0]
    root=CircuitRenderer(topo).render(topo.highlight(state),state).getroot()
    all_ids=[e.get('id') for e in root.iter() if e.get('id')]
    assert len(all_ids)==len(set(all_ids))
    types={g.get('data-symbol') for g in root.iter() if g.get('data-symbol')}
    assert {'schemdraw.elements.Inductor','schemdraw.elements.ResistorIEEE',
            'schemdraw.elements.SourceSin'}<=types


def test_hvdc_link_uses_native_reactors_and_sources():
    from hvdc_link_renderer import HVDCLinkRenderer
    from hvdc_link_model import LinkSettings,CombinedState
    from rectifier_model import CommutationSequence
    settings=LinkSettings()
    state=CommutationSequence(12).states[0]
    joint=CombinedState(1,0,1,state,state)
    root=HVDCLinkRenderer(settings).render(joint).getroot()
    types=[g.get('data-symbol') for g in root.iter() if g.get('data-symbol')]
    assert types.count('schemdraw.elements.Inductor')>=10
    assert 'schemdraw.elements.SourceSin' in types
    assert 'schemdraw.elements.ResistorIEEE' in types
