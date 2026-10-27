#!/usr/bin/env python3
"""Two-stage LCC teaching figure generator: rectifier, then inverter.

Each station is a standalone six-pulse teaching circuit. Electrical conduction
paths are computed by a shared directed graph; SVG symbols and layers are
reused from the original rectifier package. Figures do not solve dynamics.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from xml.etree import ElementTree as ET

import rectifier_art as art
from rectifier_model import CircuitTopology, CommutationSequence, Highlight
from rectifier_renderer import CircuitRenderer, build_panel, _prefix_identifiers
from retificador_trifasico_inkscape import (create_manifest, render_all_twelve,
                                            selection_from_config, parse_ids,
                                            SCR_IDS, INDUCTOR_IDS, SOURCE_IDS, WIRE_IDS)


@dataclass(frozen=True)
class InverterOperatingPoint:
    """Didactic LCC firing/overlap/extinction angles, all in degrees."""
    alpha: float = 145.0
    mu: float = 15.0
    gamma_min: float = 10.0

    def __post_init__(self) -> None:
        if not (90 < self.alpha < 180):
            raise ValueError('Inverter alpha must satisfy 90 < alpha < 180 degrees')
        if not (0 < self.mu < 60):
            raise ValueError('Overlap mu must satisfy 0 < mu < 60 degrees')
        if not (0 < self.gamma_min < 90):
            raise ValueError('gamma_min must satisfy 0 < gamma_min < 90 degrees')
        if self.gamma + 1e-8 < self.gamma_min:
            raise ValueError(
                f'Extinction margin violated: gamma={self.gamma:g}° '
                f'< gamma_min={self.gamma_min:g}°'
            )

    @property
    def gamma(self) -> float:
        """Steady-state textbook angle relation, not a dynamic simulation."""
        return 180 - self.alpha - self.mu


def renderer_for(operation: str, inverter_point: InverterOperatingPoint) -> CircuitRenderer:
    """Select the directed topology and keep all drawing primitives shared."""
    topo = CircuitTopology(operation)
    return CircuitRenderer(topo, alpha_deg=inverter_point.alpha if operation == 'inverter' else None)


def stage_manifest(seq: CommutationSequence, renderer: CircuitRenderer, folder: Path,
                   point: InverterOperatingPoint) -> None:
    """Extend the original per-state manifest with operating-mode metadata."""
    import json
    create_manifest(seq, renderer.topology, folder)
    file = folder/'manifest_estados.json'
    data = json.loads(file.read_text(encoding='utf-8'))
    data['operation'] = renderer.topology.operation
    data['power_flow'] = 'DC to AC' if renderer.inverter else 'AC to DC'
    data['dc_element'] = 'EDC' if renderer.inverter else 'R'
    data['current_convention'] = (
        'Inverter: DC source feeds the + bus; upper SCRs conduct from DC+ to AC, '
        'lower SCRs return from AC to DC-. Current flows - to + inside the DC source.'
        if renderer.inverter else
        'Rectifier: upper SCRs conduct AC to DC+, lower SCRs DC- to AC.'
    )
    data['angular_convention'] = (
        'The 12 time windows use a relative 60-degree valve-commutation cycle. '
        'They are not absolute AC phase-reference angles and do not shift with alpha.'
    )
    if renderer.inverter:
        for row in data['states']:
            row['pairs'] = [f'DC+->{h.upper()}; {l.upper()}->DC-'
                            for h, l in seq.state(row['state']).pairs]
        data['alpha_deg'] = point.alpha
        data['gamma_deg'] = point.gamma
        data['gamma_min_deg'] = point.gamma_min
        data['angle_identity'] = 'alpha + mu + gamma = 180 deg (steady ideal relation)'
    file.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


def generate_stage(operation: str, folder: Path, point: InverterOperatingPoint,
                   *, state_number: int | None = None) -> tuple[CircuitRenderer, CommutationSequence]:
    """Generate a stage using the same state sequence and SVG panel helpers."""
    seq = CommutationSequence(point.mu)
    renderer = renderer_for(operation, point)
    folder.mkdir(parents=True, exist_ok=True)
    if state_number is not None:
        state = seq.state(state_number)
        dest = folder/f'estado_{state_number:02d}.svg'
        renderer.save(renderer.render(renderer.topology.highlight(state),state),dest)
        print(f'Created {dest}')
    else:
        render_all_twelve(seq, renderer, folder)
        stage_manifest(seq, renderer, folder, point)
    return renderer, seq


def generate_overview(rectifier: CircuitRenderer, inverter: CircuitRenderer,
                      seq: CommutationSequence, file: Path) -> Path:
    """Build a teaching comparison without implying wired source interconnection."""
    state = seq.state(2)
    root = ET.Element(art.S+'svg', {'width':'1660', 'height':'740',
                                   'viewBox':'0 0 1660 740', 'version':'1.1'})
    art.element(root,'title').text='LCC: rectifier stage followed by inverter stage'
    art.element(root,'desc').text=(
        'Two standalone explanatory bridges: they are not a single physical DC-link '
        'model. Red paths show conventional current in each mode.'
    )
    art.element(root, 'rect', x=0,y=0,width=1660,height=740,fill='#F3F6FA')
    art.txt(root, 60, 55,'LCC HVDC  ·  TWO-STAGE LEARNING SEQUENCE',size=32,bold=True)
    art.txt(root, 60, 91,'First the rectifier (AC → DC), then the inverter (DC → AC)',
            size=19,color='#6C7D90')
    scale=0.514
    for side, renderer, left in [('RECTIFIER',rectifier,32),('INVERTER',inverter,842)]:
        art.txt(root,left+14,139, '01  '+side if side=='RECTIFIER' else '02  '+side,
                size=22,bold=True)
        svg=renderer.render(renderer.topology.highlight(state),state).getroot()
        # Strip standalone metadata; preserve each circuit as editable SVG groups.
        _prefix_identifiers(svg,side.lower()+'-')
        group=art.element(root,'g',transform=f'translate({left},{175}) scale({scale})')
        for node in list(svg):
            if node.tag in (art.S+'title',art.S+'desc'): continue
            group.append(node)
    art.txt(root,60,681,
            'Standalone station examples. The real DC line, transformers and controls are omitted.',
            size=17,color='#6C7D90')
    art.math_formula(root,60,711,
                     [('During overlap: three valves conduct; at the inverter: ','roman'),
                      ('α','variable'),(' + ','roman'),('μ','variable'),
                      (' + ','roman'),('γ','variable'),(' = 180','roman'),
                      ('°','unit'),('.','roman')],
                     size=17,color='#6C7D90')
    art.indent_svg(root,space='  ')
    file.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(root).write(file, encoding='utf-8', xml_declaration=True)
    return file


def manual_highlight(operation: str, config: dict[str, object],
                     arguments: argparse.Namespace) -> Highlight:
    """Reuse the original selection grammar with an inverter DC source flag."""
    initial = selection_from_config(config)
    initial = replace(initial,
                      dc_source=bool(config.get('dc_source', operation == 'inverter')),
                      title=('THREE-PHASE SCR INVERTER (LCC)' if operation == 'inverter'
                             else initial.title))
    for key, field, allowed in (
        ('thyristors','thyristors',SCR_IDS),
        ('inductors','inductors',INDUCTOR_IDS),
        ('sources','sources',SOURCE_IDS),
        ('paths','paths',WIRE_IDS),
    ):
        text = getattr(arguments, key)
        if text is not None:
            initial = replace(initial, **{field: parse_ids(text,allowed,key)})
    if arguments.dc_source is not None:
        initial = replace(initial, dc_source=arguments.dc_source == 'on')
    if arguments.arrows is not None:
        initial = replace(initial, arrows=arguments.arrows == 'on')
    return initial


def main(argv: list[str] | None = None) -> None:
    parser=argparse.ArgumentParser(description='Editable SVGs teaching rectifier and inverter LCC conduction.')
    parser.add_argument('--config',type=Path,default=None,help='Read optional JSON parameter file')
    parser.add_argument('--side',choices=('rectifier','inverter','both'),default=None)
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--all-12',action='store_true',help='Generate the full 12-state gallery (default)')
    modes.add_argument('--state',type=int,choices=range(1,13),help='Generate a single state')
    modes.add_argument('--manual',action='store_true',help='Manually color selected components')
    angles=parser.add_mutually_exclusive_group()
    angles.add_argument('--alpha',type=float,default=None,help='Inverter delay angle (degrees)')
    angles.add_argument('--gamma',type=float,default=None,
                        help='Use gamma to derive the inverter firing alpha')
    parser.add_argument('--mu',type=float,default=None,help='Overlap angle (degrees)')
    parser.add_argument('--gamma-min',type=float,default=None,help='Minimum extinction margin (degrees)')
    parser.add_argument('--output-dir',type=Path,default=None)
    parser.add_argument('--output',type=Path,default=None,help='File for a single or manual selection')
    parser.add_argument('--thyristors','--tiristores',default=None)
    parser.add_argument('--inductors','--indutores',default=None)
    parser.add_argument('--sources','--fontes',default=None)
    parser.add_argument('--paths','--caminhos',default=None)
    parser.add_argument('--dc-source',choices=('on','off'),default=None)
    parser.add_argument('--arrows',choices=('on','off'),default=None)
    args=parser.parse_args(argv)
    try:
        import json
        config=json.loads(args.config.read_text(encoding='utf-8')) if args.config else {}
        if not isinstance(config,dict):
            raise ValueError('Configuration JSON must contain a dictionary')
        side=args.side or str(config.get('side','both'))
        if side not in ('rectifier','inverter','both'):
            raise ValueError('side must be rectifier, inverter or both')
        mu=args.mu if args.mu is not None else float(config.get('mu_deg',15))
        gamma_min=args.gamma_min if args.gamma_min is not None else float(config.get('gamma_min_deg',10))
        stored_gamma=config.get('gamma_deg')
        stored_alpha=config.get('alpha_deg')
        if args.gamma is not None:
            alpha=180-mu-args.gamma
        elif args.alpha is not None:
            alpha=args.alpha
        elif stored_gamma is not None and stored_alpha is None:
            alpha=180-mu-float(stored_gamma)
        else:
            alpha=float(stored_alpha if stored_alpha is not None else 145)
        point=InverterOperatingPoint(alpha,mu,gamma_min)
        output_dir=args.output_dir or Path(str(config.get('output_dir','output_lcc')))
        mode='manual' if args.manual else ('state' if args.state is not None else
             'all-12' if args.all_12 else str(config.get('mode','all-12')))
        if mode not in ('all-12','state','manual'):
            raise ValueError('mode must be all-12, state, or manual')
        sides=('rectifier','inverter') if side=='both' else (side,)
        produced={}
        for operation in sides:
            folder=output_dir/operation if side=='both' else output_dir
            if mode=='manual':
                r=renderer_for(operation,point)
                h=manual_highlight(operation,config,args)
                dest=args.output or folder/f'{operation}_manual.svg'
                r.save(r.render(h),dest)
                print(f'Created {dest}')
                produced[operation]=(r,CommutationSequence(point.mu))
            else:
                produced[operation]=generate_stage(
                    operation,folder,point,
                    state_number=(args.state if args.state is not None else
                                  int(config.get('state',2)) if mode=='state' else None))
        if side=='both':
            overview=output_dir/'lcc_two_stage_overview.svg'
            generate_overview(produced['rectifier'][0],produced['inverter'][0],
                              produced['rectifier'][1],overview)
            print(f'Created {overview}')
    except (ValueError, OSError, TypeError) as exc:
        parser.error(str(exc))


if __name__=='__main__':
    main()
