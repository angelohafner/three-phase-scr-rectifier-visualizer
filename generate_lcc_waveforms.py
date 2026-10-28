#!/usr/bin/env python3
"""Generate synchronized didactic waveforms and editable vector teaching sheets."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from hvdc_link_model import CombinedSchedule
from lcc_waveform_model import (LCCWaveformModel, WaveformConfig,
                                WaveformValidator, station_state_windows,
                                settings_for_hvdc, verify_joint_sync)
from lcc_waveform_render import FigureSynchronizer, ViewSpec, WaveformRenderer
from rectifier_model import CommutationSequence


DEFAULTS={
    'sides': ['rectifier','inverter','hvdc'],
    'ac_peak': 1.0, 'dc_current': 1.0, 'samples': 1441, 'png_dpi': 105,
    'alpha_rectifier':15.0,'alpha_inverter':145.0,
    'mu_rectifier':15.0,'mu_inverter':15.0,'gamma_min':10.0,
    'hvdc_settings_file':'config_hvdc.json',
    'signals':['phase','line','scr','dc','idc'],
    'combined': True,'png':True,
}


def state_summary(st) -> str:
    """Present the exact SCRs and overlap transition in the circuit manifest."""
    devices=' + '.join(sorted(st.scrs, key=lambda s:int(s[1:])))
    if st.is_overlap:
        return f'{devices} | {st.outgoing} outgoing → {st.incoming} incoming'
    return f'{devices} | one upper and one lower SCR carry the DC current'


def read_config(path: Path|None)->dict:
    """Read valid user settings without changing the original model configs."""
    if path is None:
        return dict(DEFAULTS)
    info=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(info,dict):
        raise ValueError('Configuration must contain a JSON object')
    return dict(DEFAULTS,**info)


def generate(config:dict, *, stages:tuple[str,...],
             state_number:int|None=None, project:Path|None=None) -> dict:
    """Render every selected state in the original diagram's logical folder."""
    root=(project or Path(__file__).resolve().parent).resolve()
    signals=config.get('signals',DEFAULTS['signals'])
    allowed={'phase','line','scr','dc','idc'}
    if not isinstance(signals,list) or not signals or set(signals)-allowed:
        raise ValueError('signals must be a nonempty list from phase,line,scr,dc,idc')
    wc=WaveformConfig(ac_peak=float(config['ac_peak']),
                      dc_current=float(config['dc_current']),
                      samples=int(config['samples']),png_dpi=int(config['png_dpi']),
                      show_phase='phase' in signals,show_line='line' in signals,
                      show_scr='scr' in signals,show_dc='dc' in signals,
                      show_idc='idc' in signals,combined=bool(config['combined']),
                      png=bool(config['png']))
    model=LCCWaveformModel(wc)
    renderer=WaveformRenderer(wc)
    synchronizer=FigureSynchronizer()
    produced={'configuration':{k:v for k,v in config.items() if not k.startswith('_')},
              'stations':{},'count':0,
              'notes':['Full-cycle fixed scales for every state within one station.',
                       'Red shaded interval exactly matches the original topology schedule.',
                       'Current transfer is linear and illustrated; no EMT calculation.',
                       'DC voltage uses equal-reactance two-line-voltage average in overlap.',
                       'Inverter v_dc is positive DC pole-to-return drop; in signed rectifier-oriented convention it is negative.',
                       'The inter-station commutation offset is an illustrative angle, not a solved grid phase shift.']}

    def export(name:str,circuit:Path,folder:Path,view:ViewSpec,r,i):
        if not circuit.exists():
            raise FileNotFoundError('Cannot synchronize absent circuit: '+str(circuit))
        dest=folder/'waveforms'/f'{name}.svg'
        sheet=folder/'sheets'/f'{name}.svg'
        reuse=(bool(config.get('_skip_existing')) and dest.exists() and
               (not wc.png or dest.with_suffix('.png').exists()) and
               (not wc.combined or (sheet.exists() and
                (not wc.png or sheet.with_suffix('.png').exists()))))
        if not reuse:
            renderer.plot(view,r,i,dest,dest.with_suffix('.png') if wc.png else None)
            if wc.combined:
                synchronizer.compose(circuit,dest,sheet,view.title,
                                     sheet.with_suffix('.png') if wc.png else None)
        return {'state':name,'svg':str(dest.relative_to(root)),
                'circuit':str(circuit.relative_to(root)),
                'combined':str((folder/'sheets'/f'{name}.svg').relative_to(root)) if wc.combined else None,
                'windows_deg':view.windows,'rectifier_state':view.rectifier_state,
                'inverter_state':view.inverter_state,
                'note':view.explanation}

    for side in ('rectifier','inverter'):
        if side not in stages:
            continue
        mu=float(config['mu_rectifier'] if side=='rectifier' else config['mu_inverter'])
        alpha=float(config['alpha_rectifier'] if side=='rectifier' else config['alpha_inverter'])
        folder=root/'output_lcc'/side
        seq=CommutationSequence(mu)
        station=model.station(side,alpha=alpha,mu=mu,gamma_min=float(config['gamma_min']))
        WaveformValidator.validate_station(station,wc.dc_current)
        rows=[]
        for st in seq.states:
            if state_number is not None and st.number!=state_number:
                continue
            windows=station_state_windows(st.number,mu)
            for lo,hi in windows:
                WaveformValidator.verify_interval(station,st.number,lo,hi)
            fn=f'estado_{st.number:02d}'
            params=({'alpha_r':alpha,'mu_r':mu} if side=='rectifier' else
                    {'alpha_i':alpha,'mu_i':mu,'gamma_i':station.gamma})
            view=ViewSpec(title=f'{side.upper()} · STATE {st.number:02d} · '+
                         ('COMMUTATION OVERLAP' if st.is_overlap else 'NORMAL CONDUCTION'),
                         explanation=state_summary(st),windows=windows,
                         **({'rectifier_state':st.number} if side=='rectifier'
                            else {'inverter_state':st.number}),**params)
            rows.append(export(fn,folder/f'{fn}.svg',folder,view,
                               station if side=='rectifier' else None,
                               station if side=='inverter' else None))
        manifest=folder/'waveforms'/'manifest_waveforms.json'
        manifest.write_text(json.dumps({'station':side,'model':'conceptual only',
                                        'parameters':{'alpha_deg':alpha,'mu_deg':mu,
                                                      'gamma_deg':station.gamma,
                                                      'ac_peak':wc.ac_peak,'idc':wc.dc_current},
                                        'states':rows},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        produced['stations'][side]=rows
        produced['count']+=len(rows)

    if 'hvdc' in stages:
        hvdc_path=Path(str(config.get('hvdc_settings_file','config_hvdc.json')))
        if not hvdc_path.is_absolute():
            hvdc_path=root/hvdc_path
        settings=settings_for_hvdc(json.loads(hvdc_path.read_text(encoding='utf-8')))
        schedule=CombinedSchedule(settings)
        rect=model.station('rectifier',alpha=settings.alpha_rectifier,mu=settings.mu_rectifier)
        inv=model.station('inverter',alpha=settings.alpha_inverter,mu=settings.mu_inverter,
                          offset=settings.ac_phase_offset,gamma_min=settings.gamma_min)
        WaveformValidator.validate_station(rect,wc.dc_current)
        WaveformValidator.validate_station(inv,wc.dc_current)
        verify_joint_sync(schedule,rect,inv)
        folder=root/'output_hvdc'; rows=[]
        for st in schedule.intervals:
            if state_number is not None and state_number!=st.number:
                continue
            windows=((st.theta_start,st.theta_end),)
            title=f'HVDC LINK · JOINT STATE {st.number:02d} · {st.name.upper()}'
            desc=('Rectifier: '+state_summary(st.rectifier)+
                  '   |   Inverter: '+state_summary(st.inverter))
            view=ViewSpec(title=title,explanation=desc,windows=windows,
                          rectifier_state=st.rectifier.number,
                          inverter_state=st.inverter.number,
                          combined_state=st.number,
                          alpha_r=settings.alpha_rectifier,mu_r=settings.mu_rectifier,
                          alpha_i=settings.alpha_inverter,mu_i=settings.mu_inverter,
                          gamma_i=settings.gamma)
            fn=f'hvdc_joint_state_{st.number:02d}'
            rows.append(export(fn,folder/f'{fn}.svg',folder,view,rect,inv))
        manifest=folder/'waveforms'/'manifest_waveforms.json'
        manifest.write_text(json.dumps({'station':'full_hvdc','model':'conceptual only',
                                        'settings':asdict(settings),
                                        'relative_offset_note':'Station timeline shift only, not a calculated AC phase angle',
                                        'states':rows},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        produced['stations']['hvdc']=rows
        produced['count']+=len(rows)
    if state_number is None and set(stages)=={'rectifier','inverter','hvdc'}:
        # Manifest for easy machine-readable synchronization of every original figure.
        (root/'waveform_index.json').write_text(json.dumps(produced,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return produced


def main(argv:list[str]|None=None)->None:
    parser=argparse.ArgumentParser(description='Conceptual LCC current, voltage and overlap waveforms')
    parser.add_argument('--config',type=Path,default=Path('config_waveforms.json'))
    parser.add_argument('--side',choices=('all','rectifier','inverter','hvdc'),default='all')
    parser.add_argument('--state',type=int,default=None)
    parser.add_argument('--ac-peak',type=float,default=None)
    parser.add_argument('--idc',type=float,default=None)
    parser.add_argument('--samples',type=int,default=None)
    parser.add_argument('--signals',default=None,help='Comma-separated: phase,line,scr,dc,idc')
    parser.add_argument('--no-png',action='store_true')
    parser.add_argument('--no-sheets',action='store_true')
    parser.add_argument('--skip-existing',action='store_true',help='Reuse SVG/PNG files that already exist for unchanged parameters')
    parser.add_argument('--project',type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args(argv)
    try:
        root=args.project.resolve()
        config_file=(root/args.config if not args.config.is_absolute() else args.config)
        config=read_config(config_file)
        if args.ac_peak is not None: config['ac_peak']=args.ac_peak
        if args.idc is not None: config['dc_current']=args.idc
        if args.samples is not None: config['samples']=args.samples
        if args.signals is not None: config['signals']=[x.strip() for x in args.signals.split(',')]
        if args.no_png: config['png']=False
        if args.no_sheets: config['combined']=False
        if args.skip_existing: config['_skip_existing']=True
        stages=('rectifier','inverter','hvdc') if args.side=='all' else (args.side,)
        data=generate(config,stages=stages,state_number=args.state,project=root)
        print('Generated',data['count'],'synchronized state waveform sets')
        for name,rows in data['stations'].items():
            print(f'  {name}: {len(rows)} waveforms, circuit + waveform sheets')
    except (OSError,ValueError,AssertionError,RuntimeError,ImportError) as exc:
        parser.error(str(exc))


if __name__=='__main__':
    main()
