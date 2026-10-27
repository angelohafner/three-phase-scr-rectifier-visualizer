"""Regression checks for electrically coherent, mathematically styled SVGs."""
from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

import rectifier_art as art
from hvdc_link_model import CombinedSchedule, HVDCLinkTopology, LinkSettings
from hvdc_link_renderer import HVDCLinkRenderer
from rectifier_model import CommutationSequence
from lcc_converter import renderer_for, InverterOperatingPoint


def svg_text_content(tree: ET.ElementTree) -> list[str]:
    """Text content must be joined without implicit XML-formatting whitespace."""
    return [''.join(element.itertext()) for element in tree.iter(art.S + 'text')]


def test_units_variables_and_matrices_have_explicit_roles() -> None:
    root = ET.Element(art.S + 'svg')
    art.angle_notation(root, 12, 24, [('α', 'r', 15), ('μ', 'i', 12)])
    art.math_label(root, 12, 45, 'v', subscript='a')
    art.math_label(root, 12, 65, 'I', subscript='dc', upright_subscript=True)
    art.math_formula(root, 12, 80, [('10 ', 'roman'), ('kV', 'unit')])
    art.matrix_label(root, 12, 110, 'A')
    art.indent_svg(root)
    assert 'αr = 15°  ·  μi = 12°' in svg_text_content(ET.ElementTree(root))
    nodes = root.findall('.//' + art.S + 'tspan')
    assert nodes
    for node in nodes:
        role = node.get('data-math-role')
        if role in ('variable', 'subscript-variable'):
            assert node.get('font-style') == 'italic'
        if role in ('roman', 'unit', 'subscript-roman'):
            assert node.get('font-style') == 'normal'
        if role == 'matrix':
            assert node.get('font-style') == 'normal'
            assert node.get('font-weight') == '700'
    assert any(n.text == 'kV' and n.get('data-math-role') == 'unit' for n in nodes)
    assert any(n.text == 'A' and n.get('data-math-role') == 'matrix' for n in nodes)
    assert any(n.text == 'r' and n.get('data-math-role') == 'subscript-roman' for n in nodes)


@pytest.mark.parametrize('station', ['rectifier', 'inverter'])
def test_standalone_labels_have_no_implicit_spacing(station: str) -> None:
    state = CommutationSequence(15).state(2)
    renderer = renderer_for(station, InverterOperatingPoint())
    fig = renderer.render(renderer.topology.highlight(state), state)
    art.indent_svg(fig)
    text = svg_text_content(fig)
    assert any('T1' in txt or 'T' in txt for txt in text)
    assert any('L' in txt for txt in text)
    for node in fig.iter(art.S+'text'):
        if len(node):
            assert node.text is None or node.text.strip()
            assert all(not child.tail or child.tail.strip() for child in node)
    if station == 'inverter':
        assert 'α = 145°' in text
        assert 'γ = 20°' in text


@pytest.mark.parametrize('index', range(24))
def test_full_hvdc_all_24_states(index: int) -> None:
    settings = LinkSettings()
    state = CombinedSchedule(settings).intervals[index]
    top = HVDCLinkTopology()
    traced = top.highlight(state)
    figure = HVDCLinkRenderer(settings, top).render(state)
    svg = figure.getroot()
    labeled = [n for n in svg.iter(art.S+'g') if n.get('data-scr')]
    assert len(labeled) == 12
    active = {x.get('data-scr') for x in labeled if x.get('data-active') == 'true'}
    assert active == traced['scrs']
    assert all(w.start == nxt.end for loop in traced['loops']
               for w,nxt in zip(loop[1:],loop[:-1]))
    for node in labeled:
        # Each station displays T_i only, not the old erroneous T_{RT_i}.
        math_labels = [x for x in node.iter(art.S+'text') if (x.text or '') == 'T']
        assert len(math_labels) == 1
        device_num = node.get('data-scr').split('_T')[-1]
        sub = math_labels[0].find(art.S+'tspan')
        assert sub is not None and sub.text == device_num
        assert sub.get('font-style') == 'normal'
    # Topological power and return conductors must be present in every circuit.
    assert {'L_DR', 'L_DI', 'R_LINE', 'METALLIC_RETURN'} <= traced['active']
    text = svg_text_content(figure)
    assert any(x.startswith('αr = 15°') for x in text)
    assert all((node.get('font-style') == 'italic') for node in svg.iter(art.S+'tspan')
               if node.text in {'α', 'μ', 'γ'})
    assert not any('T_RT' in x or 'T_IT' in x for x in text)


def test_line_crossover_avoids_false_short_circuits() -> None:
    settings = LinkSettings()
    s = CombinedSchedule(settings).intervals[0]
    root = HVDCLinkRenderer(settings).render(s).getroot()
    for bridge in ('feeders-R', 'feeders-I'):
        groups = [e for e in root.iter(art.S+'g') if e.get('id') == bridge]
        assert len(groups) == 1
        arcs = [e.get('d') or '' for e in groups[0].iter(art.S+'path')]
        assert any(' C ' in arc for arc in arcs), 'Unconnected crossovers need their own bridge arcs'


def test_angle_reference_and_typographic_units_survive_export() -> None:
    settings = LinkSettings()
    fig = HVDCLinkRenderer(settings).render(CombinedSchedule(settings).intervals[0])
    texts = svg_text_content(fig)
    assert any('relative commutation reference' in item for item in texts)
    assert any('Relative commutation offset' in item for item in texts)
    for node in fig.iter(art.S+'tspan'):
        if node.get('data-math-role') == 'unit':
            assert node.get('font-style') == 'normal'
        if node.text in {'α', 'μ', 'γ'}:
            assert node.get('font-style') == 'italic'


def test_bus_junctions_follow_colored_conductor_paths() -> None:
    """Unused valve taps must not create black breaks in a red DC bus."""
    from hvdc_link_renderer import COLUMNS, PALETTE, Y_P, Y_N
    settings = LinkSettings()
    schedule = CombinedSchedule(settings)
    for state in schedule.intervals:
        root = HVDCLinkRenderer(settings).render(state).getroot()
        for station in ('R', 'I'):
            bridge = next(g for g in root.iter(art.S+'g')
                          if g.get('id') == f'bridge-{station}')
            for ypos in (Y_P, Y_N):
                circles = [c for c in bridge.iter(art.S+'circle')
                           if float(c.get('cy')) == ypos]
                assert len(circles) == 3
                selected = (state.rectifier if station == 'R' else state.inverter)
                values = sorted(COLUMNS[station].values())
                active_x = [COLUMNS[station][p] for p in 'abc'
                            if ((f'T{[1,3,5]["abc".index(p)]}' if ypos == Y_P
                                 else f'T{[2,4,6]["abc".index(p)]}') in selected.scrs)]
                for dot in circles:
                    x = float(dot.get('cx'))
                    should_red = (x >= min(active_x) if station == 'R'
                                  else x <= max(active_x))
                    assert (dot.get('fill') == art.C['active']) == should_red


def test_star_trunk_node_on_active_segment_matches_current_color() -> None:
    from hvdc_link_renderer import PHASE_Y, SECONDARY_NEUTRAL
    settings = LinkSettings()
    schedule = CombinedSchedule(settings)
    for state in schedule.intervals:
        root = HVDCLinkRenderer(settings).render(state).getroot()
        for station in ('R', 'I'):
            transform = next(g for g in root.iter(art.S+'g')
                             if g.get('id') == f'transformer-{station}')
            selected = (state.rectifier if station == 'R' else state.inverter)
            active_phase = {p for high, low in selected.pairs for p in (high, low)}
            ys = [PHASE_Y[p] for p in active_phase]
            dots = [c for c in transform.iter(art.S+'circle')
                    if float(c.get('cx')) == SECONDARY_NEUTRAL[station]]
            assert len(dots) == 3
            for dot in dots:
                y = float(dot.get('cy'))
                assert (dot.get('fill') == art.C['active']) == (min(ys) <= y <= max(ys))
