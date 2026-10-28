"""Editable extension of the original, graph-validated R/RL bridge drawings.

Only the series DC load subcircuit is replaced; SCR geometry and the conducting
pair continue to come from the repository's existing circuit renderer.
"""
from __future__ import annotations
import xml.etree.ElementTree as ET

import rectifier_art as art
from rectifier_loads import LoadParameters, ResistiveCircuitRenderer


def render_extended_load(renderer: ResistiveCircuitRenderer, parameters: LoadParameters,
                         angle: float, pair: int | None, mode: str) -> ET.ElementTree:
    """Render R, RL, LE or RLE without depicting a resistor in an LE branch."""
    if mode in ('R', 'RL'):
        return renderer.render(parameters, angle, pair, mode)
    if mode not in ('LE', 'RLE'):
        raise ValueError(f'Unsupported load {mode}')
    tree = renderer.render(parameters, angle, pair, 'RL')
    root = tree.getroot()
    ids = {
        f'{prefix}-{name}'
        for prefix in ('base', 'selected')
        for name in ('r', 'carga_l_r', 'carga_r_neg')
    }
    for parent in root.iter():
        for child in list(parent):
            if child.get('id') in ids:
                parent.remove(child)
            if (parent.get('id') == 'annotations' and child.tag == art.S+'text'
                    and child.get('x') == '1285' and child.get('y') == '489'):
                parent.remove(child)
    base = root.find(f'.//{art.S}g[@id="components-base"]')
    active = root.find(f'.//{art.S}g[@id="components-active"]')
    if base is None or active is None:
        raise ValueError('Base circuit component layers are missing')

    def wire(parent: ET.Element, a: float, b: float, color: str, width: float) -> None:
        art.line(parent, 1240, a, 1240, b, color, width)

    def emf(parent: ET.Element, cy: float, color: str, width: float) -> None:
        group = art.group(parent, 'source-emf-' + ('active' if parent is active else 'base'))
        radius = 30
        art.element(group, 'circle', cx=1240, cy=cy, r=radius,
                    fill=art.C['paper'], stroke=color, stroke_width=width)
        art.line(group, 1227, cy-12, 1253, cy-12, color, width*0.7)
        art.line(group, 1240, cy-23, 1240, cy-1, color, width*0.7)
        art.line(group, 1230, cy+13, 1250, cy+13, color, width*0.7)

    def resistor(parent: ET.Element, y1: float, y2: float, color: str, width: float) -> None:
        x = 1240
        points = [(x,y1),(x,y1+7),(x-13,y1+15),(x+13,y1+24),
                  (x-13,y1+33),(x+13,y1+42),(x-13,y1+51),(x,y2-6),(x,y2)]
        art.path(parent, 'M '+ ' L '.join(f'{a},{b}' for a,b in points), color, width)

    for parent, color, width in ((base,art.C['ink'],3.4),
                                  (active,art.C['active'],4.8)):
        if parent is active and pair is None:
            continue
        if mode == 'LE':
            wire(parent,373,464,color,width)
            emf(parent,494,color,width)
            wire(parent,524,662,color,width)
        else:
            wire(parent,373,408,color,width)
            resistor(parent,408,472,color,width)
            wire(parent,472,512,color,width)
            emf(parent,542,color,width)
            wire(parent,572,662,color,width)
    annotations = root.find(f'.//{art.S}g[@id="annotations"]')
    art.math_label(annotations,1284,554 if mode=='RLE' else 504,'E',subscript='dc',
                   upright_subscript=True,size=22)
    if mode=='RLE':
        art.math_label(annotations,1284,446,'R',size=23)
    headings=root.find(f'.//{art.S}g[@id="headings"]')
    for item in headings:
        if item.tag == art.S+'text' and 'RECTIFIER' in (item.text or ''):
            item.text='RECTIFIER · '+mode+' LOAD'
            break
    desc=art.element(root, 'desc')
    desc.text=(mode+' DC branch: top-to-bottom inductor, '+
               ('resistor, ' if mode=='RLE' else '')+
               'ideal signed EMF source. Positive E opposes positive DC current.')
    return tree
