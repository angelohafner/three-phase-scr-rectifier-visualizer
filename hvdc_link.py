#!/usr/bin/env python3
"""Generate editable Inkscape diagrams of the complete two-terminal HVDC link.

The two station conduction patterns reuse the existing 12-state sequence.
A configurable AC phase offset gives one shared, phase-referenced timeline.
All output figures are vector-based and individual states are validated by
closed paths using the graph in hvdc_link_model.py.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import rectifier_art as art
from hvdc_link_model import CombinedSchedule, CombinedState, HVDCLinkTopology, LinkSettings
from hvdc_link_renderer import HVDCLinkRenderer, PALETTE


def optional_png(svg_path: Path, png_path: Path, width: int = 1900) -> None:
    """Convert a vector drawing to an optional preview using CairoSVG."""
    try:
        import cairosvg
    except ImportError as exc:
        raise RuntimeError('Install cairosvg for --png previews; SVG needs no dependencies') from exc
    cairosvg.svg2png(url=str(svg_path),write_to=str(png_path),output_width=width)


def write_timeline(schedule: CombinedSchedule, path: Path) -> None:
    """Build a precise, editable 360-degree diagram of joint valve commutations."""
    root=ET.Element(art.S+'svg',{
        'width':'3180','height':'890','viewBox':'0 0 3180 890','version':'1.1',
    })
    art.element(root,'title').text='LCC HVDC: synchronized rectifier and inverter commutation states'
    art.element(root,'rect',x=0,y=0,width=3180,height=890,fill=PALETTE['canvas'])
    art.txt(root,85,82,'GLOBAL 360° CONDUCTION TIMELINE',size=38,bold=True,
            color=PALETTE['ink'])
    art.txt(root,87,128,
            'Commutation windows referenced to the rectifier event; station offset is illustrative',
            size=19,color=PALETTE['quiet'])
    left,right=350,3040
    scale=(right-left)/360
    lanes=[('RECTIFIER',230),('INVERTER',365),('COMBINED',530)]
    for label,y in lanes:
        art.txt(root,80,y+43,label,size=22,color=PALETTE['ink'],bold=True)
        art.element(root,'rect',x=left,y=y,width=right-left,height=90,
                    rx=9,fill='#E5EAF0',stroke=PALETTE['line'],stroke_width=2)
    for t in range(0,361,30):
        xx=left+t*scale
        art.line(root,xx,205,xx,640,'#FFFFFF',2)
        art.txt(root,xx,188,f'{t}°',size=16,color=PALETTE['quiet'],anchor='middle')
    for state in schedule.intervals:
        x0=left+state.theta_start*scale
        dx=(state.theta_end-state.theta_start)*scale
        rcolor=PALETTE['active'] if state.rectifier_overlap else '#518E9E'
        icolor=PALETTE['active'] if state.inverter_overlap else '#517BB0'
        bcolor=('#99417C' if state.rectifier_overlap and state.inverter_overlap else
                '#E69A45' if state.rectifier_overlap else
                '#84B56A' if state.inverter_overlap else '#DBE4EA')
        for y,color in ((230,rcolor),(365,icolor),(530,bcolor)):
            art.element(root,'rect',x=x0+.8,y=y+1.4,width=max(dx-1.6,0),height=87.2,
                        fill=color,stroke='#FFFFFF',stroke_width=1.1)
        if dx>52:
            art.txt(root,x0+dx/2,280,f'R{state.rectifier.number:02d}',size=16,
                    color='white',anchor='middle',bold=True)
            art.txt(root,x0+dx/2,415,f'I{state.inverter.number:02d}',size=16,
                    color='white',anchor='middle',bold=True)
            art.txt(root,x0+dx/2,580,f'{state.number:02d}',size=16,
                    color=PALETTE['ink'],anchor='middle',bold=True)
    art.angle_notation(root,92,712,
                       [('μ','r',schedule.settings.mu_rectifier),
                        ('μ','i',schedule.settings.mu_inverter)],
                       size=20,color=PALETTE['ink'],separator='   |   ',
                       trailer=f'   |   Relative commutation offset = {schedule.settings.ac_phase_offset:g}°')
    art.txt(root,92,757,f'{len(schedule.intervals)} distinct joint conduction intervals',
            size=20,color=PALETTE['active'],bold=True)
    art.txt(root,92,799,
            'Overlap intervals show which devices conduct; red does not quantify current sharing.',
            size=18,color=PALETTE['quiet'])
    art.txt(root,92,835,
            'The station offset is illustrative, not a power-system phase lock or transformer phase shift.',
            size=17,color=PALETTE['quiet'])
    art.indent_svg(root,space='  ')
    path.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)


def sample_state(schedule: CombinedSchedule, *, r_overlap: bool | None,
                 i_overlap: bool | None) -> CombinedState | None:
    """Choose a real interval from the joint schedule matching the request."""
    choices=[s for s in schedule.intervals
             if (r_overlap is None or s.rectifier_overlap==r_overlap)
             and (i_overlap is None or s.inverter_overlap==i_overlap)]
    if not choices:
        return None
    return max(choices,key=lambda x:x.theta_end-x.theta_start)


def write_manifest(schedule: CombinedSchedule, topology: HVDCLinkTopology, folder: Path) -> None:
    """Export electrical identities, all conductive branches and angle windows."""
    output={
        'description':'Six-pulse-per-station, two-wire metallic-return, LCC HVDC schematic',
        'angles_deg':asdict(schedule.settings),
        'gamma_inverter_deg':schedule.settings.gamma,
        'timeline_reference':'rectifier local overlap start=0; inverter local=global-phase_offset',
        'phase_offset_note':'Illustrative station commutation offset; not a modeled AC voltage phase shift or transformer shift',
        'line_model':'L_DR + R_LINE + L_DI in positive pole; explicit metallic return',
        'transformer_note':'Idealized isolated Y/Y three-phase transformer at each station',
        'physical_limitations':(
            'Topology-only. Does not solve voltages, overlap currents, commutation failure, '
            '12-pulse bridges, phase locking, transformer magnetization, line capacitance, '
            'DC load-flow or current distribution.'
        ),
        'states':[],
    }
    rows=[]
    for state in schedule.intervals:
        sel=topology.highlight(state)
        entry={
            'state':state.number,'angle_start_deg':state.theta_start,
            'angle_end_deg':state.theta_end,'rectifier_state':state.rectifier.number,
            'rectifier_overlap':state.rectifier_overlap,
            'rectifier_scrs':sorted('R_'+v for v in state.rectifier.scrs),
            'inverter_state':state.inverter.number,
            'inverter_overlap':state.inverter_overlap,
            'inverter_scrs':sorted('I_'+v for v in state.inverter.scrs),
            'incoming_rectifier':state.rectifier.incoming,
            'outgoing_rectifier':state.rectifier.outgoing,
            'incoming_inverter':state.inverter.incoming,
            'outgoing_inverter':state.inverter.outgoing,
            'path_count':sel['loop_count'],
            'highlighted_elements':sorted(sel['active']),
            'edge_directions':sel['directions'],
        }
        output['states'].append(entry)
        rows.append({k:json.dumps(v) if isinstance(v,(list,dict)) else v
                     for k,v in entry.items() if k!='edge_directions'})
    (folder/'hvdc_states.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    with (folder/'hvdc_states.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def create_settings(config: dict[str,object], args: argparse.Namespace) -> LinkSettings:
    """Combine JSON and CLI settings without silently inventing phase shifts."""
    def val(name: str, option: str) -> float:
        override=getattr(args,option,None)
        return float(override if override is not None else config.get(name,{
            'alpha_rectifier':15,'alpha_inverter':145,'mu_rectifier':12,
            'mu_inverter':15,'gamma_min':10,'ac_phase_offset':30,
        }[name]))
    mur=val('mu_rectifier','mu_r')
    mui=val('mu_inverter','mu_i')
    if args.gamma_i is not None:
        alphai=180-mui-float(args.gamma_i)
    elif 'gamma_inverter' in config and args.alpha_i is None:
        alphai=180-mui-float(config['gamma_inverter'])
    else:
        alphai=val('alpha_inverter','alpha_i')
    return LinkSettings(
        alpha_rectifier=val('alpha_rectifier','alpha_r'),
        alpha_inverter=alphai,
        mu_rectifier=mur,mu_inverter=mui,
        gamma_min=val('gamma_min','gamma_min'),
        ac_phase_offset=val('ac_phase_offset','phase_offset'),
    )


def main(argv: list[str] | None = None) -> None:
    parser=argparse.ArgumentParser(
        description='Complete LCC HVDC six-pulse teaching circuit and 360-degree conduction gallery')
    parser.add_argument('--config',type=Path,default=None)
    parser.add_argument('--output-dir',type=Path,default=Path('output_hvdc'))
    parser.add_argument('--alpha-r',type=float,default=None)
    inv=parser.add_mutually_exclusive_group()
    inv.add_argument('--alpha-i',type=float,default=None)
    inv.add_argument('--gamma-i',type=float,default=None)
    parser.add_argument('--mu-r',type=float,default=None)
    parser.add_argument('--mu-i',type=float,default=None)
    parser.add_argument('--gamma-min',type=float,default=None)
    parser.add_argument('--phase-offset',type=float,default=None)
    parser.add_argument('--png',action='store_true',help='Export PNG previews (requires cairosvg)')
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--all',action='store_true',help='Generate all joint intervals and examples (default)')
    modes.add_argument('--state',type=int,default=None,help='Render one joint state by index')
    modes.add_argument('--theta',type=float,default=None,help='Render the state at an electrical angle')
    args=parser.parse_args(argv)
    try:
        config=json.loads(args.config.read_text(encoding='utf-8')) if args.config else {}
        if not isinstance(config,dict):
            raise ValueError('Configuration JSON must be a dictionary')
        settings=create_settings(config,args)
        schedule=CombinedSchedule(settings)
        graph=HVDCLinkTopology()
        renderer=HVDCLinkRenderer(settings,graph)
        output=args.output_dir
        output.mkdir(parents=True,exist_ok=True)

        if args.state is not None or args.theta is not None:
            if args.theta is not None and not __import__('math').isfinite(args.theta):
                raise ValueError('Angle theta must be finite')
            state=(schedule.at(args.theta) if args.theta is not None else
                   schedule.intervals[args.state-1]
                   if 1<=args.state<=len(schedule.intervals) else
                   None)
            if state is None:
                raise ValueError(f'State must be between 1 and {len(schedule.intervals)}')
            dest=output/f'hvdc_joint_state_{state.number:02d}.svg'
            renderer.save(renderer.render(state),dest)
            if args.png:
                optional_png(dest,dest.with_suffix('.png'))
            print(f'Created {dest} with R{state.rectifier.number:02d} and I{state.inverter.number:02d}')
            return

        for state in schedule.intervals:
            dest=output/f'hvdc_joint_state_{state.number:02d}.svg'
            renderer.save(renderer.render(state),dest)
            if args.png:
                optional_png(dest,dest.with_suffix('.png'))
        examples={
            'hvdc_normal':sample_state(schedule,r_overlap=False,i_overlap=False),
            'hvdc_rectifier_overlap':sample_state(schedule,r_overlap=True,i_overlap=False),
            'hvdc_inverter_overlap':sample_state(schedule,r_overlap=False,i_overlap=True),
            'hvdc_simultaneous_overlap':sample_state(schedule,r_overlap=True,i_overlap=True),
        }
        for name,state in examples.items():
            if state is None:
                continue
            dest=output/f'{name}.svg'
            renderer.save(renderer.render(state),dest)
            if args.png:
                optional_png(dest,dest.with_suffix('.png'))
        write_timeline(schedule,output/'hvdc_timeline.svg')
        if args.png:
            optional_png(output/'hvdc_timeline.svg',output/'hvdc_timeline.png',width=2500)
        write_manifest(schedule,graph,output)
        print(f'Generated {len(schedule.intervals)} joint SVG states in {output}')
        print(f'Commutation events: μr={settings.mu_rectifier:g}°, '
              f'μi={settings.mu_inverter:g}°, gamma_i={settings.gamma:g}°')
        print('Standalone examples: '+', '.join(name+'.svg' for name, state in examples.items()
                                             if state is not None)+', hvdc_timeline.svg')
    except (OSError, ValueError, RuntimeError,TypeError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
