#!/usr/bin/env python3
"""Reusable SVG/ Schemdraw component drawing functions from the legacy script.

All element geometries are retained from the previous Inkscape SVG generator.
When available, native `schemdraw.elements.SCR` segments are read directly;
otherwise its published primitive geometry is used for portability.
"""
from __future__ import annotations
import math
from xml.etree import ElementTree as ET
try:
    import schemdraw.elements as elm
except ImportError:
    elm = None

SVG_NS = 'http://www.w3.org/2000/svg'

INK_NS = 'http://www.inkscape.org/namespaces/inkscape'

SODI_NS = 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd'

ET.register_namespace('', SVG_NS)
ET.register_namespace('inkscape', INK_NS)
ET.register_namespace('sodipodi', SODI_NS)
W, H = 1520, 850
S = f'{{{SVG_NS}}}'

I = f'{{{INK_NS}}}'

C = {
    'background': '#F6F8FB', 'paper': '#FFFFFF',
    'ink': '#203246', 'muted': '#6C7D90',
    'active': '#E12E3F', 'active_fill': '#FFE9EC',
    'border': '#DCE4ED',
}

X = {'a': 560, 'b': 745, 'c': 930, 'load': 1240, 'star': 180,
     'source': 250, 'coil_start': 310, 'feed_start': 430}

SOURCE_RADIUS = 22

Y = {
    'plus': 235, 'minus': 662,
    'a': 408, 'b': 455, 'c': 502,
    'top_scr': 314, 'bottom_scr': 568,
}

PHASES = ('a', 'b', 'c')

TOP = {'a': 'T1', 'b': 'T3', 'c': 'T5'}

BOTTOM = {'a': 'T2', 'b': 'T4', 'c': 'T6'}

SCR_TO_POSITION = {
    **{name: (phase, True) for phase, name in TOP.items()},
    **{name: (phase, False) for phase, name in BOTTOM.items()},
}

SCR_IDS = frozenset(SCR_TO_POSITION)

INDUCTOR_IDS = frozenset(('LA', 'LB', 'LC', 'LDC'))

SOURCE_IDS = frozenset(('VA', 'VB', 'VC'))

FEED_WIRES = tuple(f'FASE_{p.upper()}' for p in PHASES)

NEUTRAL_WIRES = ('NEUTRO_AB', 'NEUTRO_BC')

SCR_WIRES = tuple(
    wire
    for name in ('T1', 'T3', 'T5', 'T2', 'T4', 'T6')
    for wire in (f'{name}_FASE', f'{name}_{"POS" if name in TOP.values() else "NEG"}')
)

PLUS_WIRES = ('POS_T1_T3', 'POS_T3_T5', 'POS_T5_CARGA')

MINUS_WIRES = ('NEG_T2_T4', 'NEG_T4_T6', 'NEG_T6_CARGA')

LOAD_WIRES = ('CARGA_POS_L', 'CARGA_L_R', 'CARGA_R_NEG')

WIRE_IDS = frozenset(
    FEED_WIRES + NEUTRAL_WIRES + SCR_WIRES
    + PLUS_WIRES + MINUS_WIRES + LOAD_WIRES
)

def element(parent: ET.Element, tag: str, **attrs: object) -> ET.Element:
    e = ET.SubElement(parent, S + tag)
    for key, val in attrs.items():
        if val is not None:
            e.set(key.replace('_', '-'), str(val))
    return e

def group(parent: ET.Element, ident: str) -> ET.Element:
    return element(parent, 'g', id=ident)

def layer(parent: ET.Element, title: str, ident: str) -> ET.Element:
    return ET.SubElement(parent, S + 'g', {
        'id': ident, I + 'groupmode': 'layer', I + 'label': title,
    })

def path(parent: ET.Element, data: str, color: str, width: float = 3.5,
         fill: str = 'none', **kwargs: object) -> ET.Element:
    return element(parent, 'path', d=data, fill=fill,
                   stroke=color, stroke_width=width,
                   stroke_linecap='round', stroke_linejoin='round', **kwargs)

def line(parent: ET.Element, x1: float, y1: float,
         x2: float, y2: float, color: str, width: float = 3.5,
         **kwargs: object) -> ET.Element:
    return element(parent, 'line', x1=x1, y1=y1, x2=x2, y2=y2,
                   stroke=color, stroke_width=width,
                   stroke_linecap='round', **kwargs)

def dot(parent: ET.Element, x: float, y: float, on: bool,
        radius: float = 5.4) -> None:
    element(parent, 'circle', cx=x, cy=y, r=radius,
            fill=C['active'] if on else C['ink'])

def txt(parent: ET.Element, x: float, y: float, message: str, *,
        size: float = 16, color: str | None = None,
        bold: bool = False, anchor: str | None = None) -> ET.Element:
    """Draw ordinary English prose using a regular UI font."""
    t = element(parent, 'text', x=x, y=y, fill=color or C['ink'],
                font_family='DejaVu Sans, Arial, sans-serif',
                font_size=size, font_weight='700' if bold else '400',
                text_anchor=anchor)
    t.text = message
    return t

def math_label(parent: ET.Element, x: float, y: float, symbol: str, *,
               subscript: str = '', size: float = 19,
               color: str | None = None, bold: bool = False,
               anchor: str | None = None,
               upright_subscript: bool = False) -> ET.Element:
    """Draw editable mathematical lettering with real typographic subscripts.

    The STIX Math font is preferred by Inkscape. SVG tspans keep the text
    fully editable, with Cambria Math and DejaVu Serif as fallback families.
    """
    t = element(parent, 'text', x=x, y=y, fill=color or C['ink'],
                font_family=MATH_FONT,
                font_style='italic', font_size=size,
                font_weight='600' if bold else '400', text_anchor=anchor)
    t.text = symbol
    if subscript:
        low = element(t, 'tspan', baseline_shift='sub', font_size=f'{size*0.65:g}',
                      font_style='normal' if upright_subscript or subscript.isdecimal() else 'italic')
        low.text = subscript
    return t

# Mathematical notation is formatted at the glyph-span level to remain editable.
MATH_FONT = 'STIX Math, STIX, Cambria Math, DejaVu Serif, serif'


def math_formula(parent: ET.Element, x: float, y: float,
                 spans: list[tuple[str, str]] | tuple[tuple[str, str], ...], *,
                 size: float = 19, color: str | None = None,
                 anchor: str | None = None) -> ET.Element:
    """Draw SVG math tokens with explicit scientific typography.

    Roles: variable (including Greek), roman, unit, matrix (bold upright),
    subscript-variable, subscript-roman. All glyphs remain actual text and
    can be edited in Inkscape rather than converted to paths.
    """
    roles = {'variable', 'roman', 'unit', 'matrix',
             'subscript-variable', 'subscript-roman'}
    label = element(parent, 'text', x=x, y=y, fill=color or C['ink'],
                    font_family=MATH_FONT, font_style='normal',
                    font_size=size, text_anchor=anchor)
    label.set('data-math-notation', 'mixed')
    for string, role in spans:
        if role not in roles:
            raise ValueError(f'Unsupported mathematical notation role: {role}')
        if not string:
            continue
        subscript = role.startswith('subscript-')
        italic = role in {'variable', 'subscript-variable'}
        fragment = element(
            label, 'tspan', font_style='italic' if italic else 'normal',
            font_weight='700' if role == 'matrix' else '400',
            font_size=f'{size*.66:g}' if subscript else str(size),
            baseline_shift='sub' if subscript else None,
        )
        fragment.set('data-math-role', role)
        fragment.text = string
    return label


def angle_notation(parent: ET.Element, x: float, y: float,
                   angles: list[tuple[str, str, float]] | tuple[tuple[str, str, float], ...], *,
                   size: float = 18, color: str | None = None,
                   anchor: str | None = None, separator: str = '  ·  ',
                   trailer: str = '') -> ET.Element:
    """Format Greek angle variables italic and angle-unit symbols upright."""
    parts: list[tuple[str, str]] = []
    for index, (variable, descriptor, value) in enumerate(angles):
        if index:
            parts.append((separator, 'roman'))
        parts.append((variable, 'variable'))
        if descriptor:
            parts.append((descriptor, 'subscript-roman'))
        parts.append((f' = {value:g}', 'roman'))
        parts.append(('°', 'unit'))
    if trailer:
        parts.append((trailer, 'roman'))
    return math_formula(parent, x, y, parts, size=size, color=color,
                        anchor=anchor)


def matrix_label(parent: ET.Element, x: float, y: float, symbol: str, *,
                 size: float = 19, color: str | None = None,
                 anchor: str | None = None) -> ET.Element:
    """Draw a matrix name upright and bold, following project convention."""
    if not symbol:
        raise ValueError('Matrix name must not be empty')
    return math_formula(parent, x, y, [(symbol, 'matrix')], size=size,
                        color=color, anchor=anchor)


def indent_svg(root_or_tree: ET.Element | ET.ElementTree,
               space: str = '  ') -> None:
    """Pretty-print SVG while preserving mathematical tspan adjacency.

    ElementTree.indent inserts whitespace between child tspans, and SVG text
    renders those blanks as unwanted spaces. Remove only formatting whitespace
    inside editable <text> nodes after indenting everything else.
    """
    ET.indent(root_or_tree, space=space)
    root = (root_or_tree.getroot() if isinstance(root_or_tree, ET.ElementTree)
            else root_or_tree)
    for label in root.iter(S + 'text'):
        if len(label):
            if not (label.text or '').strip():
                label.text = None
            for child in label:
                if child.tail is not None and not child.tail.strip():
                    child.tail = None


def native_scr_segments() -> tuple[tuple[str, tuple[tuple[float, float], ...]], ...]:
    """Return the genuine Schemdraw SCR primitive paths in element coordinates.

    `elm.SCR` is a Diode with an extra gate terminal. Unlike an ad-hoc triangle,
    this retrieves Schemdraw's own path and polygon primitives. If Schemdraw
    cannot be imported, the equivalent 0.23 source geometry is used as a safe
    self-contained fallback (resheight=0.25; see Schemdraw twoterm.py).
    """
    if elm is not None:
        native = elm.SCR()
        result = []
        for part in native.segments:
            if hasattr(part, 'path'):
                result.append(('polyline', tuple((float(x), float(y))
                                                 for x, y in part.path)))
            elif hasattr(part, 'verts'):
                result.append(('polygon', tuple((float(x), float(y))
                                                for x, y in part.verts)))
            else:
                raise ValueError(f'Unexpected SCR native segment type: {type(part).__name__}')
        if len(result) != 3:
            raise ValueError('Unexpected Schemdraw SCR symbol definition.')
        return tuple(result)

    # Exact paths of Schemdraw 0.23: base Diode + SCR gate connection.
    nan = math.nan
    return (
        ('polyline', ((0, 0), (nan, nan), (.35, .25),
                      (.35, -.25), (nan, nan), (.35, 0))),
        ('polygon', ((0, .25), (.35, 0), (0, -.25))),
        ('polyline', ((.35, 0), (.65, -.3), (.65, -.5))),
    )

SCR_PRIMITIVES = native_scr_segments()

def scr_geometry(parent: ET.Element, name: str, color: str, on: bool,
                 status: str = "ON", inverter: bool = False) -> None:
    """Draw native Schemdraw SCR: cathode-up or cathode-down."""
    phase, upper = SCR_TO_POSITION[name]
    xc = X[phase]
    cy = Y['top_scr'] if upper else Y['bottom_scr']
    g = group(parent, f'{"selected" if on else "base"}-{name.lower()}')
    g.set('data-symbol', 'schemdraw.elements.SCR')
    g.set('data-phase', phase.upper())
    scale = 70.0
    width = 4.7 if on else 3.3

    # Flip the real Schemdraw SCR primitive, including the gate lead, for
    # the inverter where DC+ -> upper SCR -> AC -> lower SCR -> DC-.
    def xy(local: tuple[float, float]) -> tuple[float, float]:
        x, y = local
        direction = 1 if inverter else -1
        return xc + direction * scale*y, cy + direction * scale*(x - .175)

    # The external conductor endpoints stay fixed in both orientations.
    anode_y = xy((0, 0))[1]
    cathode_y = xy((.35, 0))[1]
    upper_y = min(anode_y, cathode_y)
    lower_y = max(anode_y, cathode_y)
    line(g, xc, cy-17, xc, upper_y, color, width)
    line(g, xc, lower_y, xc, cy+18, color, width)

    for shape, vertices in SCR_PRIMITIVES:
        if shape == 'polygon':
            coords = [xy(pt) for pt in vertices]
            element(g, 'polygon',
                    points=' '.join(f'{px:.3f},{py:.3f}' for px, py in coords),
                    fill=C['active_fill'] if on else C['paper'],
                    stroke=color, stroke_width=width,
                    stroke_linejoin='round')
            continue
        current = []
        for pt in vertices + ((math.nan, math.nan),):
            if not (math.isfinite(pt[0]) and math.isfinite(pt[1])):
                if len(current) >= 2:
                    d = f'M {current[0][0]:.3f},{current[0][1]:.3f}'
                    d += ''.join(f' L {px:.3f},{py:.3f}' for px, py in current[1:])
                    path(g, d, color, width)
                current = []
            else:
                current.append(xy(pt))

    math_label(g, xc + 54, cy - 5, 'T', subscript=name[1:], size=22,
               color=color if on else C['ink'], bold=True)
    if on:
        txt(g, xc - 39, cy - 30, status, size=12,
            color=color, bold=True, anchor='middle')

def winding(parent: ET.Element, phase: str,
            color: str, highlighted: bool) -> None:
    """Draw an actual Schemdraw Inductor in series with each AC source."""
    from schemdraw_symbols import draw_inductor
    yp = Y[phase]
    g = group(parent, f'{"selected" if highlighted else "base"}-l{phase}')
    width = 4.8 if highlighted else 3.4
    draw_inductor(g, (X['coil_start'], yp), (X['coil_start']+80, yp), color,
                  width, transverse_scale=120,
                  group_id=f'symbol-{"selected" if highlighted else "base"}-l{phase}')
    line(g, X['coil_start']+80, yp, X['feed_start'], yp, color, width)
    math_label(g, X['coil_start']+39, yp-21, 'L', subscript=phase,
               size=18, color=color, anchor='middle')


def ac_voltage_source(parent: ET.Element, phase: str,
                      color: str, highlighted: bool) -> None:
    """Render Schemdraw SourceSin using exact original conductor endpoints."""
    from schemdraw_symbols import draw_ac_source
    g = group(parent, f'{"selected" if highlighted else "base"}-v{phase}')
    yp = Y[phase]
    xc, r = X['source'], SOURCE_RADIUS
    width = 4.8 if highlighted else 3.4
    line(g, X['star'], yp, xc-r, yp, color, width)
    line(g, xc+r, yp, X['coil_start'], yp, color, width)
    draw_ac_source(g,(xc-r,yp),(xc+r,yp),color,width,
                   group_id=f'symbol-{"selected" if highlighted else "base"}-v{phase}')
    math_label(g,xc+r+10,yp-12,'v',subscript=phase,color=color,size=16)


def dc_inductor(parent: ET.Element, color: str,
                highlighted: bool) -> None:
    """Native Schemdraw smoothing reactor in the DC branch."""
    from schemdraw_symbols import draw_inductor
    g = group(parent, f'{"selected" if highlighted else "base"}-ldc')
    draw_inductor(g,(1240,293),(1240,373),color,
                  4.8 if highlighted else 3.4,transverse_scale=150,
                  group_id=f'symbol-{"selected" if highlighted else "base"}-ldc')


def us_resistor(parent: ET.Element, color: str,
                highlighted: bool) -> None:
    """Native Schemdraw ResistorIEEE (American zigzag)."""
    from schemdraw_symbols import draw_resistor
    g = group(parent, f'{"selected" if highlighted else "base"}-r')
    draw_resistor(g,(1240,443),(1240,535),color,
                  4.7 if highlighted else 3.4,transverse_scale=68,
                  group_id=f'symbol-{"selected" if highlighted else "base"}-r')


def dc_voltage_supply(parent: ET.Element, color: str,
                      highlighted: bool) -> None:
    """Native Schemdraw SourceV with original inverter source polarity."""
    from schemdraw_symbols import draw_dc_source
    g = group(parent, f'{"selected" if highlighted else "base"}-edc')
    width = 4.8 if highlighted else 3.4
    x,y,r = X['load'],489,29
    line(g,x,443,x,y-r,color,width)
    line(g,x,y+r,x,535,color,width)
    draw_dc_source(g,(x,y+r),(x,y-r),color,width,
                   group_id=f'symbol-{"selected" if highlighted else "base"}-edc')


def arc_feeder(y: float, x_end: float) -> str:
    """Bridge wire crossings with arcs without electrical connections."""
    crossings = [X[ph] for ph in PHASES if X[ph] < x_end]
    commands = [f'M {X["feed_start"]},' + str(y)]
    for xx in crossings:
        commands.append(f'L {xx - 15},{y}')
        commands.append(
            f'C {xx - 15},{y - 20} {xx + 15},{y - 20} {xx + 15},{y}'
        )
    commands.append(f'L {x_end},{y}')
    return ' '.join(commands)

def draw_feeder(parent: ET.Element, phase: str,
                on: bool) -> None:
    xend, yp = X[phase], Y[phase]
    ident = f'FASE_{phase.upper()}'
    g = group(parent, 'wire-' + ident.lower())
    for cross_phase in PHASES:
        xc = X[cross_phase]
        if xc >= xend:
            continue
        # A white underlay breaks the crossed vertical wire, not the feeder.
        jump = (f'M {xc - 15},{yp} C {xc - 15},{yp - 20} '
                f'{xc + 15},{yp - 20} {xc + 15},{yp}')
        path(g, jump, C['paper'], 11)
    path(g, arc_feeder(yp, xend),
         C['active'] if on else C['ink'], 4.9 if on else 3.4)

def wire_segment(parent: ET.Element, ident: str,
                 color: str, on: bool) -> None:
    """Draw exactly one independently selectable conductive wire section."""
    if ident in FEED_WIRES:
        raise ValueError('Feeders are drawn last to preserve wire jump masks.')
    g = group(parent, ('selected-' if on else 'base-') + ident.lower())
    width = 5.1 if on else 3.4

    if ident == 'NEUTRO_AB':
        line(g, X['star'], Y['a'], X['star'], Y['b'], color, width)
    elif ident == 'NEUTRO_BC':
        line(g, X['star'], Y['b'], X['star'], Y['c'], color, width)
    elif ident.startswith('POS_'):
        coords = {
            'POS_T1_T3': (X['a'], X['b']),
            'POS_T3_T5': (X['b'], X['c']),
            'POS_T5_CARGA': (X['c'], X['load']),
        }
        ax, bx = coords[ident]
        line(g, ax, Y['plus'], bx, Y['plus'], color, width)
    elif ident.startswith('NEG_'):
        coords = {
            'NEG_T2_T4': (X['a'], X['b']),
            'NEG_T4_T6': (X['b'], X['c']),
            'NEG_T6_CARGA': (X['c'], X['load']),
        }
        ax, bx = coords[ident]
        line(g, ax, Y['minus'], bx, Y['minus'], color, width)
    elif ident in LOAD_WIRES:
        endpoints = {
            'CARGA_POS_L': (Y['plus'], 293),
            'CARGA_L_R': (373, 443),
            'CARGA_R_NEG': (535, Y['minus']),
        }
        ya, yb = endpoints[ident]
        line(g, X['load'], ya, X['load'], yb, color, width)
    else:
        name, side = ident.split('_')
        phase, upper = SCR_TO_POSITION[name]
        xc, yp = X[phase], Y[phase]
        cy = Y['top_scr'] if upper else Y['bottom_scr']
        if upper:
            ya, yb = ((yp, cy + 18) if side == 'FASE'
                      else (Y['plus'], cy - 17))
        else:
            ya, yb = ((yp, cy - 17) if side == 'FASE'
                      else (cy + 18, Y['minus']))
        line(g, xc, ya, xc, yb, color, width)
