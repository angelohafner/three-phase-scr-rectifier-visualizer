#!/usr/bin/env python3
"""Render real Schemdraw element segments into positioned editable SVG groups.

The component geometry comes from Schemdraw's element definitions.  When the
optional package is absent, explicitly labelled reference geometry from
Schemdraw 0.23 is used so the offline lecture can still be built.  CI tests
and regenerates with the actual Schemdraw package installed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from xml.etree import ElementTree as ET

try:
    import schemdraw.elements as elm
except ImportError:
    elm = None

import rectifier_art as art

SCHEMDRAW_AVAILABLE = elm is not None
NATIVE_NAMES = ('SCR', 'ResistorIEEE', 'Inductor', 'SourceSin', 'SourceV', 'SourceI')


@dataclass(frozen=True)
class ReferencePath:
    path: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class ReferencePolygon:
    verts: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class ReferenceCircle:
    center: tuple[float, float]
    radius: float


@dataclass(frozen=True)
class ReferenceArc:
    center: tuple[float, float]
    width: float
    height: float
    theta1: float
    theta2: float
    angle: float = 0


def _reference_segments(name: str) -> tuple:
    """Reference primitives matching the MIT-licensed Schemdraw 0.23 sources."""
    nan = math.nan
    if name == 'SCR':
        return (ReferencePath(((0, 0), (nan, nan), (.35, .25), (.35, -.25),
                               (nan, nan), (.35, 0))),
                ReferencePolygon(((0, .25), (.35, 0), (0, -.25))),
                ReferencePath(((.35, 0), (.65, -.3), (.65, -.5))))
    if name == 'ResistorIEEE':
        w, h = 1 / 6, .25
        return (ReferencePath(((0, 0), (.5*w, h), (1.5*w, -h),
                               (2.5*w, h), (3.5*w, -h), (4.5*w, h),
                               (5.5*w, -h), (1, 0))),)
    if name == 'Inductor':
        result = [ReferencePath(((0, 0), (nan, nan), (1, 0)))]
        result.extend(ReferenceArc(((i*2+1)*.25/2, 0), .25, .25, 0, 180)
                      for i in range(4))
        return tuple(result)
    if name in ('SourceSin', 'SourceV', 'SourceI'):
        result = [ReferencePath(((0, 0), (0, 0), (nan, nan),
                                 (1, 0), (1, 0))),
                  ReferenceCircle((.5, 0), .5)]
        if name == 'SourceSin':
            sy = [(-.25 + .5 * n / 24) for n in range(25)]
            sx = [.2 * math.sin((v-.25)*math.pi*2/.5)+.5 for v in sy]
            result.append(ReferencePath(tuple(zip(sx, sy))))
        elif name == 'SourceV':
            result.extend((ReferencePath(((.25, -.1), (.25, .1))),
                           ReferencePath(((.65, 0), (.85, 0))),
                           ReferencePath(((.75, -.1), (.75, .1)))))
        else:
            # Schemdraw SourceI: circled arrow along the element axis.
            result.append(ReferencePath(((.25, 0), (.75, 0))))
        return tuple(result)
    raise ValueError(f'Unknown electrical symbol {name}')


def element_segments(name: str, *, require_library: bool = False) -> tuple:
    """Instantiate a native Schemdraw component and extract its own segments."""
    if name not in NATIVE_NAMES:
        raise ValueError(f'Unsupported Schemdraw element: {name}')
    if elm is not None:
        obj = getattr(elm, name)()
        return tuple(obj.segments)
    if require_library:
        raise RuntimeError('Schemdraw is required: python -m pip install schemdraw>=0.22')
    return _reference_segments(name)


def draw_component(parent: ET.Element, name: str,
                   start: tuple[float, float], end: tuple[float, float],
                   color: str, width: float = 3.4,
                   *, fill: str = 'white', transverse_scale: float | None = None,
                   group_id: str | None = None, require_library: bool = False) -> ET.Element:
    """Place Schemdraw native geometry by its terminal anchors, preserving wires.

    start/end are true electrical terminals; their physical coordinates are not
    inferred from a stroke's bounding box.  SVG paths stay editable in Inkscape.
    """
    x0, y0 = start
    dx, dy = end[0] - x0, end[1] - y0
    length = math.hypot(dx, dy)
    if length < 1e-8:
        raise ValueError('A two-terminal component requires distinct endpoints')
    span = .35 if name == 'SCR' else 1.0
    axis = length / span
    cross = transverse_scale if transverse_scale is not None else axis
    ux, uy = dx/length, dy/length
    vx, vy = -uy, ux
    def pt(point: tuple[float, float]) -> tuple[float, float]:
        x, y = float(point[0]), float(point[1])
        return x0 + x*axis*ux + y*cross*vx, y0 + x*axis*uy + y*cross*vy

    g = art.group(parent, group_id or f'{name.lower()}-component')
    g.set('data-symbol', f'schemdraw.elements.{name}')
    g.set('data-symbol-source', 'native-instance' if SCHEMDRAW_AVAILABLE else 'schemdraw-0.23-reference')
    g.set('data-terminal-start', f'{x0:g},{y0:g}')
    g.set('data-terminal-end', f'{end[0]:g},{end[1]:g}')

    parts = element_segments(name, require_library=require_library)
    for index, seg in enumerate(parts):
        if hasattr(seg, 'path'):
            sequence = []
            def flush() -> None:
                if len(sequence) > 1:
                    art.path(g, 'M '+' L '.join(f'{x:.3f},{y:.3f}' for x,y in sequence),
                             color, width)
                sequence.clear()
            for x, y in list(seg.path) + [(math.nan, math.nan)]:
                if not (math.isfinite(x) and math.isfinite(y)):
                    flush()
                else:
                    if name == 'SourceSin' and index == len(parts)-1 and abs(dx) > abs(dy):
                        # Schemdraw's source sine is designed for upright sources.
                        # Rotate only the native sine path for horizontal terminals.
                        x, y = .5-y, x-.5
                    sequence.append(pt((x, y)))
        elif hasattr(seg, 'verts'):
            points = [pt(tuple(a)) for a in seg.verts]
            art.element(g, 'polygon', points=' '.join(f'{x:.3f},{y:.3f}' for x,y in points),
                        fill=fill, stroke=color, stroke_width=width,
                        stroke_linejoin='round')
        elif hasattr(seg, 'center') and hasattr(seg, 'radius'):
            # A circular Schemdraw source remains a circle under uniform scale.
            cx, cy = pt(tuple(seg.center))
            if abs(axis-cross)<1e-7:
                art.element(g, 'circle', cx=f'{cx:.3f}', cy=f'{cy:.3f}',
                            r=f'{seg.radius*axis:.3f}', fill=fill,
                            stroke=color, stroke_width=width)
            else:
                pts = [pt((seg.center[0]+seg.radius*math.cos(t*math.tau/90),
                           seg.center[1]+seg.radius*math.sin(t*math.tau/90))) for t in range(91)]
                art.path(g, 'M '+' L '.join(f'{x:.3f},{y:.3f}' for x,y in pts)+' Z',color,width,fill)
        elif hasattr(seg, 'center') and hasattr(seg, 'theta1'):
            cx, cy = seg.center
            t1, t2 = math.radians(seg.theta1), math.radians(seg.theta2)
            rotation = math.radians(getattr(seg, 'angle', 0))
            points=[]
            for j in range(31):
                th = t1+(t2-t1)*j/30
                xx = seg.width/2*math.cos(th)
                yy = seg.height/2*math.sin(th)
                local=(cx + xx*math.cos(rotation) - yy*math.sin(rotation),
                       cy + xx*math.sin(rotation) + yy*math.cos(rotation))
                points.append(pt(local))
            art.path(g, 'M '+' L '.join(f'{x:.3f},{y:.3f}' for x,y in points),color,width)
        else:
            raise TypeError(f'Unsupported Schemdraw segment: {type(seg).__name__}')
    if name == 'SourceI':
        # SourceI stores its arrow head as Segment(arrow='->'); preserve it
        # when converting Schemdraw primitives to editable SVG shapes.
        tip = pt((.75, 0))
        upper = pt((.59, -.095))
        lower = pt((.59, .095))
        art.element(g, 'polygon', points=' '.join(
            f'{x:.3f},{y:.3f}' for x, y in (tip, upper, lower)),
            fill=color, stroke=color, stroke_width='1')
    return g


def draw_inductor(parent, start, end, color, width=3.4, **kwargs):
    return draw_component(parent, 'Inductor', start, end, color, width, **kwargs)


def draw_resistor(parent, start, end, color, width=3.4, **kwargs):
    return draw_component(parent, 'ResistorIEEE', start, end, color, width, **kwargs)


def draw_scr(parent, start, end, color, width=3.4, **kwargs):
    return draw_component(parent, 'SCR', start, end, color, width, **kwargs)


def draw_ac_source(parent, start, end, color, width=3.4, **kwargs):
    return draw_component(parent, 'SourceSin', start, end, color, width, **kwargs)


def draw_dc_source(parent, start, end, color, width=3.4, **kwargs):
    return draw_component(parent, 'SourceV', start, end, color, width, **kwargs)


def draw_current_source(parent, start, end, color, width=3.4, **kwargs):
    """Use the native Schemdraw SourceI element when it is installed."""
    return draw_component(parent, 'SourceI', start, end, color, width, **kwargs)
