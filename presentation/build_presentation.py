#!/usr/bin/env python3
"""Build a self-contained, offline 16:9 LCC HTML slide deck.

Uses the existing SCR and HVDC topology models rather than inventing wire paths.
All external assets are inlined; the final HTML works over file://.
"""
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
    """Normalize a trusted repository SVG and omit stale static annotations."""
    raw = re.sub(r'<\?xml[^>]*\?>', '', source, count=1).lstrip()
    raw = re.sub(r'<!DOCTYPE\s+svg\s+PUBLIC\s+"[^"]+"\s+"[^"]+"\s*>', '', raw, count=1).lstrip()
    root = ET.fromstring(raw)
    if root.tag != '{%s}svg' % SVG_NS:
        raise ValueError('Asset must be SVG')
    for parent in list(root.iter()):
        for child in list(parent):
            local = child.tag.rpartition('}')[2]
            # Strip metadata, active scripts and linked external content.
            if local in ('metadata', 'script', 'foreignObject'):
                parent.remove(child)
                continue
            if child.attrib.get('id') == 'headings' and not hvdc:
                parent.remove(child)
                continue
            if hvdc and local == 'rect' and child.get('y') in ('0', '1323') and child.get('fill') in ('#21334A', '#FFFFFF'):
                parent.remove(child)
                continue
            if hvdc and local == 'text':
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
        # Crop nominal annotation banners and leave the electrical circuit.
        root.set('viewBox', '40 158 3420 1160')
    for el in root.iter():
        el.tail = None if el.tail is not None and not el.tail.strip() else el.tail
    root.set('preserveAspectRatio', 'xMidYMid meet')
    root.attrib.pop('width', None)
    root.attrib.pop('height', None)
    return ET.tostring(root, encoding='unicode', short_empty_elements=True)


def build(source: Path, out: Path, src: Path) -> dict:
    """Inline 48 reference waveforms and 168 topology-valid circuit figures."""
    source = source.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(source))
    try:
        from rectifier_model import CommutationSequence
        from hvdc_link_model import LinkSettings, CombinedState
        from hvdc_link_renderer import HVDCLinkRenderer
    except ImportError as exc:
        raise RuntimeError('Run the builder against the full LCC repository') from exc
    settings_file = source / 'config_hvdc.json'
    settings = LinkSettings(**json.loads(settings_file.read_text(encoding='utf-8')))
    renderer = HVDCLinkRenderer(settings)
    rect = CommutationSequence(settings.mu_rectifier)
    inv = CommutationSequence(settings.mu_inverter)
    figures: dict = {'rectifier': {}, 'inverter': {}, 'hvdc': {}}
    refs: dict = {'rectifier': {}, 'inverter': {}, 'hvdc': {}}

    for side, count in [('rectifier', 12), ('inverter', 12), ('hvdc', 24)]:
        root = source / ('output_hvdc' if side == 'hvdc' else 'output_lcc/' + side)
        for i in range(1, count + 1):
            filename = f'hvdc_joint_state_{i:02d}.svg' if side == 'hvdc' else f'estado_{i:02d}.svg'
            filename_path = root / filename
            reference_path = root / 'waveforms' / filename
            if not filename_path.exists():
                raise FileNotFoundError(filename_path)
            if not reference_path.exists():
                raise FileNotFoundError(reference_path)
            refs[side][str(i)] = svg_xml(reference_path.read_text(encoding='utf-8'))
            if side != 'hvdc':
                figures[side][str(i)] = svg_xml(filename_path.read_text(encoding='utf-8'))

    # Every possible pair of 12 per-station states is precomputed from the
    # graph-validated topology. This avoids stale pre-rendered joint highlights
    # when a user changes overlap and a previously absent pair becomes active.
    for r in rect.states:
        for i in inv.states:
            state = CombinedState(1, 0, 1, r, i)
            svg = ET.tostring(renderer.render(state).getroot(), encoding='unicode')
            figures['hvdc'][f'{r.number}:{i.number}'] = svg_xml(svg, hvdc=True)

    from rectifier_loads import LoadParameters, ResistiveCircuitRenderer
    from lcc_advanced_loads import AdvancedLoadParameters, render_voltage_source_circuit
    load_renderer = ResistiveCircuitRenderer()
    load_figures = {}
    for mode in ('R','RL','LE','RLE'):
        for idx in range(-1,6):
            tree = (load_renderer.render(LoadParameters(), 105.0, idx if idx>=0 else None, mode)
                    if mode in ('R','RL') else
                    render_voltage_source_circuit(AdvancedLoadParameters(), 105.0, idx if idx>=0 else None, mode))
            for parent in tree.getroot().iter():
                for child in list(parent):
                    if child.get('id') == 'legend':
                        parent.remove(child)
            clean = svg_xml(ET.tostring(tree.getroot(), encoding='unicode'))
            image = ET.fromstring(clean)
            image.set('viewBox', '55 174 1420 550')
            load_figures[f'{mode}:{idx}'] = ET.tostring(image, encoding='unicode')
    # Source-constrained bridge figures share existing graph-validated SCR paths.
    # They replace only the DC branch; each phase source remains a voltage source.
    from current_source_figures import generate as generate_current_source
    source_dir = source/'output_lcc'/'current_source'
    if not (source_dir/'rectifier'/'circuits'/'estado_01.svg').exists():
        generate_current_source(source,source_dir,preview=False)
    current_source_figures={'rectifier':{},'inverter':{}}
    for side in ('rectifier','inverter'):
        for j in range(1,13):
            path=source_dir/side/'circuits'/f'estado_{j:02d}.svg'
            fig=ET.fromstring(svg_xml(path.read_text(encoding='utf-8')))
            # The original 12-state legend shows fixed reference mu=15 degrees.
            # Omit it so the live slider can never contradict stale SVG annotations.
            for parent in fig.iter():
                for child in list(parent):
                    if child.attrib.get('id') in ('legend','headings'):
                        parent.remove(child)
            fig.set('viewBox','120 181 1290 510')
            current_source_figures[side][str(j)]=ET.tostring(fig,encoding='unicode')
    from halfwave_figures import circuit_svg
    halfwave_figures={}
    for load in ('R','RL'):
        for conducting in (False,True):
            key=load+':'+('on' if conducting else 'off')
            xml=ET.tostring(circuit_svg(load,conducting).getroot(),encoding='unicode')
            halfwave_figures[key]=svg_xml(xml)
    # Chapter 04 uses actual Schemdraw elements; no symbol fallback is allowed.
    from chapter04_schemdraw import generate_assets as generate_chapter04
    chapter04_schematics = generate_chapter04(
        source / 'presentation' / 'assets' / 'chapter04')
    data = {
        'chapter04_schematics': chapter04_schematics,
        'halfwave_figures': halfwave_figures,
        'current_source_figures':current_source_figures,
        'load_figures': load_figures,
        'format': 'LCC interactive engineering teaching deck v2 · R RL LE RLE · SCR vAK',
        'source': 'angelohafner/three-phase-scr-rectifier-visualizer',
        'angle_reference': 'relative commutation angle; station offset=30 degrees, illustrative',
        'limitations': 'Conceptual linear current transfer; equal-reactance overlap midpoint voltage; not EMT',
        'diagrams': figures,
        'references': refs,
    }
    template = (src / 'template.html').read_text(encoding='utf-8')
    assets = {
        '<!--INLINE_CSS-->': (src / 'styles.css').read_text(encoding='utf-8'),
        '<!--INLINE_CCC_CSS-->': (src / 'ccc_chapter.css').read_text(encoding='utf-8'),
        '<!--INLINE_WAVEFORMS-->': (src / 'waveforms.js').read_text(encoding='utf-8'),
        '<!--INLINE_MATH_UI-->': (src / 'math_ui.js').read_text(encoding='utf-8'),
        '<!--INLINE_FIXED_AXES-->': (src / 'fixed_axes.js').read_text(encoding='utf-8'),
        '<!--INLINE_CHARTS-->': (src / 'charts.js').read_text(encoding='utf-8'),
        '<!--INLINE_LOAD_MODELS-->': (src / 'load_models.js').read_text(encoding='utf-8'),
        '<!--INLINE_LOAD_CHARTS-->': (src / 'load_charts.js').read_text(encoding='utf-8'),
        '<!--INLINE_HALFWAVE-->': (src / 'halfwave.js').read_text(encoding='utf-8'),
        '<!--INLINE_CURRENT_SOURCE_MODEL-->': (src / 'current_source.js').read_text(encoding='utf-8'),
        '<!--INLINE_CURRENT_SOURCE_POLICY-->': (src / 'current_source_policy.js').read_text(encoding='utf-8'),
        '<!--INLINE_CURRENT_SOURCE_CHARTS-->': (src / 'current_source_charts.js').read_text(encoding='utf-8'),
        '<!--INLINE_CCC_MODEL-->': (src / 'ccc_model.js').read_text(encoding='utf-8'),
        '<!--INLINE_CCC_POWER_MATCH-->': (src / 'ccc_power_match.js').read_text(encoding='utf-8'),
        '<!--INLINE_CCC_CHAPTER-->': (src / 'ccc_chapter.js').read_text(encoding='utf-8'),
        '<!--INLINE_PRESENTATION-->': (src / 'presentation.js').read_text(encoding='utf-8'),
        '<!--INLINE_DATA-->': json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            .replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026'),
    }
    for tag, content in assets.items():
        if template.count(tag) != 1:
            raise ValueError(f'Missing or duplicate template token: {tag}')
        template = template.replace(tag, content)
    if re.search(r'<(?:script|link)[^>]+(?:src|href)\s*=\s*["\']https?://', template):
        raise ValueError('Found external dependency')
    out.write_text(template, encoding='utf-8')
    import hashlib
    import os
    import subprocess
    def _git_blob_sha(path: Path) -> str:
        content = path.read_bytes()
        return hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
    revision=os.environ.get('GITHUB_SHA') or os.environ.get('LCC_SOURCE_COMMIT')
    if not revision:
        try:
            revision=subprocess.run(['git','rev-parse','HEAD'], cwd=source,
                capture_output=True,text=True,check=True,timeout=3).stdout.strip()
        except (OSError,subprocess.SubprocessError):
            revision='local-uncommitted'
    source_files=['waveforms.js','fixed_axes.js','charts.js','load_charts.js',
        'current_source.js','current_source_charts.js','ccc_model.js',
        'ccc_power_match.js','ccc_chapter.js','presentation.js','styles.css','halfwave.js']
    trace={
        'source_revision':revision,
        'built_with':[{'path':'presentation/src/'+name,
                       'git_blob_sha':_git_blob_sha(src/name)} for name in source_files],
        'html_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
        'slides':86,
        'convention':'I_dc: rectifier to inverter; Vdc,r positive, Vdc,i negative in normal power flow',
    }
    (out.parent/(out.stem+'.build.json')).write_text(json.dumps(trace,indent=2)+'\n',encoding='utf-8')
    return {
        'html': str(out),
        'bytes': out.stat().st_size,
        'individual_circuits': len(figures['rectifier']) + len(figures['inverter']),
        'hvdc_topology_pairs': len(figures['hvdc']),
        'reference_waveforms': sum(map(len, refs.values())),
        'slides': 86,
        'offline': True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent.parent / 'dist' / 'lcc_hvdc_interactive.html')
    args = parser.parse_args()
    info = build(args.project, args.output, Path(__file__).resolve().parent/'src')
    print(json.dumps(info, indent=2))


if __name__ == '__main__':
    main()
