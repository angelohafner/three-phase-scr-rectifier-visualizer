#!/usr/bin/env python3
"""Reusable Inkscape SVG renderer and 12-state editorial comparison panel."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET
import copy

import rectifier_art as art
from rectifier_model import CircuitTopology, ConductionState, CommutationSequence, Highlight


@dataclass(frozen=True)
class StyleManager:
    """Centralized visual styles, text formatting, and SVG arrow markers."""
    ink: str = art.C['ink']
    red: str = art.C['active']
    muted: str = art.C['muted']
    background: str = art.C['background']
    paper: str = art.C['paper']
    border: str = art.C['border']

    def add_arrow_definition(self, root: ET.Element) -> None:
        definitions = art.element(root, 'defs')
        marker = art.element(definitions, 'marker', id='redArrow',
                             viewBox='0 0 12 12', refX='10', refY='6',
                             markerWidth='5.5', markerHeight='5.5',
                             orient='auto', markerUnits='strokeWidth')
        art.path(marker, 'M 1,1 L 11,6 L 1,11 Z', self.red, 0, self.red)

    def arrow(self, parent: ET.Element, x1: float, y1: float,
              x2: float, y2: float) -> None:
        """Draw the conventional-current arrow exactly on the wire centerline."""
        art.line(parent, x1, y1, x2, y2, self.red, 3.6,
                 marker_end='url(#redArrow)')

    def arrow_on(self, parent: ET.Element, name: str, orientation: int) -> None:
        """Place only physically meaningful arrows on straight wire sections."""
        if orientation == 0:
            return
        x = art.X
        y = art.Y
        coord: tuple[float, float, float, float] | None = None
        if name.startswith('FASE_'):
            ph = name[-1].lower()
            coord = (469, y[ph], 509, y[ph])
        elif name == 'NEUTRO_AB':
            coord = (x['star'], 415, x['star'], 445)
        elif name == 'NEUTRO_BC':
            coord = (x['star'], 463, x['star'], 493)
        elif name.startswith('POS_') or name.startswith('NEG_'):
            a, b = {
                'POS_T1_T3': ('a', 'b'),
                'POS_T3_T5': ('b', 'c'),
                'POS_T5_CARGA': ('c', 'load'),
                'NEG_T2_T4': ('a', 'b'),
                'NEG_T4_T6': ('b', 'c'),
                'NEG_T6_CARGA': ('c', 'load'),
            }[name]
            cx = (x[a] + x[b]) / 2
            bus_y = y['plus'] if name.startswith('POS_') else y['minus']
            coord = (cx - 22, bus_y, cx + 22, bus_y)
        elif name.startswith('T') and '_' in name:
            scr, side = name.split('_', 1)
            ph, upper = art.SCR_TO_POSITION[scr]
            x0 = x[ph]
            if upper:
                if side == 'FASE':
                    coord = (x0, 382, x0, 353)
                else:
                    coord = (x0, 286, x0, 253)
            else:
                if side == 'FASE':
                    middle = (y[ph] + y['bottom_scr'] - 17) / 2
                    coord = (x0, middle + 14, x0, middle - 14)
                else:
                    coord = (x0, 632, x0, 604)
            # The physical orientation of all SCR leads in this layout is upward.
            # The graph definition follows this same direction for these leads.
            if coord and orientation < 0:
                coord = (coord[2], coord[3], coord[0], coord[1])
            self.arrow(parent, *coord)
            return
        elif name == 'CARGA_POS_L':
            coord = (x['load'], 251, x['load'], 279)
        elif name == 'CARGA_L_R':
            coord = (x['load'], 391, x['load'], 422)
        elif name == 'CARGA_R_NEG':
            coord = (x['load'], 586, x['load'], 615)
        if coord is not None:
            if orientation < 0:
                coord = (coord[2], coord[3], coord[0], coord[1])
            self.arrow(parent, *coord)


class CircuitRenderer:
    """Render any manual or electrically validated state with shared primitives."""
    def __init__(self, topology: CircuitTopology | None = None,
                 styles: StyleManager | None = None) -> None:
        self.topology = topology or CircuitTopology()
        self.styles = styles or StyleManager()

    def render(self, selected: Highlight, state: ConductionState | None = None,
               ideal_step: int | None = None) -> ET.ElementTree:
        art.ET.register_namespace('', art.SVG_NS)
        art.ET.register_namespace('inkscape', art.INK_NS)
        root = ET.Element(art.S+'svg', {
            'width': str(art.W), 'height': str(art.H),
            'viewBox': f'0 0 {art.W} {art.H}', 'version': '1.1',
        })
        art.element(root, 'title').text = (
            f'{state.label}, state {state.number}: {state.scr_description}'
            if state else f'Editable six-pulse SCR bridge: {selected.title}'
        )
        art.element(root, 'desc').text = (
            'Editable conduction paths in a three-phase SCR rectifier. '
            'Red means an active conducting component. Commutation overlap '
            'is a topological model, not a current-sharing simulation. '
            'Arrow directions follow graph traversals.'
        )
        self.styles.add_arrow_definition(root)
        self._background(root)
        self._header(root, selected, state, ideal_step)
        self._wires(root, selected)
        self._components(root, selected, state)
        self._feeders(root, selected)
        self._annotations(root, selected)
        self._footer(root, selected, state, ideal_step)
        return ET.ElementTree(root)

    def _background(self, root: ET.Element) -> None:
        layer = art.layer(root, '01 - Background', 'background')
        art.element(layer, 'rect', x=0, y=0, width=art.W, height=art.H,
                    fill=self.styles.background)
        art.element(layer, 'rect', x=55, y=178, width=1410, height=545,
                    rx=20, fill=self.styles.paper, stroke=self.styles.border,
                    stroke_width=1.4)

    def _header(self, root: ET.Element, selected: Highlight,
                state: ConductionState | None, ideal_step: int | None) -> None:
        layer = art.layer(root, '02 - Headings', 'headings')
        art.txt(layer, 65, 78, selected.title[:48], size=32, bold=True)
        art.txt(layer, 66, 120,
                'Six-pulse bridge  ·  Star-connected AC sources  ·  Conduction paths',
                size=19, color=self.styles.muted)
        art.element(layer, 'rect', x=1197, y=46, width=267, height=77,
                    rx=13, fill='#EAF0F7', stroke=self.styles.border)
        if state:
            title = f'STATE {state.number:02d} / 12  ·  '+ ('OVERLAP' if state.is_overlap else 'NORMAL')
            active = ' · '.join(sorted(state.scrs, key=lambda a:int(a[1:])))
        elif ideal_step is not None:
            title = f'IDEAL INTERVAL {ideal_step} / 6'
            active = ' · '.join(sorted(selected.thyristors, key=lambda a:int(a[1:])))
        else:
            title = 'CUSTOM SELECTION'
            active = ' · '.join(sorted(selected.thyristors, key=lambda a:int(a[1:]))) or 'NONE'
        art.txt(layer, 1215, 71, title, size=13, bold=True, color=self.styles.muted)
        art.txt(layer, 1215, 105, active, size=23, bold=True,
                color=self.styles.red)

    def _wires(self, root: ET.Element, sel: Highlight) -> None:
        black = art.layer(root, '03 - Conductors', 'wires-base')
        for name in sorted(art.WIRE_IDS.difference(art.FEED_WIRES)):
            art.wire_segment(black, name, self.styles.ink, False)
        highlighted = art.layer(root, '04 - Highlighted conductors',
                                'wires-highlighted')
        for name in sorted(sel.paths.difference(art.FEED_WIRES)):
            art.wire_segment(highlighted, name, self.styles.red, True)

    def _components(self, root: ET.Element, sel: Highlight,
                    state: ConductionState | None) -> None:
        base = art.layer(root, '05 - Voltage sources, reactors and load', 'components-base')
        for ph in art.PHASES:
            art.ac_voltage_source(base, ph, self.styles.ink, False)
            art.winding(base, ph, self.styles.ink, False)
        art.dc_inductor(base, self.styles.ink, False)
        art.us_resistor(base, self.styles.ink, False)
        scr_base = art.layer(root, '06 - Native Schemdraw SCR geometry', 'scr-base')
        for name in ('T1', 'T3', 'T5', 'T2', 'T4', 'T6'):
            art.scr_geometry(scr_base, name, self.styles.ink, False)
        selected = art.layer(root, '07 - Highlighted sources and elements', 'components-active')
        for ph in art.PHASES:
            if f'V{ph.upper()}' in sel.sources:
                art.ac_voltage_source(selected, ph, self.styles.red, True)
            if f'L{ph.upper()}' in sel.inductors:
                art.winding(selected, ph, self.styles.red, True)
        if 'LDC' in sel.inductors:
            art.dc_inductor(selected, self.styles.red, True)
        if sel.resistor:
            art.us_resistor(selected, self.styles.red, True)
        active_scrs = art.layer(root, '08 - Conducting SCRs', 'scr-active')
        for name in ('T1', 'T3', 'T5', 'T2', 'T4', 'T6'):
            if name not in sel.thyristors:
                continue
            status = 'ON'
            if state and state.is_overlap:
                if state.outgoing == name:
                    status = 'OUT'
                elif state.incoming == name:
                    status = 'IN'
            art.scr_geometry(active_scrs, name, self.styles.red, True, status)

    def _feeders(self, root: ET.Element, sel: Highlight) -> None:
        layer = art.layer(root, '09 - AC conductor jumps', 'ac-feeders')
        for ph in art.PHASES:
            art.draw_feeder(layer, ph, f'FASE_{ph.upper()}' in sel.paths)

    def _annotations(self, root: ET.Element, sel: Highlight) -> None:
        layer = art.layer(root, '10 - Mathematics, junctions and arrows', 'annotations')
        neighbors_plus = {
            'a': ('T1_POS', 'POS_T1_T3'),
            'b': ('T3_POS', 'POS_T1_T3', 'POS_T3_T5'),
            'c': ('T5_POS', 'POS_T3_T5', 'POS_T5_CARGA'),
        }
        neighbors_minus = {
            'a': ('T2_NEG', 'NEG_T2_T4'),
            'b': ('T4_NEG', 'NEG_T2_T4', 'NEG_T4_T6'),
            'c': ('T6_NEG', 'NEG_T4_T6', 'NEG_T6_CARGA'),
        }
        def any_selected(*items: str) -> bool:
            return any(item in sel.paths or item in sel.sources
                       for item in items)

        for ph in art.PHASES:
            P = ph.upper()
            art.dot(layer, art.X[ph], art.Y[ph],
                    any_selected(f'FASE_{P}', f'{art.TOP[ph]}_FASE',
                                 f'{art.BOTTOM[ph]}_FASE'), 6.2)
            art.math_label(layer, 450, art.Y[ph]-13, P,
                           color=(self.styles.red if f'FASE_{P}' in sel.paths
                                  else self.styles.ink), size=19, bold=True)
            adjacent = ('NEUTRO_AB',) if ph == 'a' else (
                ('NEUTRO_AB', 'NEUTRO_BC') if ph == 'b' else ('NEUTRO_BC',))
            art.dot(layer, art.X['star'], art.Y[ph],
                    any_selected(f'V{P}', *adjacent))
            art.dot(layer, art.X[ph], art.Y['plus'],
                    any_selected(*neighbors_plus[ph]))
            art.dot(layer, art.X[ph], art.Y['minus'],
                    any_selected(*neighbors_minus[ph]))

        art.dot(layer, art.X['load'], art.Y['plus'],
                any_selected('POS_T5_CARGA', 'CARGA_POS_L'))
        art.dot(layer, art.X['load'], art.Y['minus'],
                any_selected('NEG_T6_CARGA', 'CARGA_R_NEG'))
        art.math_label(layer, art.X['star']-30, art.Y['b']-9, 'O',
                       color=self.styles.muted, size=19, bold=True)
        art.txt(layer, 1267, 255, '+', size=26, bold=True,
                color=self.styles.red if 'CARGA_POS_L' in sel.paths
                else self.styles.ink)
        art.txt(layer, 1267, 669, '−', size=28, bold=True,
                color=self.styles.red if 'CARGA_R_NEG' in sel.paths
                else self.styles.ink)
        art.math_label(layer, 1285, 337, 'L', subscript='dc',
                       upright_subscript=True, size=23,
                       color=self.styles.red if 'LDC' in sel.inductors
                       else self.styles.ink)
        art.math_label(layer, 1285, 489, 'R', size=24,
                       color=self.styles.red if sel.resistor else self.styles.ink)
        if sel.arrows:
            arrows = sel.signed_edges()
            if not arrows:
                # Manual overrides can still show directional arrows when the
                # chosen SCR pair specifies exactly one physically valid loop.
                upper = [s for s in sel.thyristors if s in art.TOP.values()]
                lower = [s for s in sel.thyristors if s in art.BOTTOM.values()]
                if len(upper)==1 and len(lower)==1:
                    h = art.SCR_TO_POSITION[upper[0]][0]
                    l = art.SCR_TO_POSITION[lower[0]][0]
                    if h != l:
                        arrows = {w.edge.name:w.direction
                                  for w in self.topology.current_loop(h,l)}
            for edge, signed in arrows.items():
                # Manual selection may leave non-highlighted segments black.
                if edge in sel.paths and signed:
                    self.styles.arrow_on(layer, edge, 1 if signed > 0 else -1)

    def _footer(self, root: ET.Element, sel: Highlight,
                state: ConductionState | None, ideal_step: int | None) -> None:
        layer = art.layer(root, '11 - State legend', 'legend')
        if state:
            if state.is_overlap:
                heading = 'THREE SCRs CONDUCTING'
                label = (f'OUTGOING: {state.outgoing}    ·    '
                         f'INCOMING: {state.incoming}    ·    '
                         'two simultaneous conduction loops')
            else:
                heading = 'TWO SCRs CONDUCTING'
                label = 'One positive-group SCR and one negative-group SCR'
            art.txt(layer, 74, 757, heading, size=16, bold=True,
                    color=self.styles.red)
            art.txt(layer, 74, 784, label, size=16, color=self.styles.ink)
            art.txt(layer, 74, 812, f'Paths: {state.phase_description}',
                    size=14, color=self.styles.muted)
            art.txt(layer, 955, 783,
                    f'Electrical angle: {state.theta_start:g}°–{state.theta_end:g}°',
                    size=15, color=self.styles.ink)
            art.math_label(layer, 957, 812, f'μ = {state.mu:g}°', size=17,
                           color=self.styles.muted)
        elif ideal_step:
            art.txt(layer, 74, 762, f'IDEAL CONDUCTION INTERVAL {ideal_step} OF 6',
                    size=17, bold=True, color=self.styles.red)
            art.txt(layer, 74, 792, 'Two SCRs conducting. Overlap neglected (μ = 0°).',
                    size=17, color=self.styles.ink)
        else:
            art.txt(layer, 74, 763, 'MANUAL COMPONENT SELECTION', size=17,
                    bold=True, color=self.styles.red)
            art.txt(layer, 74, 793,
                    'SCRs: ' + ', '.join(sorted(sel.thyristors)) +
                    '    |    Sources: ' + ', '.join(sorted(sel.sources)) +
                    '    |    Inductors: ' + ', '.join(sorted(sel.inductors)),
                    size=15, color=self.styles.ink)
            art.txt(layer, 74, 823,
                    'Manual highlighting does not guarantee a physically valid conduction path.',
                    size=14, color=self.styles.muted)

    @staticmethod
    def save(tree: ET.ElementTree, filename: Path) -> None:
        filename.parent.mkdir(parents=True, exist_ok=True)
        ET.indent(tree, space='  ')
        tree.write(filename, encoding='utf-8', xml_declaration=True)


def _prefix_identifiers(svg: ET.Element, prefix: str) -> None:
    """Avoid ID collisions in the editable panel assembled from 12 SVGs."""
    replacements = {}
    for node in svg.iter():
        ident = node.get('id')
        if ident:
            replacements[ident] = prefix + ident
            node.set('id', prefix + ident)
    for node in svg.iter():
        for key, value in tuple(node.attrib.items()):
            if 'url(#' in value:
                for old, new in replacements.items():
                    value = value.replace('url(#'+old+')', 'url(#'+new+')')
                node.set(key, value)


def build_panel(states: tuple[ConductionState, ...], renderer: CircuitRenderer,
                output: Path) -> Path:
    """Assemble 12 full editable circuit vectors into a comparison SVG."""
    if len(states) != 12:
        raise ValueError('A 12-state comparison panel requires exactly 12 states')
    scale = 0.444
    itemw, itemh = art.W*scale, art.H*scale
    gapx, gapy, margin = 24, 24, 44
    top = 128
    width = 3*itemw + 2*gapx + 2*margin
    height = top + 4*itemh + 3*gapy + margin + 30
    root = ET.Element(art.S+'svg', {
        'width': str(round(width)), 'height': str(round(height)),
        'viewBox': f'0 0 {width:g} {height:g}', 'version': '1.1',
    })
    art.element(root, 'title').text = 'Twelve SCR conduction states with commutation overlap'
    art.element(root, 'rect', x=0, y=0, width=width, height=height,
                fill='#F0F4F9')
    art.txt(root, margin, 52, 'SIX-PULSE SCR RECTIFIER', size=34, bold=True)
    art.txt(root, margin, 89,
            f'12 conduction states   ·   μ = {states[0].mu:g}°   ·   3-phase ABC system',
            size=21, color=renderer.styles.muted)
    for i, state in enumerate(states):
        col, row = i%3, i//3
        ox = margin + col*(itemw+gapx)
        oy = top + row*(itemh+gapy)
        art.element(root, 'rect', x=ox-2, y=oy-2,
                    width=itemw+4, height=itemh+4, rx=12,
                    fill='#FFFFFF', stroke='#CFDBE8', stroke_width=2)
        child_root = copy.deepcopy(renderer.render(renderer.topology.highlight(state),state).getroot())
        _prefix_identifiers(child_root, f'st{i+1:02d}-')
        grouped = ET.SubElement(root, art.S+'g', {
            'id': f'panel-state-{i+1:02d}',
            'transform': f'translate({ox:.3f} {oy:.3f}) scale({scale:g})',
        })
        for element in list(child_root):
            grouped.append(element)
    art.txt(root, margin, height-25,
            'Red = conducting path    ·    OUT = outgoing SCR    ·    IN = incoming SCR    ·    μ changes angular duration, not current magnitude',
            size=17, color=renderer.styles.muted)
    renderer.save(ET.ElementTree(root),output)
    return output
