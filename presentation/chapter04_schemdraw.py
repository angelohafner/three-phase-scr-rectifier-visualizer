#!/usr/bin/env python3
"""Build Chapter 04 SVG circuits from actual Schemdraw 0.23 element instances.

Electrical component shapes are never authored by hand. Native element
segments are placed at explicit electrical terminals; custom SVG is restricted
to wires, labels, insulation crossover arcs, and interactive annotations.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from xml.etree import ElementTree as ET

import schemdraw
import schemdraw.elements as elm

import sys
# Allow execution by path while importing the shared repository-root symbol renderer.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import schemdraw_symbols as native

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
INK = "#274b61"
MUTED = "#537388"
RED = "#c43e59"
ACCENT = "#167f91"
PHASE_Y = (152.0, 282.0, 412.0)
PHASE_X = (590.0, 715.0, 840.0)
PHASES = "abc"
VIEW_W, VIEW_H = 1080, 564
REQUIRED = ("SCR", "SourceSin", "SourceI", "Inductor",
            "Capacitor", "ResistorIEEE", "Transformer", "Ground", "Dot")


def add(parent: ET.Element, tag: str, **attrs: object) -> ET.Element:
    return ET.SubElement(parent, f"{{{NS}}}{tag}",
                         {k.replace("_", "-"): str(v) for k, v in attrs.items()
                          if v is not None})


def label(parent: ET.Element, x: float, y: float, value: str,
          *, size: int = 14, color: str = INK, key: str | None = None) -> None:
    add(parent, "text", x=f"{x:.3f}", y=f"{y:.3f}", fill=color,
        font_family="Segoe UI, Arial, sans-serif", font_size=size,
        id=key).text = value


def wire(parent: ET.Element, path: str, *, name: str | None = None,
         phase: str | None = None) -> ET.Element:
    return add(parent, "path", d=path, stroke=INK, fill="none",
               stroke_width=2.8, stroke_linecap="round",
               stroke_linejoin="round", id=name,
               data_wire_phase=phase)


def segment(parent: ET.Element, x1: float, y1: float,
            x2: float, y2: float, *, name: str | None = None,
            phase: str | None = None) -> ET.Element:
    return wire(parent, f"M {x1:.3f},{y1:.3f} L {x2:.3f},{y2:.3f}",
                name=name, phase=phase)


def jump_path(start: float, end: float, y: float,
              crossing_x: list[float]) -> str:
    """Continuous insulated wire bridges over nonconnecting vertical wires."""
    d = f"M {start:.3f},{y:.3f}"
    for x in crossing_x:
        if not start + 8 < x < end - 8:
            continue
        d += (f" L {x-10:.3f},{y:.3f}"
              f" Q {x:.3f},{y-21:.3f} {x+10:.3f},{y:.3f}")
    return d + f" L {end:.3f},{y:.3f}"


def native_two(parent: ET.Element, cls: str, start: tuple[float, float],
               end: tuple[float, float], key: str, phase: str | None = None,
               transverse: float | None = None) -> ET.Element:
    group = native.draw_component(
        parent, cls, start, end, INK, 2.6,
        transverse_scale=transverse, group_id=key,
        require_library=True,
    )
    group.set("data-role", "component")
    if phase:
        group.set("data-phase", phase)
    return group


def arbitrary_native(parent: ET.Element, obj: object, name: str,
                     transform, group_id: str, *,
                     fill: str = "none") -> ET.Element:
    """Convert Schemdraw's *own* Segment objects, not redrawn symbols."""
    g = add(parent, "g", id=group_id, data_symbol="schemdraw.elements." + name,
            data_symbol_source="native-instance", data_role="component")
    for item in obj.segments:
        if hasattr(item, "path"):
            path: list[tuple[float, float]] = []
            def flush():
                if len(path) > 1:
                    xy = " L ".join(f"{x:.3f},{y:.3f}" for x, y in path)
                    add(g, "path", d="M " + xy, stroke=INK,
                        stroke_width=2.6, fill="none", stroke_linecap="round")
                path.clear()
            for p in list(item.path) + [(math.nan, math.nan)]:
                x, y = float(p[0]), float(p[1])
                if math.isfinite(x) and math.isfinite(y):
                    path.append(transform((x, y)))
                else:
                    flush()
        elif hasattr(item, "verts"):
            pts = [transform((float(p[0]), float(p[1]))) for p in item.verts]
            add(g, "polygon", points=" ".join(
                f"{x:.3f},{y:.3f}" for x, y in pts),
                stroke=INK, stroke_width=2.6, fill=fill)
        elif hasattr(item, "center") and hasattr(item, "radius"):
            cx, cy = transform(tuple(item.center))
            rr = math.dist(transform((0.0, 0.0)), transform((float(item.radius), 0.0)))
            add(g, "circle", cx=f"{cx:.3f}", cy=f"{cy:.3f}",
                r=f"{rr:.3f}", stroke=INK, stroke_width=2.6, fill=fill)
        elif hasattr(item, "center") and hasattr(item, "theta1"):
            cx, cy = item.center
            rotation = math.radians(getattr(item, "angle", 0))
            coords: list[tuple[float, float]] = []
            for k in range(41):
                theta = math.radians(item.theta1 +
                                    (item.theta2 - item.theta1) * k / 40)
                xx = item.width / 2 * math.cos(theta)
                yy = item.height / 2 * math.sin(theta)
                coords.append(transform(
                    (cx + xx * math.cos(rotation) - yy * math.sin(rotation),
                     cy + xx * math.sin(rotation) + yy * math.cos(rotation))))
            add(g, "path", d="M " + " L ".join(
                f"{x:.3f},{y:.3f}" for x, y in coords),
                stroke=INK, stroke_width=2.6, fill="none")
        else:
            raise TypeError(f"Unsupported native Schemdraw segment: {type(item).__name__}")
    return g



def native_capacitor(parent: ET.Element, start: tuple[float,float],
                     end: tuple[float,float], key: str, phase: str,
                     transverse: float) -> ET.Element:
    """Center actual native capacitor plates and close both terminal conductors.

    Schemdraw's Capacitor segments contain two plates, not built-in leads.
    Their native path x coordinates determine the exact contact points; this
    avoids any visually convincing but electrically open wire gaps.
    """
    obj=elm.Capacitor()
    xvals=sorted({round(float(p[0]),9) for segment in obj.segments
                  if hasattr(segment,"path") for p in segment.path
                  if math.isfinite(float(p[0])) and math.isfinite(float(p[1]))})
    if len(xvals)!=2 or xvals[1]<=xvals[0]:
        raise RuntimeError("Unexpected native capacitor plate geometry")
    dx,dy=end[0]-start[0],end[1]-start[1]
    length=math.hypot(dx,dy)
    if length<14:raise RuntimeError("Capacitor branch too short")
    ux,uy=dx/length,dy/length
    vx,vy=-uy,ux
    midx,midy=(start[0]+end[0])/2,(start[1]+end[1])/2
    gap=min(12.,length/3)
    native_center=(xvals[0]+xvals[1])/2
    def transform(p):
        longitudinal=(float(p[0])-native_center)*gap/(xvals[1]-xvals[0])
        cross=float(p[1])*transverse
        return midx+longitudinal*ux+cross*vx,midy+longitudinal*uy+cross*vy
    group=arbitrary_native(parent,obj,"Capacitor",transform,key)
    group.set("data-phase",phase)
    group.set("data-terminal-start",f"{start[0]:.3f},{start[1]:.3f}")
    group.set("data-terminal-end",f"{end[0]:.3f},{end[1]:.3f}")
    plate_left=transform((xvals[0],0))
    plate_right=transform((xvals[1],0))
    group.set("data-contact-left",f"{plate_left[0]:.3f},{plate_left[1]:.3f}")
    group.set("data-contact-right",f"{plate_right[0]:.3f},{plate_right[1]:.3f}")
    segment(parent,*start,*plate_left,name=key+"-lead-in",phase=phase)
    segment(parent,*plate_right,*end,name=key+"-lead-out",phase=phase)
    return group


def transformer(parent: ET.Element, x: float, top: float,
                phase: str) -> dict[str, tuple[float, float]]:
    """Place a native two-winding Transformer using its real winding anchors."""
    obj = elm.Transformer(t1=4, t2=4, core=True)
    anchors = obj.anchors
    for name in ("p1", "p2", "s1", "s2"):
        if name not in anchors:
            raise RuntimeError(f"Native transformer lacks {name} anchor")
    p1, p2 = anchors["p1"], anchors["p2"]
    delta = float(p1[1]) - float(p2[1])
    if delta <= 0:
        raise RuntimeError("Native transformer winding anchors have reversed polarity")
    factor = 60.0 / delta
    def convert(point):
        return (x + (float(point[0])-float(p1[0]))*factor,
                top + (float(p1[1])-float(point[1]))*factor)
    group = arbitrary_native(parent, obj, "Transformer", convert,
                             f"transformer-{phase}")
    group.set("data-phase", phase)
    ends = {name:convert(anchors[name]) for name in ("p1","p2","s1","s2")}
    for name, point in ends.items():
        group.set("data-anchor-" + name, f"{point[0]:.3f},{point[1]:.3f}")
    label(parent, x-8, top-11, f"T{phase.upper()}", size=12, color=MUTED)
    return ends


def native_ground(parent: ET.Element, x: float, y: float,
                  key: str) -> ET.Element:
    obj = elm.Ground()
    group = arbitrary_native(parent, obj, "Ground",
                             lambda p:(x + float(p[0])*28,
                                       y - float(p[1])*28), key)
    return group


def native_dot(parent: ET.Element, x: float, y: float, key: str) -> ET.Element:
    obj = elm.Dot()
    return arbitrary_native(parent, obj, "Dot",
                            lambda p:(x+float(p[0])*20,
                                      y-float(p[1])*20),
                            key, fill=INK)


def bridge(parent: ET.Element, x: float, phase: str) -> None:
    positive, negative = 34.0, 513.0
    node, upper, lower = PHASE_Y[PHASES.index(phase)]-30, 88.0, 449.0
    scr_u = native_two(parent,"SCR",(x,upper+19),(x,upper-19),
                       "scr-" + ("T1" if phase=="a" else "T3" if phase=="b" else "T5"),
                       phase, transverse=34)
    scr_l = native_two(parent,"SCR",(x,lower+19),(x,lower-19),
                       "scr-" + ("T2" if phase=="a" else "T4" if phase=="b" else "T6"),
                       phase, transverse=34)
    scr_u.set("data-role","scr")
    scr_l.set("data-role","scr")
    scr_u.set("data-valve", ("T1" if phase=="a" else "T3" if phase=="b" else "T5"))
    scr_l.set("data-valve", ("T2" if phase=="a" else "T4" if phase=="b" else "T6"))
    segment(parent,x,positive,x,upper-19)
    segment(parent,x,upper+19,x,node)
    segment(parent,x,node,x,lower-19)
    segment(parent,x,lower+19,x,negative)
    native_dot(parent,x,node,f"junction-{phase}")
    label(parent,x+23,upper-9,scr_u.get("data-valve"),size=15)
    label(parent,x+23,lower-9,scr_l.get("data-valve"),size=15)


def one(caps: bool, shunt: bool) -> tuple[str, dict]:
    if not native.SCHEMDRAW_AVAILABLE:
        raise RuntimeError("Chapter 04 requires actual Schemdraw, no fallback.")
    for name in REQUIRED:
        if not hasattr(elm,name):
            raise RuntimeError(f"Native Schemdraw 0.23 lacks {name}")
    root = ET.Element(f"{{{NS}}}svg", {
        "viewBox":f"0 0 {VIEW_W} {VIEW_H}",
        "role":"img",
        "aria-label":"Native Schemdraw three-phase transformer, six SCR valves, "
                     "series capacitor bank and external DC current source",
        "data-generator":"chapter04_schemdraw.py",
        "data-library":"schemdraw",
        "data-native-symbols":"true",
        "data-topology":"CCC" if caps else "LCC",
        "data-shunt":"true" if shunt else "false",
    })
    add(root, "title").text = (
        "Capacitor-commutated six-pulse bridge" if caps
        else "Conventional six-pulse line-commutated bridge"
    )
    add(root, "desc").text = (
        "Three idealized transformer windings, each with a physical leakage "
        "inductor and resistance. CCC includes one dynamic series capacitor "
        "per AC phase; LCC bypasses these elements. SCR polarities and "
        "the isolated DC positive/negative rails are explicit. "
        "The electromagnetic transformer equivalent itself is not solved."
    )
    add(root,"rect",x=0,y=0,width=VIEW_W,height=VIEW_H,fill="#ffffff")
    label(root,21,23,"AC NETWORK / THREE SYMBOLIC ISOLATED TRANSFORMERS",size=14)
    label(root,538,23,"SIX-PULSE VALVE BRIDGE",size=14)
    label(root,886,23,"DC LINK",size=14)
    ac_primary = add(root,"g",id="ac-primary")
    phases = add(root,"g",id="phase-components")
    winding_stars = add(root,"g",id="secondary-star")
    wires = add(root,"g",id="phase-wiring")
    valves = add(root,"g",id="valves")
    dcp = add(root,"g",id="dc-link")
    notes = add(root,"g",id="dynamic-annotations")
    neutral_primary: list[float] = []
    neutral_secondary: list[tuple[float,float]] = []
    phase_sources: list[tuple[float,float]]=[]
    capacitor_info: dict[str,dict] = {}
    for index, phase in enumerate(PHASES):
        y = PHASE_Y[index]
        top, bottom = y-30.0, y+30.0
        label(ac_primary,27,top-13,phase.upper(),size=17)
        source = native_two(ac_primary,"SourceSin",(73,bottom-12),(73,top+12),
                            f"source-{phase}",phase,transverse=37)
        source.set("data-role","ac-source")
        segment(ac_primary,73,top,73,top+12)
        segment(ac_primary,73,bottom-12,73,bottom)
        # Source and transformer primary share the same two-terminal AC voltage.
        T=transformer(ac_primary,212,top,phase)
        segment(ac_primary,73,top,T["p1"][0],T["p1"][1])
        segment(ac_primary,73,bottom,T["p2"][0],T["p2"][1])
        segment(ac_primary,24,bottom,73,bottom)
        neutral_primary.append(bottom)
        if shunt:
            g = native_capacitor(ac_primary,(132,top+14),(132,bottom-14),
                                 f"shunt-{phase}",phase,transverse=39)
            g.set("data-role","shunt-capacitor")
            segment(ac_primary,132,top,132,top+14)
            segment(ac_primary,132,bottom-14,132,bottom)
        s1,s2 = T["s1"],T["s2"]
        neutral_secondary.append(s2)
        phase_sources.append(s1)
    segment(ac_primary,24,neutral_primary[0],24,neutral_primary[-1]+37)
    native_ground(ac_primary,24,neutral_primary[-1]+37,"ground-primary")
    # Secondary winding terminals form a genuine three-phase star neutral.
    star_x=max(s[0] for s in phase_sources)+21.0
    if star_x >= 338:
        raise RuntimeError(f"Transformer too wide for drawing: neutral at {star_x}")
    for point in neutral_secondary:
        segment(winding_stars,point[0],point[1],star_x,point[1])
    segment(winding_stars,star_x,neutral_secondary[0][1],
            star_x,neutral_secondary[-1][1]+63)
    native_ground(winding_stars,star_x,neutral_secondary[-1][1]+63,
                  "ground-secondary")
    # The upper terminal of each secondary winding crosses the insulated
    # neutral star bus but does not connect to it.
    for index,phase in enumerate(PHASES):
        y=PHASE_Y[index]-30
        s1=phase_sources[index]
        wire(wires,jump_path(s1[0],352,y,[star_x]),
             name=f"feed-{phase}-pre",phase=phase)
        g=native_two(phases,"Inductor",(352,y),(405,y),
                     f"leakage-{phase}",phase,transverse=32)
        g.set("data-role","leakage-inductor")
        segment(wires,405,y,420,y,phase=phase)
        r=native_two(phases,"ResistorIEEE",(420,y),(462,y),
                     f"resistance-{phase}",phase,transverse=27)
        r.set("data-role","phase-resistance")
        segment(wires,462,y,478,y,phase=phase)
        if caps:
            capacitor=native_capacitor(phases,(478,y),(523,y),
                                       f"series-{phase}",phase,transverse=48)
            capacitor.set("data-role","series-capacitor")
        else:
            segment(wires,478,y,523,y,phase=phase)
            label(notes,477,y-22,"BYPASS",size=12,color=MUTED)
        # Each branch crosses the earlier vertical valve legs with insulation
        # arcs. None of these crossings is an electrical junction.
        crosses=list(PHASE_X[:index])
        wire(wires,jump_path(523,PHASE_X[index],y,crosses),
             name=f"feed-{phase}-post",phase=phase)
        label(notes,435,y+60,f"i{phase} = 0.00",size=14,
              key=f"live-current-{phase}")
        if caps:
            label(notes,472,y+34,f"vC{phase} = 0.00",size=13,
                  key=f"live-capacitor-{phase}")
        capacitor_info[phase]={"phase_input":s1,"valve_node":[PHASE_X[index],y]}
    segment(dcp,PHASE_X[0],34,990,34,name="bus-dc-positive")
    segment(dcp,PHASE_X[0],513,990,513,name="bus-dc-negative")
    for phase,x in zip(PHASES,PHASE_X):
        bridge(valves,x,phase)
    smoothing=native_two(dcp,"Inductor",(990,118),(990,182),
                         "smoothing-inductor",transverse=43)
    smoothing.set("data-role","dc-smoothing")
    sink=native_two(dcp,"SourceI",(990,310),(990,391),
                    "dc-current-source",transverse=79)
    sink.set("data-role","dc-current-source")
    segment(dcp,990,34,990,118)
    segment(dcp,990,182,990,310)
    segment(dcp,990,391,990,513)
    label(notes,1009,49,"DC +",size=15)
    label(notes,1009,507,"DC −",size=15)
    label(notes,1007,162,"Ldc",size=14)
    label(notes,1015,362,"Idc",size=15)
    label(notes,351,91,"Lc  +  R  +  C" if caps else "Lc  +  R  (C BYPASSED)",size=13)
    label(notes,29,555,"Transformer winding geometry is symbolic; its electromagnetic dynamics are not simulated.",size=12,color=MUTED)
    if shunt:
        label(notes,114,48,"3φ shunt bank",size=13,color=ACCENT)
        label(notes,114,66,"Q shunt = 0.00 p.u.",size=12,
              color=ACCENT,key="live-shunt")
    manifest = {
        "generator":"presentation/chapter04_schemdraw.py",
        "native_library":str(getattr(schemdraw,"__version__","installed")),
        "native_required":list(REQUIRED),
        "topology":"CCC" if caps else "LCC",
        "shunt":shunt,
        "valve_order":["T1","T3","T5","T2","T4","T6"],
        "series_capacitors":3 if caps else 0,
        "shunt_capacitors":3 if shunt else 0,
        "source_reference":"AC sources on symbolic transformer primaries; dynamic e_k is the referred secondary voltage",
        "current_reference":"DC current sink oriented from DC+ toward DC−",
        "phase_nodes":capacitor_info,
        "dc_positive_y":34,
        "dc_negative_y":513,
    }
    text=ET.tostring(root,encoding="unicode",xml_declaration=False)
    ET.fromstring(text)
    if text.count('data-symbol-source="native-instance"') < 24:
        raise RuntimeError("Native Schemdraw component provenance missing")
    return text,manifest


def generate_assets(output: Path) -> dict[str,str]:
    output.mkdir(parents=True,exist_ok=True)
    result={}
    for caps in (False,True):
        for shunt in (False,True):
            name=("ccc" if caps else "lcc")+("_shunt" if shunt else "")
            svg,manifest=one(caps,shunt)
            (output/(name+".svg")).write_text(svg,encoding="utf-8")
            (output/(name+".manifest.json")).write_text(
                json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            result[name]=svg
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,
                        default=Path(__file__).parent/"assets"/"chapter04")
    args=parser.parse_args()
    result=generate_assets(args.output_dir)
    print(f"Generated {len(result)} native Schemdraw Chapter 04 SVG circuits")


if __name__=="__main__":
    main()
