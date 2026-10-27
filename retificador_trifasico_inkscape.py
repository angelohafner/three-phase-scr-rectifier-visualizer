#!/usr/bin/env python3
"""Generate editable six-pulse SCR conduction and commutation-overlap SVGs.

The program reuses the previous Inkscape generator's vector primitives,
models the circuit as a graph, and highlights actual current-loop unions.

Examples:
    python retificador_trifasico_inkscape.py --all-12 --mu 15 --output-dir output
    python retificador_trifasico_inkscape.py --state 2 --mu 20 --output state_02.svg
    python retificador_trifasico_inkscape.py --all --output-dir output_ideal
    python retificador_trifasico_inkscape.py --config config_sequencia.json
    python retificador_trifasico_inkscape.py --config configuracao_retificador.json
    python retificador_trifasico_inkscape.py --manual --thyristors T1,T6 --sources VA,VC
    python retificador_trifasico_inkscape.py --list-parts

Uses Python standard library. Optional `schemdraw` supplies the native SCR
vector segments; otherwise the identical published SCR symbol coordinates
embedded in the original generator remain available.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import difflib
import json
from pathlib import Path
from typing import Iterable

import rectifier_art as art
from rectifier_model import (CircuitTopology, CommutationSequence,
                             ConductionState, Highlight, PHASES, PAIRS,
                             UPPER, LOWER, WIRE_IDS)
from rectifier_renderer import CircuitRenderer, build_panel


SCR_IDS = frozenset((*UPPER.values(), *LOWER.values()))
INDUCTOR_IDS = frozenset(('LA', 'LB', 'LC', 'LDC'))
SOURCE_IDS = frozenset(('VA', 'VB', 'VC'))


def parse_ids(value: object, allowed: frozenset[str], field: str) -> frozenset[str]:
    """Read user-specified IDs with suggestions for misspelled components."""
    if isinstance(value, str):
        entries = value.split(',')
    elif isinstance(value, list):
        entries = value
    else:
        raise ValueError(f'{field}: expected an array or a comma-separated string')
    output: set[str] = set()
    for item in entries:
        if not isinstance(item, str):
            raise ValueError(f'{field}: each ID must be a string')
        item = item.strip().upper().replace('-', '_')
        if not item:
            continue
        if item not in allowed:
            options = ', '.join(difflib.get_close_matches(item, sorted(allowed),n=3))
            raise ValueError(f'{field}: unknown component {item!r}. '
                             + (f'Did you mean: {options}? ' if options else '')
                             + 'See --list-parts.')
        output.add(item)
    return frozenset(output)


def selection_from_config(data: dict[str, object]) -> Highlight:
    """Accept current and legacy Portuguese/English manual-selection JSON."""
    def get(pt: str, en: str, default: object) -> object:
        return data.get(pt, data.get(en, default))
    title = get('titulo', 'title', 'THREE-PHASE SCR RECTIFIER')
    if not isinstance(title, str):
        raise ValueError('titulo/title must be a string')
    thyristors = parse_ids(get('tiristores','thyristors',[]),SCR_IDS,'thyristors')
    inductors = parse_ids(get('indutores','inductors',[]),INDUCTOR_IDS,'inductors')
    default_sources = [f'V{x[-1]}' for x in inductors if x in ('LA','LB','LC')]
    sources = parse_ids(get('fontes','sources',default_sources),SOURCE_IDS,'sources')
    paths = parse_ids(get('caminhos','paths',[]),WIRE_IDS,'paths')
    resistor = get('resistor','resistor',False)
    arrows = get('setas','arrows',True)
    if not isinstance(resistor,bool) or not isinstance(arrows,bool):
        raise ValueError('resistor and arrows must be booleans')
    return Highlight(thyristors,inductors,sources,paths,resistor,arrows,title)


def selection_for_ideal(topology: CircuitTopology, index: int) -> Highlight:
    """Retain the original six-pair '--step' and '--all' behavior."""
    if index not in range(1,7):
        raise ValueError('Legacy ideal step must be 1..6')
    high, low = PAIRS[index-1]
    pseudo = ConductionState(number=2*index-1,kind='normal',
                             pairs=((high, low),),
                             scrs=frozenset((UPPER[high],LOWER[low])),
                             theta_start=0,theta_end=60,mu=0)
    return topology.highlight(pseudo)


def create_manifest(seq: CommutationSequence, topology: CircuitTopology,
                    output_dir: Path) -> None:
    """Export inspectable exact states, paths, component sets and angles."""
    rows = []
    for st in seq.states:
        h = topology.highlight(st)
        rows.append({
            'state': st.number,
            'kind': st.kind,
            'start_angle_deg': st.theta_start,
            'end_angle_deg': st.theta_end,
            'overlap_mu_deg': seq.mu,
            'thyristors': sorted(h.thyristors),
            'outgoing': st.outgoing,
            'incoming': st.incoming,
            'pairs': [f'{a.upper()}+/{b.upper()}-' for a,b in st.pairs],
            'sources': sorted(h.sources),
            'inductors': sorted(h.inductors),
            'wires': sorted(h.paths),
            'signed_edge_traversals': dict(h.directions),
            'file': f'estado_{st.number:02d}.svg',
        })
    (output_dir/'manifest_estados.json').write_text(
        json.dumps({'mu_deg':seq.mu,
                    'angular_convention':'Normal i is [60*(i-1)+mu, 60*i]; overlap i is [60*i,60*i+mu]. Final interval wraps modulo 360.',
                    'warning':'Topological current paths only; no computed transient currents.',
                    'states':rows},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    with (output_dir/'manifest_estados.csv').open('w',newline='',encoding='utf-8-sig') as fh:
        writer=csv.DictWriter(fh,fieldnames=('state','kind','start_angle_deg',
            'end_angle_deg','overlap_mu_deg','thyristors','outgoing','incoming','pairs',
            'sources','inductors','wires','file'),extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({k:', '.join(v) if isinstance(v,list) else v
                             for k,v in row.items()})


def render_all_twelve(seq: CommutationSequence, renderer: CircuitRenderer,
                      output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True,exist_ok=True)
    paths=[]
    for state in seq.states:
        file = output_dir / f'estado_{state.number:02d}.svg'
        renderer.save(renderer.render(renderer.topology.highlight(state),state),file)
        print(f'Created: {file}')
        paths.append(file)
    p = build_panel(seq.states,renderer,output_dir/'painel_12_estados.svg')
    print(f'Created: {p}')
    create_manifest(seq,renderer.topology,output_dir)
    return paths



def apply_overrides(selected: Highlight, args: argparse.Namespace) -> tuple[Highlight, bool]:
    """Apply manual overrides without silently discarding user selections.

    The returned boolean is True when the original validated current-loop
    highlight was altered. In this case, the chart is labeled 'custom'.
    """
    changed_electrical = False
    overrides = (
        ('thyristors', 'thyristors', SCR_IDS),
        ('inductors', 'inductors', INDUCTOR_IDS),
        ('sources', 'sources', SOURCE_IDS),
        ('paths', 'paths', WIRE_IDS),
    )
    for argname, field, allowed in overrides:
        raw = getattr(args, argname)
        if raw is not None:
            selected = replace(selected, **{field:parse_ids(raw,allowed,field)})
            changed_electrical = True
    if args.resistor is not None:
        selected = replace(selected,resistor=args.resistor=='on')
        changed_electrical = True
    if args.arrows is not None:
        selected = replace(selected,arrows=args.arrows=='on')
    if args.title is not None:
        selected = replace(selected,title=args.title)
    if changed_electrical:
        selected = replace(selected,directions=(),step=None)
    return selected, changed_electrical

def list_parts() -> str:
    return '\n'.join([
        'SCRs:      ' + ', '.join(sorted(SCR_IDS)),
        'Inductors: ' + ', '.join(sorted(INDUCTOR_IDS)),
        'Sources:   ' + ', '.join(sorted(SOURCE_IDS)),
        'AC wires:  ' + ', '.join(sorted(w for w in WIRE_IDS
                                          if w.startswith(('FASE_','NEUTRO_')))),
        'SCR leads: ' + ', '.join(sorted(w for w in WIRE_IDS
                                          if w.startswith('T'))),
        'DC wires:  ' + ', '.join(sorted(w for w in WIRE_IDS
                                          if w.startswith(('POS_','NEG_','CARGA_')))),
        'Automatic graph-based highlighting is available with --state, --all-12, --step and --all.'
    ])


def main(argv: Iterable[str] | None = None) -> None:
    p = argparse.ArgumentParser(description='Generate editable SVGs of all '
         'six-pulse SCR conduction and three-SCR commutation-overlap states.')
    modes = p.add_mutually_exclusive_group()
    modes.add_argument('--all-12',action='store_true',help='Generate 12 states, a panel and a manifest')
    modes.add_argument('--all',action='store_true',help='Legacy: generate six ideal conduction pairs')
    modes.add_argument('--state',type=int,choices=range(1,13),help='Generate one of 12 states')
    modes.add_argument('--step',type=int,choices=range(1,7),help='Legacy ideal conduction pair 1..6')
    modes.add_argument('--manual',action='store_true',help='Start a manual component selection')
    modes.add_argument('--config',type=Path,help='Read JSON for manual selection or automatic sequence')
    p.add_argument('--mu',type=float,default=None,help='Overlap angle in electrical degrees (default 15)')
    p.add_argument('--output-dir',type=Path,default=None,help='Folder for --all-12 / --all SVGs')
    p.add_argument('--output',type=Path,default=None,help='Destination SVG for a single selected state')
    p.add_argument('--thyristors','--tiristores',dest='thyristors')
    p.add_argument('--inductors','--indutores',dest='inductors')
    p.add_argument('--sources','--fontes',dest='sources')
    p.add_argument('--paths','--caminhos',dest='paths')
    p.add_argument('--resistor',choices=['on','off'])
    p.add_argument('--arrows','--setas',choices=['on','off'])
    p.add_argument('--title','--titulo',dest='title')
    p.add_argument('--require-schemdraw',action='store_true',
                   help='Fail unless the Schemdraw native SCR class can be imported')
    p.add_argument('--list-parts',action='store_true')
    args = p.parse_args(argv)
    if args.list_parts:
        print(list_parts()); return
    if args.require_schemdraw and art.elm is None:
        p.error('Schemdraw unavailable. Install: python -m pip install schemdraw')
    try:
        config: dict[str,object] = {}
        if args.config:
            config = json.loads(args.config.read_text(encoding='utf-8'))
            if not isinstance(config,dict):
                raise ValueError('Root JSON must be an object')
        selection_flags = (args.thyristors,args.inductors,args.sources,args.paths,
                           args.resistor,args.arrows,args.title)
        using_overrides = any(v is not None for v in selection_flags)
        mode = 'all-12' if args.all_12 else 'all' if args.all else (
            'state' if args.state is not None else 'step' if args.step is not None
            else 'manual' if args.manual else 'config' if args.config else 'step')
        if mode=='config':
            mode = str(config.get('mode','manual')).lower().replace('_','-')
        if mode not in ('all-12','all','state','step','manual'):
            raise ValueError(f'Unsupported mode: {mode}')
        if mode in ('all','all-12') and using_overrides:
            raise ValueError('Full automatic sequences cannot use manual override flags')
        mu = args.mu if args.mu is not None else float(config.get('mu_deg',config.get('mu',15)))
        topology=CircuitTopology()
        renderer=CircuitRenderer(topology)
        output_dir = args.output_dir or Path(str(config.get('output_dir','output')))
        if mode=='all-12':
            render_all_twelve(CommutationSequence(mu),renderer,output_dir)
        elif mode=='all':
            output_dir.mkdir(parents=True,exist_ok=True)
            for idx in range(1,7):
                file=output_dir/f'ideal_passo_{idx:02d}.svg'
                renderer.save(renderer.render(selection_for_ideal(topology,idx),
                                              ideal_step=idx),file)
                print(f'Created: {file}')
        elif mode=='state':
            state_no = args.state if args.state is not None else int(config.get('state',1))
            state=CommutationSequence(mu).state(state_no)
            selected=topology.highlight(state)
            selected, customized = apply_overrides(selected,args)
            file=args.output or Path(str(config.get('output','estado_'+f'{state_no:02d}.svg')))
            renderer.save(renderer.render(selected, None if customized else state),file)
            print(f'Created: {file}')
        elif mode=='step':
            idx=args.step if args.step is not None else int(config.get('step',1))
            selected=selection_for_ideal(topology,idx)
            selected, customized = apply_overrides(selected,args)
            file=args.output or Path(str(config.get('output','retificador_trifasico.svg')))
            renderer.save(renderer.render(selected,ideal_step=None if customized else idx),file)
            print(f'Created: {file}')
        else:
            selected=selection_from_config(config) if args.config else Highlight(
                frozenset(),frozenset(),frozenset(),frozenset(),arrows=False)
            selected, _ = apply_overrides(selected,args)
            file=args.output or Path(str(config.get('output','retificador_personalizado.svg')))
            renderer.save(renderer.render(selected),file)
            print(f'Created: {file}')
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as err:
        p.error(str(err))


if __name__ == '__main__':
    main()
