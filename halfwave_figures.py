#!/usr/bin/env python3
"""Generate editable half-wave SCR schematics and conceptual waveforms.

Native Schemdraw SCR primitives are reused through rectifier_art, retaining
Inkscape-editable SVG text and paths. The figures never imply EMT accuracy.
"""
from __future__ import annotations
from pathlib import Path
import math
import xml.etree.ElementTree as ET

import rectifier_art as art
import schemdraw_symbols as native
from halfwave_model import HalfWaveSettings, HalfWaveModel

S = art.S
TEAL = '#088E99'
RED = '#C33D53'
BLUE = '#176F9E'
INK = '#173B51'
MUTED = '#6B8291'


def circuit_svg(load: str = 'RL', conducting: bool = True) -> ET.ElementTree:
    """Create a one-source, one-SCR, one-R/RL series current loop."""
    if load not in ('R', 'RL'):
        raise ValueError(load)
    root = ET.Element(S + 'svg', {
        'viewBox': '0 0 1040 550',
        'role': 'img', 'aria-label': f'Half-wave SCR with {load} load'
    })
    art.element(root, 'rect', x=12, y=12, width=1016, height=526, rx=12,
                fill='#FFFFFF', stroke='#DAE6EB', stroke_width=1.5)
    art.txt(root, 51, 60, 'SINGLE-PHASE HALF-WAVE RECTIFIER', size=21, bold=True, color=INK)
    art.txt(root, 51, 90, 'Ideal SCR · common return · no freewheeling diode', size=14, color=MUTED)
    color = RED if conducting else INK
    width = 5 if conducting else 3.4
    wire = art.group(root, 'current-path' if conducting else 'blocked-path')
    for x1,y1,x2,y2 in [
        (194,235,194,145),(194,145,465,145),(515.75,145,845,145),
        (845,145,845,217 if load == 'RL' else 273),
        (845,366,845,420),(845,420,194,420),(194,420,194,325),
    ]:
        art.line(wire,x1,y1,x2,y2,color,width)
    if load=='RL':
        art.line(wire,845,287,845,310,color,width)
    # The source geometry comes from schemdraw.elements.SourceSin.
    native.draw_ac_source(root,(194,235),(194,325),color,width,
                          group_id='source-ac')
    art.math_label(root,116,271,'v',subscript='s',size=22,color=INK)
    # Native SCR with the original electrical terminal positions.
    scr=native.draw_scr(root,(465,145),(515.75,145),color,width,
                        fill='#FBE7E9' if conducting else 'white',
                        group_id='scr-T1')
    scr.set('data-state','on' if conducting else 'off')
    art.math_label(root,607,113,'T',subscript='1',size=24,
                   color=RED if conducting else INK)
    art.txt(root,470,206,'GATE',size=11,color=MUTED)
    if load=='RL':
        native.draw_inductor(root,(845,217),(845,287),color,width,
                             transverse_scale=120,group_id='load-inductor')
        ry1=310
        art.math_label(root,900,257,'L',size=26,color=INK)
    else:
        ry1=273
    native.draw_resistor(root,(845,ry1),(845,366),color,width,
                         transverse_scale=65,group_id='load-resistor')
    art.math_label(root,900,344,'R',size=26,color=INK)
    art.math_label(root,685,122,'i',subscript='T',size=20,color=RED if conducting else MUTED)
    art.math_label(root,918,173,'v',subscript='o',size=20,color=INK)
    art.txt(root,920,195,'+',size=18,color=INK)
    art.txt(root,920,429,'−',size=18,color=INK)
    if conducting:
        for (d,code) in [((680,145),'right'),((530,420),'left')]:
            ax,ay=d
            if code=='right': p=f'M {ax-13},{ay-8} L {ax+5},{ay} L {ax-13},{ay+8}'
            else:p=f'M {ax+13},{ay-8} L {ax-5},{ay} L {ax+13},{ay+8}'
            art.path(wire,p,RED,3.2)
    else:
        art.txt(root,516,218,'SCR BLOCKING',size=14,bold=True,color=MUTED)
    art.txt(root,51,501,'RED = CONDUCTION PATH' if conducting else 'NO CURRENT · SCR BLOCKING',
            size=14,bold=True,color=RED if conducting else MUTED)
    art.txt(root,49,524,'Schemdraw SCR / SourceSin / '+('Inductor / ' if load=='RL' else '')+'ResistorIEEE · one closed loop',size=12,color=MUTED)
    return ET.ElementTree(root)


def save_svg(tree: ET.ElementTree, path: Path) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tree.write(path,encoding='unicode',xml_declaration=True)


def waveform_figure(config: HalfWaveSettings, output: Path, view: str = 'overview') -> None:
    """Plot the exact analytical waveform, with alpha/180/beta annotations."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.family':'DejaVu Sans','mathtext.fontset':'stix',
                         'axes.labelsize':10,'axes.titlesize':11,'font.size':9,
                         'svg.fonttype':'none'})
    model=HalfWaveModel(config)
    samples=model.series(0.25)
    x=np.array([q.theta_deg for q in samples])
    v_s=np.array([q.vs_V for q in samples])
    v_o=np.array([q.vo_V for q in samples])
    v_r=np.array([q.vr_V for q in samples])
    v_l=np.array([q.vl_V for q in samples])
    v_ak=np.array([q.vak_V for q in samples])
    it=np.array([q.i_A for q in samples])
    en=np.array([q.energy_J for q in samples])
    fig, axs=plt.subplots(3 if view=='overview' else 2,1,figsize=(11,7),sharex=True,
                          gridspec_kw={'hspace':.36})
    if view=='overview':
        plots=[[(v_s,r'$v_s$',BLUE,'-'),(v_o,r'$v_o$',RED,'--')],[(it,r'$i_T$',RED,'-')],
               [(v_l,r'$v_L$',TEAL,':'),(v_ak,r'$v_{AK}$',BLUE,'-.')]]
        labels=['AC / load voltage (V)','SCR current (A)','Component voltage (V)']
    elif view=='energy':
        plots=[[(it,r'$i_T$',RED,'-')],[(en,r'$W_L$',TEAL,'-')]]
        labels=['SCR current (A)','Magnetic energy (J)']
    else:
        plots=[[(v_s,r'$v_s$',BLUE,'-'),(v_r,r'$v_R$',RED,'--'),(v_l,r'$v_L$',TEAL,':')],
               [(it,r'$i_T$',RED,'-')]]
        labels=['Source / component voltages (V)','SCR current (A)']
    for ax,tracks,lab in zip(axs,plots,labels):
        ax.axvspan(config.alpha_deg,model.beta_deg,color=TEAL,alpha=.09)
        ax.axvline(180,color='#C18B41',linewidth=1.25,linestyle=':',label=r'$180^\circ$')
        ax.axvline(config.alpha_deg,color='#667789',linewidth=1,linestyle='--')
        ax.axvline(model.beta_deg,color=RED,linewidth=1.25,linestyle='--')
        if model.beta_deg>180:
            ax.axvspan(180,model.beta_deg,color='#C18B41',alpha=.19)
        for y,name,color,style in tracks:
            ax.plot(x,y,label=name,color=color,linestyle=style,alpha=.83,linewidth=1.9)
        ax.set_ylabel(lab)
        ax.grid(color='#E1E9ED',linewidth=.6)
        ax.legend(loc='upper right',ncol=min(4,len(tracks)+1),frameon=False)
        ax.set_xlim(0,360)
        ax.set_xticks(range(0,361,60))
    axs[-1].set_xlabel(r'Electrical angle $\theta$ (°)')
    fig.suptitle(f'Half-wave SCR with {config.load} load | '
                 rf'$\alpha$ = {config.alpha_deg:.1f}° | $\beta$ = {model.beta_deg:.1f}°',
                 fontsize=13,color=INK)
    output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(output.with_suffix('.svg'),bbox_inches='tight')
    fig.savefig(output.with_suffix('.png'),dpi=135,bbox_inches='tight')
    plt.close(fig)


def generate(root: Path) -> None:
    """Write the circuit and reference waveform galleries."""
    import cairosvg
    circuits=root/'circuits'
    for load in ('R','RL'):
        for conducting in (False,True):
            ident=f'half_wave_{load}_{"on" if conducting else "off"}'
            path=circuits/(ident+'.svg')
            save_svg(circuit_svg(load,conducting),path)
            cairosvg.svg2png(url=str(path),write_to=str(path.with_suffix('.png')),output_width=1250)
    cases=[('R',30,'R_alpha_030','overview'),('R',75,'R_alpha_075','overview'),
           ('RL',50,'RL_alpha_050','overview'),('RL',95,'RL_alpha_095','overview'),
           ('RL',50,'RL_extinction','energy'),('RL',75,'RL_component_voltages','voltages')]
    for load,alpha,name,view in cases:
        waveform_figure(HalfWaveSettings(load=load,alpha_deg=alpha),root/'waveforms'/name,view)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--output-dir',type=Path,default=Path('output_lcc/fundamentals'))
    args=p.parse_args()
    generate(args.output_dir)
    print(f'Created half-wave fundamentals figures in {args.output_dir}')
