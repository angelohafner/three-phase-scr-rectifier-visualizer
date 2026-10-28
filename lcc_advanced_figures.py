#!/usr/bin/env python3
"""Export editable SVG waveforms and load circuits for R, RL, LE and RLE."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from lcc_advanced_loads import AdvancedLoadParameters, VoltageSourceLoad, valve_voltages, render_voltage_source_circuit
from rectifier_loads import LoadParameters, ResistiveCircuitRenderer, ResistiveLoad, ResistiveInductiveLoad

COLORS=('#bd3952','#1e78a3','#008b91','#815b9b','#a87629','#50886a')
DASHES=((0,()),(0,(7,4)),(0,(2,3)),(0,(9,4,2,4)),(0,(11,5)),(0,(4,3,11,3)))
NAMES=('T1','T2','T3','T4','T5','T6')


def waveform(mode:str,params:AdvancedLoadParameters,theta:np.ndarray):
    """Reuse the R/RL model and share the advanced LE/RLE source model."""
    if mode in ('LE','RLE'):
        return VoltageSourceLoad(params,mode).sample(theta)
    ordinary=LoadParameters(alpha_deg=params.alpha_deg,resistance_ohm=params.resistance_ohm,
                            inductance_mH=params.inductance_mH,
                            phase_peak_pu=params.phase_peak_pu,
                            frequency_hz=params.frequency_hz)
    return (ResistiveLoad(ordinary) if mode=='R' else ResistiveInductiveLoad(ordinary)).sample(theta)


def state_windows(w,angle:float):
    """Return all connected angular intervals containing the current state."""
    pair=int(w.conducting_pair[np.argmin(abs(w.theta_deg-angle))]);mask=w.conducting_pair==pair
    index=int(np.argmin(abs(w.theta_deg-angle)));
    lo=hi=index
    while lo>0 and mask[lo-1]:lo-=1
    while hi<len(mask)-2 and mask[hi+1]:hi+=1
    windows=[(float(w.theta_deg[lo]),float(w.theta_deg[hi+1]))]
    if lo==0 and mask[-2]:
        k=len(mask)-2
        while k>0 and mask[k-1]:k-=1
        if k>0:windows.append((float(w.theta_deg[k]),360.))
    return pair,windows


def graph(mode:str,w,output:Path,angle:float=127.5)->None:
    """Draw three SVG panels with varied line patterns and valid SCR voltages."""
    plt.rcParams.update({'font.family':'DejaVu Sans','mathtext.fontset':'stix','font.size':9,
                         'axes.labelsize':10,'svg.fonttype':'none','axes.spines.top':False,
                         'axes.spines.right':False})
    v=valve_voltages(w.phase,w.conducting_pair)
    active,regions=state_windows(w,angle)
    fig,axs=plt.subplots(3,1,figsize=(11,7.2),sharex=True,layout='constrained')
    axs[0].plot(w.theta_deg,w.dc_v,color=COLORS[1],ls='--',alpha=.8,lw=1.9,label=r'$v_{\mathrm{dc}}$')
    axs[0].plot(w.theta_deg,w.dc_i,color=COLORS[0],ls='-',alpha=.9,lw=2,label=r'$i_{\mathrm{dc}}$')
    axs[0].set_ylabel('DC quantities (p.u.)')
    for k,component in enumerate(NAMES):
        ax=axs[1];ax.plot(w.theta_deg,w.scr[component],color=COLORS[k],ls=DASHES[k],
                          alpha=.69,lw=1.65,label=rf'$i_{{{component}}}$')
        axs[2].plot(w.theta_deg,v[component],color=COLORS[k],ls=DASHES[k],
                    alpha=.74,lw=1.4,label=rf'$v_{{\mathrm{{AK}},{component}}}$')
    axs[1].set_ylabel('SCR currents (p.u.)')
    axs[2].set_ylabel('SCR voltages (p.u.)')
    axs[2].set_xlabel(r'Electrical angle $\theta$ ($^\circ$)')
    for ax in axs:
        for lo,hi in regions:ax.axvspan(lo,hi,alpha=.13,color='#009ca8' if active>=0 else '#a6adb6')
        ax.axvline(angle,color='#b33e51',lw=1.2,alpha=.8,ls='--')
        ax.set_xlim(0,360);ax.set_xticks(np.arange(0,361,60));ax.grid(alpha=.14)
        ax.legend(ncol=6,loc='upper right',fontsize=8,framealpha=.78)
    title=f'{mode} LOAD · '
    fig.suptitle(title+r'$\alpha$ = '+f'{w.alpha_deg:.1f}'+r'$^\circ$'+' · Ideal AC commutation',fontsize=14,color='#17435c',fontweight='bold')
    fig.text(.5,.005,'SCR blocking voltages are undefined where both DC buses float (traces omitted).',
             ha='center',fontsize=9,color='#647d8e')
    output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(output,format='svg');fig.savefig(output.with_suffix('.png'),dpi=105)
    plt.close(fig)


def build(out:Path)->dict:
    """Export every model's circuit, waveform, and a comparison graphic."""
    params=AdvancedLoadParameters()
    samples=np.linspace(0,360,1441)
    base=ResistiveCircuitRenderer()
    waveforms={}
    results=[]
    for mode in ('R','RL','LE','RLE'):
        wave=waveform(mode,params,samples);waveforms[mode]=wave
        index=int(wave.conducting_pair[np.argmin(abs(samples-100))])
        circuit=(base.render(LoadParameters(),100,index if index>=0 else None,mode)
                 if mode in ('R','RL') else render_voltage_source_circuit(params,100,index if index>=0 else None,mode))
        destination=out/'circuits'/f'rectifier_{mode}.svg'
        destination.parent.mkdir(parents=True,exist_ok=True)
        # The upstream renderer's SVG remains editable in Inkscape.
        circuit.write(destination,encoding='utf-8',xml_declaration=True)
        graph(mode,wave,out/'waveforms'/f'rectifier_{mode}.svg')
        results.append(str(destination))
    fig,axs=plt.subplots(2,2,figsize=(12,7.4),sharex=True,layout='constrained')
    for ax,mode in zip(axs.flat,('R','RL','LE','RLE')):
        w=waveforms[mode]
        ax.plot(w.theta_deg,w.dc_v,label=r'$v_{\mathrm{dc}}$',ls='--',color=COLORS[1],alpha=.83,lw=1.7)
        ax.plot(w.theta_deg,w.dc_i,label=r'$i_{\mathrm{dc}}$',color=COLORS[0],alpha=.9,lw=1.7)
        _,regions=state_windows(w,127.5)
        for lo,hi in regions:ax.axvspan(lo,hi,color='#009ba4',alpha=.12)
        ax.set_title(mode+' load',fontsize=12,color='#18465c');ax.set_xlim(0,360)
        ax.grid(alpha=.14);ax.set_xticks(np.arange(0,361,60));ax.legend(fontsize=9)
        ax.set_ylabel('p.u.');ax.set_xlabel(r'$\theta$ ($^\circ$)')
    fig.suptitle('Rectifier load models · ideal AC commutation, same firing angle',fontsize=14,color='#17445d')
    comp=out/'comparisons'/'rectifier_R_RL_LE_RLE.svg'
    comp.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(comp,format='svg');fig.savefig(comp.with_suffix('.png'),dpi=125)
    plt.close(fig)
    return {'load_models':4,'circuits':len(results),'waveforms':4,'comparison':str(comp)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=Path('output_lcc/rectifier/advanced_loads'))
    args=parser.parse_args()
    print(build(args.output_dir))
