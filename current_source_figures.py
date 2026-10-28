#!/usr/bin/env python3
"""Generate reusable current-source bridge SVGs and didactic waveform assets."""
from __future__ import annotations

import argparse
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import rectifier_art as art
import schemdraw_symbols as symbols
from current_source_model import (CurrentSourceSettings, PAIRS, UPPER, LOWER,
                                  full_cycle, sample)

SVG_NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG_NS)
ET.register_namespace('inkscape', 'http://www.inkscape.org/namespaces/inkscape')


def circuit(source: Path, *, inverter: bool = False) -> ET.ElementTree:
    """Keep graph-validated AC bridge and replace only its DC load branch."""
    root = ET.parse(source).getroot()
    active = root.find(f'.//{art.S}g[@id="components-active"]') is not None
    def replace(parent: ET.Element) -> None:
        for child in list(parent):
            key = child.get('id', '')
            if key in {
                'base-ldc', 'selected-ldc', 'base-r', 'selected-r',
                'base-carga_pos_l', 'base-carga_l_r', 'base-carga_r_neg',
                'selected-carga_pos_l', 'selected-carga_l_r', 'selected-carga_r_neg',
                # Inverter source may already have a DC voltage element.
                'base-edc', 'selected-edc', 'base-vdc', 'selected-vdc',
            }:
                parent.remove(child)
            else:
                replace(child)
    replace(root)
    # A current source constrains current ONLY while a valid SCR loop exists.
    # In the schematic, its arrow points down for the rectifier's load/sink,
    # and up for the inverter's equivalent supplying DC source.
    for id_, red in [('components-base', False), ('components-active', True)]:
        parent = root.find(f'.//{art.S}g[@id="{id_}"]')
        if parent is None or (red and not active):
            continue
        color = '#E12E3F' if red else '#203246'
        line_width = 4.5 if red else 3.4
        art.line(parent, 1240, 235, 1240, 419, color, line_width)
        art.line(parent, 1240, 527, 1240, 662, color, line_width)
        start = (1240, 527) if inverter else (1240, 419)
        end = (1240, 419) if inverter else (1240, 527)
        symbols.draw_current_source(parent, start, end, color, line_width,
                                    transverse_scale=108,
                                    group_id='current-source-' + ('active' if red else 'base'))
    anno = root.find(f'.//{art.S}g[@id="annotations"]')
    if anno is not None:
        for el in list(anno):
            if el.tag != art.S+'text':
                continue
            try:
                x, y = float(el.get('x','0')), float(el.get('y','0'))
            except ValueError:
                continue
            if x >= 1220 and 275 <= y <= 640:
                anno.remove(el)
        art.math_label(anno, 1310, 486, 'I', subscript='dc', upright_subscript=True,
                       size=26, color='#193b4e')
    head = root.find(f'.//{art.S}g[@id="headings"]')
    if head is not None:
        for e in head:
            if e.tag == art.S+'text' and 'THREE-PHASE' in (e.text or ''):
                e.text = 'SIX-PULSE LCC · IDEAL DC CURRENT SOURCE'
                break
    legend = root.find(f'.//{art.S}g[@id="legend"]')
    if legend is not None:
        for e in legend:
            if e.tag != art.S+'text':
                continue
            if e.get('y')=='784':
                e.text = 'DC current imposed · commutation currents shared by valve group'
    ET.SubElement(root, art.S+'desc').text = (
        'Current source idealization: voltage-compliance and valid conducting SCR path required. '
        'Three-phase AC voltage sources and commutation inductors are retained.')
    return ET.ElementTree(root)


def waveform(path: Path, state: int, settings: CurrentSourceSettings) -> None:
    """Produce reference SVG and PNG with fixed scales and overlap shading."""
    wave=full_cycle(settings,1441)
    theta=wave['angle']
    fig,axes=plt.subplots(3,1,figsize=(13.2,7.8),sharex=True)
    fig.patch.set_facecolor('white')
    lines=[('-',1.0),('--',.85),(':',.85),('-.',.8),((0,(6,3,1,3)),.76),((0,(3,4)),.7)]
    colors=['#d03f5c','#137e9b','#9b7a32','#77539a','#408a72','#66788c']
    for k,name in enumerate(('T1','T2','T3','T4','T5','T6')):
        style,opacity=lines[k]
        axes[0].plot(theta,wave['scr'][name],ls=style,c=colors[k],alpha=opacity,
                     lw=1.8,label=name)
    axes[0].set_ylabel(r'$i_{T}$ (p.u.)')
    for k,name in enumerate(('a','b','c')):
        axes[1].plot(theta,wave['phase'][k],ls=['-','--',':'][k],
                     color=colors[k],lw=1.75,alpha=.86,label=fr'$v_{name}$')
    axes[1].set_ylabel(r'$v_{\rm phase}$ (p.u.)')
    axes[2].plot(theta,wave['dc'],color='#24789a',lw=1.75,label=r'$v_{\rm dc}$')
    axes[2].plot(theta,wave['idc'],color='#d03f5c',ls='--',lw=2,
                 alpha=.83,label=r'$i_{\rm dc}$')
    axes[2].set_ylabel('DC (p.u.)')
    axes[2].set_xlabel(r'Electrical angle $\theta$ (degrees)')
    # 12-state convention from the current-source model.
    index=state//2 if state%2==0 else (state-1)//2
    start=index*60+(0 if state%2==0 else settings.mu_deg)
    stop=index*60+(settings.mu_deg if state%2==0 else 60)
    if state==12:
        start,stop=0,settings.mu_deg
    for ax in axes:
        ax.axvspan(start,stop,color='#1295a1',alpha=.13,zorder=0)
        ax.set_xlim(0,360)
        ax.set_xticks(range(0,361,60))
        ax.grid(alpha=.13)
        ax.legend(loc='upper right',ncol=6 if ax is axes[0] else 3,
                  fontsize=8,frameon=False)
        ax.tick_params(axis='both',labelsize=9)
    fig.suptitle('CONSTANT DC CURRENT · CONDUCTION '+str(state).zfill(2),
                 color='#163b50',fontsize=15,fontweight='semibold')
    fig.tight_layout(rect=[0,0,1,.955])
    fig.savefig(path.with_suffix('.svg'))
    fig.savefig(path.with_suffix('.png'),dpi=130)
    plt.close(fig)


def generate(project:Path, out:Path, preview:bool=True):
    """Create both station figures without rebuilding established bridge logic."""
    settings=CurrentSourceSettings()
    result=[]
    for side in ('rectifier','inverter'):
        target=out/side/'circuits'
        waves=out/side/'waveforms'
        target.mkdir(parents=True,exist_ok=True)
        waves.mkdir(parents=True,exist_ok=True)
        for j in range(1,13):
            base=project/'output_lcc'/side/f'estado_{j:02d}.svg'
            if not base.exists():raise FileNotFoundError(base)
            svg=circuit(base,inverter=(side=='inverter'))
            dest=target/f'estado_{j:02d}.svg'
            svg.write(dest,encoding='unicode',xml_declaration=True)
            if preview:
                import cairosvg
                cairosvg.svg2png(url=str(dest),write_to=str(dest.with_suffix('.png')),
                                  output_width=1400)
            # Waveform examples for both stations use the shared constant-current
            # rectifier current-reference sign convention; the inverter's voltage
            # and AC power direction is explained separately in the HTML.
            if side=='rectifier':
                waveform(waves/f'estado_{j:02d}',j,settings)
            result.append(dest)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent/'output_lcc'/'current_source')
    parser.add_argument('--no-png',action='store_true')
    args=parser.parse_args()
    result=generate(args.project,args.out,not args.no_png)
    print(f'Created {len(result)} editable current-source converter SVGs')


if __name__=='__main__':main()
