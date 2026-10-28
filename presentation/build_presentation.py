#!/usr/bin/env python3
"""Build a one-file offline LCC HVDC slide deck from existing project SVGs."""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

SVG_NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG_NS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

def svg_xml(source: str, *, hvdc: bool = False) -> str:
    """Normalize a trusted SVG and remove nominal-time text annotations."""
    raw = re.sub(r'<\?xml[^>]*\?>', '', source, count=1).lstrip()
    raw = re.sub(r'<!DOCTYPE\s+svg\s+PUBLIC\s+"[^"]+"\s+"[^"]+"\s*>', '', raw, count=1).lstrip()
    root = ET.fromstring(raw)
    if root.tag != '{%s}svg' % SVG_NS:
        raise ValueError('Expected SVG circuit data')
    for parent in list(root.iter()):
        for child in list(parent):
            local = child.tag.rpartition('}')[2]
            if local in ('metadata', 'script', 'foreignObject'):
                parent.remove(child)
                continue
            if child.attrib.get('id') == 'headings' and not hvdc:
                parent.remove(child)
                continue
            if hvdc and local == 'rect' and child.get('y') in ('0', '1323') and child.get('fill') in ('#21334A', '#FFFFFF'):
                parent.remove(child)
                continue
            if local == 'text':
                try:
                    y = float(child.get('y', '-1'))
                except ValueError:
                    y = -1
                if (hvdc and (0 <= y < 310 or y > 1310)) or (not hvdc and y >= 735):
                    parent.remove(child)
                    continue
            for attr in list(child.attrib):
                if attr.lower().startswith('on'):
                    del child.attrib[attr]
    if hvdc:
        root.set('viewBox', '40 158 3420 1160')
    for el in root.iter():
        if el.tail is not None and not el.tail.strip():
            el.tail = None
    root.set('preserveAspectRatio', 'xMidYMid meet')
    root.attrib.pop('width', None)
    root.attrib.pop('height', None)
    return ET.tostring(root, encoding='unicode', short_empty_elements=True)

def build(source: Path, out: Path, src: Path) -> dict:
    """Embed all diagrams and source figures without runtime HTTP requests."""
    source = source.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(source))
    from rectifier_model import CommutationSequence
    from hvdc_link_model import LinkSettings, CombinedState
    from hvdc_link_renderer import HVDCLinkRenderer

    settings = LinkSettings(**json.loads((source / 'config_hvdc.json').read_text(encoding='utf-8')))
    renderer = HVDCLinkRenderer(settings)
    rect = CommutationSequence(settings.mu_rectifier)
    inv = CommutationSequence(settings.mu_inverter)
    figures = {'rectifier': {}, 'inverter': {}, 'hvdc': {}}
    refs = {'rectifier': {}, 'inverter': {}, 'hvdc': {}}

    for side, count in [('rectifier', 12), ('inverter', 12), ('hvdc', 24)]:
        base = source / ('output_hvdc' if side == 'hvdc' else 'output_lcc/' + side)
        for i in range(1, count + 1):
            filename = f'hvdc_joint_state_{i:02d}.svg' if side == 'hvdc' else f'estado_{i:02d}.svg'
            circuit = base / filename
            waveform = base / 'waveforms' / filename
            if not circuit.exists() or not waveform.exists():
                raise FileNotFoundError(f'Missing circuit/waveform: {circuit} or {waveform}')
            refs[side][str(i)] = svg_xml(waveform.read_text(encoding='utf-8'))
            if side != 'hvdc':
                figures[side][str(i)] = svg_xml(circuit.read_text(encoding='utf-8'))

    for r in rect.states:
        for i in inv.states:
            state = CombinedState(1, 0, 1, r, i)
            svg = ET.tostring(renderer.render(state).getroot(), encoding='unicode')
            figures['hvdc'][f'{r.number}:{i.number}'] = svg_xml(svg, hvdc=True)

    data = {
        'format': 'LCC interactive deck v1',
        'source': 'angelohafner/three-phase-scr-rectifier-visualizer',
        'angle_reference': 'relative commutation; illustrative 30-degree station offset',
        'limitations': 'Linear current transfer and approximate overlap voltage, not EMT',
        'diagrams': figures, 'references': refs,
    }
    template = (src / 'template.html').read_text(encoding='utf-8')
    bindings = {
        '<!--INLINE_CSS-->': (src / 'styles.css').read_text(encoding='utf-8'),
        '<!--INLINE_WAVEFORMS-->': (src / 'waveforms.js').read_text(encoding='utf-8'),
        '<!--INLINE_CHARTS-->': (src / 'charts.js').read_text(encoding='utf-8'),
        '<!--INLINE_PRESENTATION-->': (src / 'presentation.js').read_text(encoding='utf-8'),
        '<!--INLINE_DATA-->': json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            .replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    }
    for key, value in bindings.items():
        if template.count(key) != 1:
            raise ValueError('Expected one template token: ' + key)
        template = template.replace(key, value)
    out.write_text(template, encoding='utf-8')
    return {'html': str(out), 'bytes': out.stat().st_size,
            'waveform_sets': 48, 'joint_topology_combinations': 144, 'slides': 54}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent.parent / 'dist' / 'lcc_hvdc_interactive.html')
    args = parser.parse_args()
    print(json.dumps(build(args.project, args.output, Path(__file__).resolve().parent / 'src'), indent=2))

if __name__ == '__main__':
    main()
