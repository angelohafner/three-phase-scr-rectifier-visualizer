#!/usr/bin/env python3
"""Inkscape-editable vector drawings of an interconnected six-pulse HVDC link.

All SCR triangles and gates reuse the exact Schemdraw primitives imported in
rectifier_art. Coils, magnetic coupling and source symbols are vector paths.
Every colored element is selected from the two-station electrical graph.
"""
from __future__ import annotations

import math
from pathlib import Path
from xml.etree import ElementTree as ET

import rectifier_art as art
from hvdc_link_model import CombinedState, HVDCLinkTopology, LinkSettings
from rectifier_model import LOWER, UPPER


WIDTH, HEIGHT = 3500, 1550
PALETTE = {
    'ink': '#21334A', 'active': '#D52940', 'blue': '#2566A0',
    'quiet': '#76889C', 'green': '#18857B', 'paper': '#FFFFFF',
    'canvas': '#F4F7FB', 'line': '#D7E2ED', 'amber': '#A65B18',
}
Y_P, Y_N = 370.0, 1190.0
Y_TOP, Y_BOTTOM = 520.0, 1010.0
PHASE_Y = {'a': 705.0, 'b': 805.0, 'c': 905.0}
COLUMNS = {'R': {'a': 835.0, 'b': 1045.0, 'c': 1255.0},
           'I': {'a': 2225.0, 'b': 2435.0, 'c': 2645.0}}
SECONDARY_NEUTRAL = {'R': 405.0, 'I': 3125.0}
T_X = {
    'R': {'grid': 86, 'source': 156, 'primary_coil': (255, 313),
          'primary_neutral': 334, 'core': (365, 377),
          'secondary_coil': (435, 493), 'secondary_neutral': 405,
          'leakage': (571, 631), 'feed': 665},
    'I': {'grid': 3415, 'source': 3340, 'primary_coil': (3213, 3271),
          'primary_neutral': 3192, 'core': (3150, 3162),
          'secondary_coil': (3049, 3107), 'secondary_neutral': 3125,
          'leakage': (2790, 2850), 'feed': 2750},
}


def svg_title(root: ET.Element, title: str, desc: str) -> None:
    art.element(root, 'title').text = title
    art.element(root, 'desc').text = desc


def polyline(root: ET.Element, pts: list[tuple[float, float]], color: str,
             width: float = 3.6, **attrs: object) -> None:
    data = 'M '+' L '.join(f'{x:g},{y:g}' for x, y in pts)
    art.path(root, data, color, width, **attrs)


def round_rect(root: ET.Element, x: float, y: float, w: float, h: float,
               fill: str, stroke: str, r: float = 18, sw: float = 2) -> None:
    art.element(root, 'rect', x=x, y=y, width=w, height=h, rx=r,
                fill=fill, stroke=stroke, stroke_width=sw)


def coil(root: ET.Element, x1: float, x2: float, y: float, color: str,
         width: float = 3.8, upper: bool = True) -> None:
    """A continuous four-loop, IEEE-like horizontally oriented reactor coil."""
    sign = -1 if upper else 1
    count = 4
    step = (x2 - x1) / count
    pieces = [f'M {x1:g},{y:g}']
    for i in range(count):
        xi = x1 + i * step
        pieces.append(
            f'C {xi + step*.2:g},{y + sign*28:g} '
            f'{xi + step*.8:g},{y + sign*28:g} '
            f'{xi + step:g},{y:g}'
        )
    art.path(root, ' '.join(pieces), color, width)


def horizontal_resistor(root: ET.Element, x1: float, x2: float, y: float,
                        color: str, width: float = 3.8) -> None:
    """Draw the U.S. ANSI/IEEE resistor zigzag."""
    pitch = (x2 - x1) / 8
    pts = [(x1,y), (x1+pitch,y-18), (x1+2*pitch,y+18),
           (x1+3*pitch,y-18), (x1+4*pitch,y+18),
           (x1+5*pitch,y-18), (x1+6*pitch,y+18),
           (x1+7*pitch,y-18), (x2,y)]
    polyline(root,pts,color,width)


def source_symbol(root: ET.Element, cx: float, cy: float, radius: float,
                  color: str, width: float = 3.5) -> None:
    art.element(root,'circle',cx=cx,cy=cy,r=radius,fill=PALETTE['paper'],
                stroke=color,stroke_width=width)
    art.path(root,
             f'M {cx-15:g},{cy:g} C {cx-12:g},{cy-12:g} {cx-5:g},{cy-12:g} {cx:g},{cy:g}'
             f' C {cx+5:g},{cy+12:g} {cx+12:g},{cy+12:g} {cx+15:g},{cy:g}',
             color,2.1)


def scr(root: ET.Element, x: float, cy: float, ident: str,
        color: str, active: bool, direction: str,
        role: str | None = None) -> None:
    """Draw a native Schemdraw SCR rotated along the bridge vertical."""
    ident_group = art.group(root,'scr-'+ident.lower())
    ident_group.set('data-native-symbol','schemdraw.elements.SCR')
    ident_group.set('data-scr',ident)
    ident_group.set('data-active',str(active).lower())
    magnitude = 86.0
    sign = -1 if direction=='up' else 1
    stroke_width = 5.0 if active else 3.6
    def xy(coord: tuple[float, float]) -> tuple[float, float]:
        u, v = coord
        return x + sign*magnitude*v, cy + sign*magnitude*(u-.175)
    top, bottom = cy-.175*magnitude, cy+.175*magnitude
    art.line(ident_group,x,cy-35,x,top,color,stroke_width)
    art.line(ident_group,x,bottom,x,cy+35,color,stroke_width)
    for kind, points in art.SCR_PRIMITIVES:
        if kind=='polygon':
            coords=[xy(pt) for pt in points]
            art.element(ident_group,'polygon',points=' '.join(
                f'{px:.2f},{py:.2f}' for px,py in coords),
                fill='#FFF0F2' if active else 'white',
                stroke=color,stroke_width=stroke_width,stroke_linejoin='round')
            continue
        segment=[]
        for point in (*points,(math.nan,math.nan)):
            if not (math.isfinite(point[0]) and math.isfinite(point[1])):
                if len(segment)>1:
                    polyline(ident_group,segment,color,stroke_width)
                segment=[]
            else:
                segment.append(xy(point))
    # Station prefix avoids ambiguity when both stations use T1..T6.
    art.math_label(ident_group,x+40,cy-10,'T',subscript=ident.replace('_',''),
                   size=20,color=color,bold=True)
    if role in ('OUT','IN'):
        art.txt(ident_group,x-33,cy-45,role,size=16,bold=True,
                anchor='middle',color=PALETTE['amber'] if role=='OUT' else PALETTE['green'])


def overlaid_arrow(root: ET.Element, x1: float, y1: float,
                     x2: float, y2: float, color: str) -> None:
    """Overlay direction arrows on the conductor centerline without offset."""
    art.line(root,x1,y1,x2,y2,color,3.6,marker_end='url(#current-arrow)')


class HVDCLinkRenderer:
    """A stand-alone, fully editable topology drawing for two HVDC stations."""

    def __init__(self, settings: LinkSettings,
                 topology: HVDCLinkTopology | None = None) -> None:
        self.settings = settings
        self.topology = topology or HVDCLinkTopology()

    @staticmethod
    def _defs(root: ET.Element) -> None:
        defs=art.element(root,'defs')
        arrow=art.element(defs,'marker',id='current-arrow',viewBox='0 0 12 12',
                          refX='10',refY='6',markerWidth='5.2',markerHeight='5.2',
                          orient='auto',markerUnits='strokeWidth')
        art.path(arrow,'M 1,1 L 11,6 L 1,11 Z',PALETTE['active'],0,
                 PALETTE['active'])

    @staticmethod
    def _tag(root: ET.Element, eid: str, active: bool) -> ET.Element:
        g=art.group(root,'edge-'+eid.lower())
        g.set('data-edge-id',eid)
        g.set('data-active',str(active).lower())
        return g

    def _header(self, root: ET.Element, state: CombinedState,
                active: frozenset[str]) -> None:
        art.element(root,'rect',x=0,y=0,width=WIDTH,height=HEIGHT,
                    fill=PALETTE['canvas'])
        art.element(root,'rect',x=0,y=0,width=WIDTH,height=137,
                    fill=PALETTE['ink'])
        art.txt(root,75,61,'HVDC LCC  ·  COMPLETE CURRENT PATH',
                size=39,color='white',bold=True)
        art.txt(root,76,108,'Stage 3  ·  6-pulse rectifier → DC link → 6-pulse inverter',
                size=20,color='#BFD5EA')
        art.txt(root,WIDTH-85,57,f'JOINT STATE  {state.number:02d}',
                size=30,color='white',anchor='end',bold=True)
        art.txt(root,WIDTH-85,98,
                f'{state.theta_start:g}° – {state.theta_end:g}°  (global AC reference)',
                size=19,color='#BFD5EA',anchor='end')
        round_rect(root,66,169,1385,1130,'#FFFFFF',PALETTE['line'],20)
        round_rect(root,2047,169,1385,1130,'#FFFFFF',PALETTE['line'],20)
        art.txt(root,94,222,'01  RECTIFIER STATION',size=25,bold=True,
                color=PALETTE['blue'])
        art.txt(root,2080,222,'02  INVERTER STATION',size=25,bold=True,
                color=PALETTE['blue'])
        art.txt(root,94,258,f'αr = {self.settings.alpha_rectifier:g}°   ·   '
                f'μr = {self.settings.mu_rectifier:g}°',size=18,color=PALETTE['quiet'])
        art.txt(root,2080,258,
                f'αi = {self.settings.alpha_inverter:g}°   ·   '
                f'μi = {self.settings.mu_inverter:g}°   ·   '
                f'γi = {self.settings.gamma:g}°',size=18,color=PALETTE['quiet'])
        art.txt(root,94,298,f'R state {state.rectifier.number:02d}: '
                f'{state.rectifier.scr_description}  ·  '
                f'{"Overlap" if state.rectifier_overlap else "Normal"}',
                size=18,color=PALETTE['active'])
        art.txt(root,2080,298,f'I state {state.inverter.number:02d}: '
                f'{state.inverter.scr_description}  ·  '
                f'{"Overlap" if state.inverter_overlap else "Normal"}',
                size=18,color=PALETTE['active'])
        art.txt(root,1750,231,'ONE CONTINUOUS DC LOOP',size=18,bold=True,
                anchor='middle',color=PALETTE['ink'])
        art.txt(root,1750,263,'metallic return (not earth return)',size=15,
                anchor='middle',color=PALETTE['quiet'])
        art.txt(root,1672,342,'+' ,size=29,color=PALETTE['active'],bold=True)
        art.txt(root,1884,342,'+' ,size=29,color=PALETTE['active'],bold=True)
        art.txt(root,1730,1164,'RETURN',size=18,color=PALETTE['quiet'],anchor='middle')

    @staticmethod
    def _neutral(root: ET.Element, x: float, active_phases: set[str]) -> None:
        # The two outer terminals of the neutral star are connected through O.
        y_min, y_max=PHASE_Y['a'],PHASE_Y['c']
        art.line(root,x,y_min,x,y_max,PALETTE['ink'],3.4)
        if len(active_phases)>1:
            y_values=[PHASE_Y[p] for p in active_phases]
            art.line(root,x,min(y_values),x,max(y_values),PALETTE['active'],5.1)
        for phase in 'abc':
            art.dot(root,x,PHASE_Y[phase],phase in active_phases,4.8)
        art.math_label(root,x-18,PHASE_Y['b']-13,'O',size=17,
                       color=PALETTE['quiet'])

    def _transformer(self, root: ET.Element, side: str,
                     active: frozenset[str], arrows: dict[str,int]) -> None:
        coord=T_X[side]
        station=art.layer(root,f'{side} - transformer and AC grid',f'transformer-{side}')
        active_phases={phase for phase in 'abc'
                       if f'{side}_TR_{phase.upper()}' in active}
        art.txt(station,105 if side=='R' else 2850,605,
                '3-PHASE CONVERTER TRANSFORMER',size=16,bold=True,
                color=PALETTE['quiet'])
        art.txt(station,125 if side=='R' else 2962,629,
                'Y/Y  ·  isolated windings  ·  teaching model',size=14,
                color=PALETTE['quiet'])
        pri=coord['primary_coil'];sec=coord['secondary_coil']
        core=coord['core'];lc=coord['leakage']
        art.line(station,coord['primary_neutral'],PHASE_Y['a'],
                 coord['primary_neutral'],PHASE_Y['c'],PALETTE['ink'],3.3)
        self._neutral(station,coord['secondary_neutral'],active_phases)
        for p in 'abc':
            yp=PHASE_Y[p]
            is_active=p in active_phases
            tcolor=PALETTE['active'] if is_active else PALETTE['ink']
            if side=='R':
                # The grid primary and the converter secondary are never wired together.
                art.line(station,coord['grid'],yp,coord['source']-23,yp,PALETTE['ink'],3.3)
                source_symbol(station,coord['source'],yp,23,PALETTE['ink'])
                art.line(station,coord['source']+23,yp,pri[0],yp,PALETTE['ink'],3.3)
                coil(station,*pri,yp,PALETTE['ink'])
                art.line(station,pri[1],yp,coord['primary_neutral'],yp,PALETTE['ink'],3.3)
                art.line(station,coord['secondary_neutral'],yp,sec[0],yp,tcolor,4.9 if is_active else 3.3)
                secondary= self._tag(station,f'R_TR_{p.upper()}',is_active)
                coil(secondary,*sec,yp,tcolor,4.9 if is_active else 3.3)
                art.line(secondary,sec[1],yp,lc[0],yp,tcolor,4.9 if is_active else 3.3)
                leakage=self._tag(station,f'R_LC_{p.upper()}',is_active)
                coil(leakage,*lc,yp,tcolor,4.9 if is_active else 3.3)
                art.line(leakage,lc[1],yp,coord['feed'],yp,tcolor,4.9 if is_active else 3.3)
            else:
                secondary=self._tag(station,f'I_TR_{p.upper()}',is_active)
                art.line(secondary,sec[1],yp,coord['secondary_neutral'],yp,tcolor,4.9 if is_active else 3.3)
                coil(secondary,*sec,yp,tcolor,4.9 if is_active else 3.3)
                leakage=self._tag(station,f'I_LC_{p.upper()}',is_active)
                art.line(leakage,coord['feed'],yp,lc[0],yp,tcolor,4.9 if is_active else 3.3)
                coil(leakage,*lc,yp,tcolor,4.9 if is_active else 3.3)
                art.line(leakage,lc[1],yp,sec[0],yp,tcolor,4.9 if is_active else 3.3)
                art.line(station,coord['primary_neutral'],yp,pri[0],yp,PALETTE['ink'],3.3)
                coil(station,*pri,yp,PALETTE['ink'])
                art.line(station,pri[1],yp,coord['source']-23,yp,PALETTE['ink'],3.3)
                source_symbol(station,coord['source'],yp,23,PALETTE['ink'])
                art.line(station,coord['source']+23,yp,coord['grid'],yp,PALETTE['ink'],3.3)
            for cx in core:
                art.line(station,cx,yp-34,cx,yp+34,PALETTE['quiet'],2.2)
            art.txt(station,coord['grid'] if side=='R' else coord['grid']-4,
                    yp-28,p.upper(),size=18,bold=True,
                    color=PALETTE['ink'])
            xlab=627 if side=='R' else 2787
            art.math_label(station,xlab,yp-29,'L',subscript=f'c,{p}{side.lower()}',
                           size=17,color=tcolor,anchor='middle')
            if is_active:
                direction=arrows.get(f'{side}_LC_{p.upper()}',0)
                if direction:
                    # The physical R winding goes left-to-right; I goes right-to-left.
                    left,right=(644,662) if side=='R' else (2734,2752)
                    positive= direction if side=='R' else -direction
                    (x1,x2)=(left,right) if positive>0 else (right,left)
                    overlaid_arrow(station,x1,yp,x2,yp,PALETTE['active'])
        art.txt(station,60 if side=='R' else 3275,960,
                'AC GRID' if side=='R' else 'AC GRID',
                size=18,color=PALETTE['quiet'],bold=True)

    @staticmethod
    def _feeder_path(xstart: float, xend: float, y: float,
                     crosses: list[float]) -> str:
        """Insulated jump arcs at nonconnected phase/valve wire crossings."""
        direction=1 if xend>xstart else -1
        crossings=sorted(crosses,reverse=(direction<0))
        parts=[f'M {xstart:g},{y:g}']
        for x in crossings:
            parts.append(f'L {x-direction*19:g},{y:g}')
            parts.append(f'C {x-direction*13:g},{y-17:g} '
                         f'{x+direction*13:g},{y-17:g} {x+direction*19:g},{y:g}')
        parts.append(f'L {xend:g},{y:g}')
        return ' '.join(parts)

    def _bridge(self, root: ET.Element, side: str,
                state: CombinedState, active: frozenset[str]) -> None:
        columns=COLUMNS[side]
        sel=state.rectifier if side=='R' else state.inverter
        upper_active={s for s in sel.scrs if s in UPPER.values()}
        lower_active={s for s in sel.scrs if s in LOWER.values()}
        rdir='up' if side=='R' else 'down'
        valve=art.layer(root,side+' - bridge valves and nodes',f'bridge-{side}')
        xs=list(columns.values())
        # Use explicit upper and lower bridges; never connect AC phase crosses.
        art.line(valve,xs[0],Y_P,xs[-1],Y_P,PALETTE['ink'],3.6)
        art.line(valve,xs[0],Y_N,xs[-1],Y_N,PALETTE['ink'],3.6)
        if side=='R':
            for idx in range(2):
                if any(UPPER[p] in upper_active for p in 'abc'[:idx+1]):
                    art.line(valve,xs[idx],Y_P,xs[idx+1],Y_P,PALETTE['active'],5.1)
                if any(LOWER[p] in lower_active for p in 'abc'[:idx+1]):
                    art.line(valve,xs[idx],Y_N,xs[idx+1],Y_N,PALETTE['active'],5.1)
        else:
            for idx in range(2):
                if any(UPPER[p] in upper_active for p in 'abc'[idx+1:]):
                    art.line(valve,xs[idx],Y_P,xs[idx+1],Y_P,PALETTE['active'],5.1)
                if any(LOWER[p] in lower_active for p in 'abc'[idx+1:]):
                    art.line(valve,xs[idx],Y_N,xs[idx+1],Y_N,PALETTE['active'],5.1)
        for phase, xc in columns.items():
            yp=PHASE_Y[phase]
            high,low=UPPER[phase],LOWER[phase]
            high_on=f'{side}_{high}' in active
            low_on=f'{side}_{low}' in active
            hcol=PALETTE['active'] if high_on else PALETTE['ink']
            lcol=PALETTE['active'] if low_on else PALETTE['ink']
            art.line(valve,xc,Y_P,xc,Y_TOP-35,hcol,5.1 if high_on else 3.4)
            art.line(valve,xc,Y_TOP+35,xc,yp,hcol,5.1 if high_on else 3.4)
            art.line(valve,xc,yp,xc,Y_BOTTOM-35,lcol,5.1 if low_on else 3.4)
            art.line(valve,xc,Y_BOTTOM+35,xc,Y_N,lcol,5.1 if low_on else 3.4)
            upper_role=(
                'OUT' if sel.outgoing==high else 'IN' if sel.incoming==high else None
            )
            lower_role=(
                'OUT' if sel.outgoing==low else 'IN' if sel.incoming==low else None
            )
            scr(valve,xc,Y_TOP,f'{side}_{high}',hcol,high_on,rdir,upper_role)
            scr(valve,xc,Y_BOTTOM,f'{side}_{low}',lcol,low_on,rdir,lower_role)
            art.dot(valve,xc,Y_P,high_on,5.1)
            art.dot(valve,xc,Y_N,low_on,5.1)
            art.dot(valve,xc,yp,high_on or low_on,6.0)
        # Each phase feeder jumps over unrelated vertical valve conductors.
        # The white halo at the arc protects the unconnected crossing point.
        feeders=art.layer(root,side+' - phase crossings',f'feeders-{side}')
        for p in 'abc':
            xend=columns[p]
            xstart=T_X[side]['feed']
            crosses=[columns[q] for q in 'abc' if (columns[q]-xstart)*(columns[q]-xend)<0]
            data=self._feeder_path(xstart,xend,PHASE_Y[p],crosses)
            selected=(f'{side}_LC_{p.upper()}' in active)
            if crosses:
                for cross in crosses:
                    # Local white/colored crossover hump, not a junction.
                    local=self._feeder_path(cross-21 if xend>xstart else cross+21,
                                            cross+21 if xend>xstart else cross-21,
                                            PHASE_Y[p],[cross])
                    art.path(feeders,local,PALETTE['paper'],11)
            art.path(feeders,data,PALETTE['ink'],3.6)
            if selected:
                art.path(feeders,data,PALETTE['active'],5.1)
            # Redraw the connected final valve phase dot.
            art.dot(feeders,xend,PHASE_Y[p],selected,5.4)
        # Direction labels identify the same current arrow in both stations.
        art.txt(valve,(xs[0]+xs[-1])/2,400,
                'VALVE GROUP +',size=15,color=PALETTE['quiet'],anchor='middle')
        art.txt(valve,(xs[0]+xs[-1])/2,1173,
                'VALVE GROUP −',size=15,color=PALETTE['quiet'],anchor='middle')

    def _dc_link(self, root: ET.Element,
                 active: frozenset[str]) -> None:
        dc=art.layer(root,'DC transmission conductors and smoothing reactors','dc-link')
        xcR=COLUMNS['R']['c']
        xcI=COLUMNS['I']['a']
        # The two directional paths are continuous and are NEVER earth-return.
        plus=PALETTE['active'] if 'L_DR' in active else PALETTE['ink']
        neg=PALETTE['active'] if 'METALLIC_RETURN' in active else PALETTE['ink']
        w=5.1 if 'L_DR' in active else 3.6
        art.line(dc,xcR,Y_P,1425,Y_P,plus,w)
        coil(dc,1425,1550,Y_P,plus,w)
        art.line(dc,1550,Y_P,1695,Y_P,plus,w)
        horizontal_resistor(dc,1695,1795,Y_P,plus,w)
        art.line(dc,1795,Y_P,1975,Y_P,plus,w)
        coil(dc,1975,2100,Y_P,plus,w)
        art.line(dc,2100,Y_P,xcI,Y_P,plus,w)
        art.line(dc,xcI,Y_N,xcR,Y_N,neg,5.1 if 'METALLIC_RETURN' in active else 3.6)
        for eid in ('L_DR','R_LINE','L_DI','METALLIC_RETURN'):
            tag=self._tag(dc,eid,eid in active)
            tag.set('data-rendered-as','continuous-dc-link')
        art.math_label(dc,1482,317,'L',subscript='d,r',size=22,color=plus,
                       anchor='middle')
        art.math_label(dc,1745,315,'R',subscript='line',size=22,color=plus,
                       anchor='middle',upright_subscript=True)
        art.math_label(dc,2035,317,'L',subscript='d,i',size=22,color=plus,
                       anchor='middle')
        art.math_label(dc,1745,1098,'I',subscript='dc',size=25,color=neg,
                       anchor='middle',upright_subscript=True)
        art.txt(dc,1750,441,'POSITIVE DC CONDUCTOR',size=17,
                color=PALETTE['quiet'],anchor='middle')
        if 'L_DR' in active:
            overlaid_arrow(dc,1605,Y_P,1644,Y_P,plus)
            overlaid_arrow(dc,1830,Y_P,1875,Y_P,plus)
        if 'METALLIC_RETURN' in active:
            overlaid_arrow(dc,1940,Y_N,1895,Y_N,neg)
            overlaid_arrow(dc,1570,Y_N,1520,Y_N,neg)
        # A real line has distributed RLC and possible electrodes/returns;
        # here only a lumped resistance and an explicit metallic conductor exist.

    def _current_arrows(self, root: ET.Element, state: CombinedState,
                        active: frozenset[str]) -> None:
        annotations=art.layer(root,'On-wire current direction','on-wire-arrows')
        for side in ('R','I'):
            sel=state.rectifier if side=='R' else state.inverter
            for phase,x in COLUMNS[side].items():
                if UPPER[phase] in sel.scrs:
                    if side=='R':
                        overlaid_arrow(annotations,x,Y_TOP+120,x,Y_TOP+72,PALETTE['active'])
                    else:
                        overlaid_arrow(annotations,x,Y_TOP+74,x,Y_TOP+122,PALETTE['active'])
                if LOWER[phase] in sel.scrs:
                    if side=='R':
                        overlaid_arrow(annotations,x,Y_BOTTOM+92,x,Y_BOTTOM+45,PALETTE['active'])
                    else:
                        overlaid_arrow(annotations,x,Y_BOTTOM+44,x,Y_BOTTOM+90,PALETTE['active'])
        art.math_label(annotations,1750,524,'I',subscript='dc',size=25,
                       color=PALETTE['active'],anchor='middle',upright_subscript=True)
        art.txt(annotations,1750,550,'Conventional current: rectifier → inverter',
                size=17,color=PALETTE['quiet'],anchor='middle')
        art.txt(annotations,1750,578,'The same current returns through the lower conductor.',
                size=15,color=PALETTE['quiet'],anchor='middle')

    def _footer(self, root: ET.Element, state: CombinedState,
                active: frozenset[str], loop_count: int) -> None:
        # Shallow footer strips, kept outside the physical circuit.
        round_rect(root,67,1323,3366,156,'#FFFFFF',PALETTE['line'],14,2)
        art.txt(root,94,1363,'TEACHING MODE  ·  SIX-PULSE PER STATION',
                size=19,color=PALETTE['ink'],bold=True)
        art.txt(root,94,1402,state.name,size=19,color=PALETTE['active'])
        art.txt(root,94,1441,
                f'{len([e for e in active if self.topology.edges[e].kind == "scr"])} conducting SCRs '
                f'· {loop_count} graph-validated conducting path(s)',
                size=16,color=PALETTE['quiet'])
        art.txt(root,1350,1364,
                f'αr = {self.settings.alpha_rectifier:g}°   ·  '
                f'αi = {self.settings.alpha_inverter:g}°   ·  '
                f'γi ≈ {self.settings.gamma:g}°',
                size=18,color=PALETTE['ink'])
        art.txt(root,1350,1405,
                f'μr = {self.settings.mu_rectifier:g}°   ·  '
                f'μi = {self.settings.mu_inverter:g}°   ·  '
                f'AC phase offset = {self.settings.ac_phase_offset:g}°',
                size=17,color=PALETTE['quiet'])
        art.txt(root,1350,1443,
                'Transformer primaries are galvanically isolated from the conducting valve-side loops.',
                size=16,color=PALETTE['quiet'])
        art.txt(root,WIDTH-93,1372,'NO CURRENT SHARING SOLVED',
                size=16,color=PALETTE['amber'],anchor='end',bold=True)
        art.txt(root,WIDTH-93,1410,'Red = potentially conducting branches',
                size=16,color=PALETTE['quiet'],anchor='end')
        art.txt(root,WIDTH-93,1443,'NOT a 12-pulse or EMT model',
                size=16,color=PALETTE['quiet'],anchor='end')

    def render(self, state: CombinedState) -> ET.ElementTree:
        selection=self.topology.highlight(state)
        active=selection['active']
        directed=selection['directions']
        assert isinstance(active,frozenset) and isinstance(directed,dict)
        root=ET.Element(art.S+'svg',{
            'width':str(WIDTH),'height':str(HEIGHT),
            'viewBox':f'0 0 {WIDTH} {HEIGHT}',
            'version':'1.1',
        })
        svg_title(root,'Full LCC HVDC circuit — '+state.name,
                  'Two three-phase, two-winding converter transformers, '
                  'a six-pulse rectifier, two smoothing reactors, line resistance, '
                  'a six-pulse inverter, and a metallic return. '
                  'The red line is the union of validated complete electrical current loops.')
        self._defs(root)
        self._header(root,state,active)
        self._dc_link(root,active)
        self._bridge(root,'R',state,active)
        self._bridge(root,'I',state,active)
        self._transformer(root,'R',active,directed)
        self._transformer(root,'I',active,directed)
        self._current_arrows(root,state,active)
        self._footer(root,state,active,int(selection['loop_count']))
        ET.indent(root,space='  ')
        return ET.ElementTree(root)

    @staticmethod
    def save(tree: ET.ElementTree, path: Path) -> None:
        path.parent.mkdir(parents=True,exist_ok=True)
        tree.write(path,encoding='utf-8',xml_declaration=True)
