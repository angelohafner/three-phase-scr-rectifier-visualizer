#!/usr/bin/env python3
"""Ideal resistive and dynamic RL load models for a six-pulse SCR rectifier.

This module separates the DC load differential equation from ideal AC-side
commutation. The source and SCR models assume zero AC source inductance.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import rectifier_art as art
from rectifier_model import CircuitTopology, Highlight, UPPER, LOWER, PAIRS
from rectifier_renderer import CircuitRenderer

SCR_NAMES = ('T1', 'T2', 'T3', 'T4', 'T5', 'T6')


@dataclass(frozen=True)
class LoadParameters:
    """Per-unit phase voltage, equivalent load values, and trigger delay."""
    alpha_deg: float = 75.0
    resistance_ohm: float = 1.0
    inductance_mH: float = 8.0
    frequency_hz: float = 60.0
    phase_peak_pu: float = 1.0

    def __post_init__(self) -> None:
        if not 0 <= self.alpha_deg < 120:
            raise ValueError('Ideal R/RL firing angle must satisfy 0 <= alpha < 120 degrees')
        if self.resistance_ohm <= 0 or self.inductance_mH < 0:
            raise ValueError('Resistance must be positive; inductance cannot be negative')
        if self.frequency_hz <= 0 or self.phase_peak_pu <= 0:
            raise ValueError('Frequency and voltage amplitude must be positive')


@dataclass
class LoadWaveforms:
    """Continuous-time waveforms sampled at identical electrical-angle points."""
    theta_deg: np.ndarray
    phase: np.ndarray
    line: np.ndarray
    dc_v: np.ndarray
    dc_i: np.ndarray
    scr: dict[str, np.ndarray]
    phase_i: np.ndarray
    conducting_pair: np.ndarray
    alpha_deg: float
    load_type: str

    @property
    def blocked(self) -> np.ndarray:
        return self.conducting_pair < 0


def phase_voltages(theta_deg: np.ndarray, peak: float) -> np.ndarray:
    """Natural six-pulse reference: pair A+/C- commutates at theta=0."""
    radians = np.deg2rad(theta_deg)
    return peak * np.array([np.cos(radians),
                             np.cos(radians - 2 * np.pi / 3),
                             np.cos(radians + 2 * np.pi / 3)])


def line_voltages(phase: np.ndarray) -> np.ndarray:
    """Return v_ab, v_bc, v_ca without changing mathematical orientation."""
    return np.array([phase[0]-phase[1], phase[1]-phase[2], phase[2]-phase[0]])


def fired_pair(theta_deg: np.ndarray | float, alpha: float) -> tuple[np.ndarray, np.ndarray]:
    """Most recently gated pair and its age in degrees (double-pulse gating)."""
    angle = np.asarray(theta_deg, dtype=float)
    k = np.floor((angle-alpha)/60.0).astype(int)
    elapsed = angle-(60.0*k+alpha)
    return np.mod(k, 6), elapsed


def pair_voltage(phase: np.ndarray, pair_index: np.ndarray) -> np.ndarray:
    """Line voltage across the selected upper and lower bridge valves."""
    upper_indices = np.array([0,1,1,2,2,0], dtype=int)
    lower_indices = np.array([2,2,0,0,1,1], dtype=int)
    n = pair_index.size
    columns = np.arange(n)
    return phase[upper_indices[pair_index], columns] - phase[lower_indices[pair_index], columns]


def assemble(theta: np.ndarray, p: LoadParameters, load: str, dc_i: np.ndarray,
             pair: np.ndarray, dc_v: np.ndarray) -> LoadWaveforms:
    """Derive all SCR and phase currents from the exact selected valve pair."""
    phase=phase_voltages(theta,p.phase_peak_pu)
    scr={name:np.zeros(theta.size,dtype=float) for name in SCR_NAMES}
    for k,(high,low) in enumerate(PAIRS):
        active=pair==k
        scr[UPPER[high]][active]=dc_i[active]
        scr[LOWER[low]][active]=dc_i[active]
    phase_i=np.array([scr[UPPER[name]]-scr[LOWER[name]] for name in ('a','b','c')])
    return LoadWaveforms(theta,phase,line_voltages(phase),dc_v,dc_i,scr,phase_i,pair,p.alpha_deg,load)


class ResistiveLoad:
    """Exact ideal-switching R-load current with extinction at zero voltage."""
    def __init__(self,p:LoadParameters):
        self.p=p

    def sample(self,theta:np.ndarray) -> LoadWaveforms:
        a=np.asarray(theta,dtype=float)
        phase=phase_voltages(a,self.p.phase_peak_pu)
        pair,elapsed=fired_pair(a,self.p.alpha_deg)
        voltage=pair_voltage(phase,pair)
        duration=min(60.0,120.0-self.p.alpha_deg)
        active=(elapsed>=-1e-7)&(elapsed<duration-1e-8)&(voltage>0)
        conducting=np.where(active,pair,-1)
        dc_v=np.where(active,voltage,0)
        dc_i=dc_v/self.p.resistance_ohm
        return assemble(a,self.p,'R',dc_i,conducting,dc_v)


class ResistiveInductiveLoad:
    """Integrate R-L load current across firing and natural extinction events.

    The model assumes idealized zero-duration AC commutation (mu=0). A new
    SCR pair is gated at each alpha+60*k and receives current whenever the
    preceding pair is conducting or the new line voltage is positive. At a
    natural current zero, the SCRs block until a subsequent scheduled trigger.
    """
    def __init__(self,p:LoadParameters):
        self.p=p

    def sample(self,theta:np.ndarray,cycles:int=7)->LoadWaveforms:
        t=np.asarray(theta,dtype=float)
        if len(t)<2 or np.any(np.diff(t)<=0) or abs(t[0])>1e-8 or abs(t[-1]-360)>1e-7:
            raise ValueError('RL sampling requires sorted angles covering exactly 0..360')
        if self.p.inductance_mH <= 0:
            return ResistiveLoad(self.p).sample(t)
        # Discrete exponential integration: voltage is sampled at the midpoint
        # of each electrical-angle increment. Periodic transients are removed
        # by simulating several cycles before retaining the final cycle.
        n=t.size
        dtheta=float(t[1]-t[0]);
        if np.max(np.abs(np.diff(t)-dtheta))>1e-7:
            raise ValueError('RL requires a uniform angular grid')
        L=self.p.inductance_mH*1e-3
        tau_deg=360.0*self.p.frequency_hz*L/self.p.resistance_ohm
        smooth=math.exp(-dtheta/tau_deg)
        i=0.0; pair=-1
        stored_i=np.zeros(n); stored_v=np.zeros(n); stored_pair=np.full(n,-1,dtype=int)
        prev_sector=None
        for cycle in range(cycles):
            for j,angle in enumerate(t[:-1]):
                which, elapsed=fired_pair(float(angle)+1e-9,self.p.alpha_deg)
                k=int(which)
                current_sector=int(math.floor((float(angle)-self.p.alpha_deg+1e-9)/60))
                if current_sector != prev_sector:
                    # At firing, wide or double pulses permit a fresh pair to
                    # latch even after a disconnected-current interval.
                    ph=phase_voltages(np.array([angle+1e-9]),self.p.phase_peak_pu)
                    u=float(pair_voltage(ph,np.array([k]))[0])
                    pair=k if i>1e-10 or u>0 else -1
                    prev_sector=current_sector
                if pair>=0:
                    middle=float(angle+dtheta/2)
                    v0=phase_voltages(np.array([middle]),self.p.phase_peak_pu)
                    u=float(pair_voltage(v0,np.array([pair]))[0])
                    new_i=i*smooth + (u/self.p.resistance_ohm)*(1-smooth)
                    if new_i<=1e-10:
                        i=0.0;pair=-1
                        vdc=0.0
                    else:
                        i=new_i;vdc=u
                else:
                    i=0.0;vdc=0.0
                if cycle==cycles-1:
                    stored_i[j]=i;stored_v[j]=vdc;stored_pair[j]=pair
        stored_i[-1]=stored_i[0];stored_v[-1]=stored_v[0];stored_pair[-1]=stored_pair[0]
        return assemble(t,self.p,'RL',stored_i,stored_pair,stored_v)


def state_at_angle(w:LoadWaveforms,theta:float)->tuple[int|None,tuple[str,...]]:
    """Return currently conducting pair and the exact active SCR names."""
    j=int(np.argmin(abs(w.theta_deg-theta)))
    p=int(w.conducting_pair[j])
    return (None, ()) if p<0 else (p,tuple((UPPER[PAIRS[p][0]],LOWER[PAIRS[p][1]])))


class ResistiveCircuitRenderer:
    """Use the existing editable SCR bridge and replace zero-valued reactors by wires."""
    def __init__(self):
        self.topology=CircuitTopology()
        self.original=CircuitRenderer(self.topology)

    def render(self,p:LoadParameters,theta:float,conducting_pair:int|None,load_type:str="R")->ET.ElementTree:
        if load_type not in ("R", "RL"):
            raise ValueError("load_type must be R or RL")
        if conducting_pair is None:
            chosen=Highlight(frozenset(),frozenset(),frozenset(),frozenset(),False,False,
                             'THREE-PHASE SCR RECTIFIER · R LOAD')
        else:
            hi,lo=PAIRS[conducting_pair]
            # A graph-derived complete loop remains the source of truth for
            # activated conductors, including both SCR orientations.
            from rectifier_model import ConductionState
            st=ConductionState(1,'normal',((hi,lo),),frozenset((UPPER[hi],LOWER[lo])),0,60,0)
            found=self.topology.highlight(st)
            chosen=replace(found,inductors=(frozenset(('LDC',)) if load_type=='RL' else frozenset()),title='THREE-PHASE SCR RECTIFIER · '+load_type+' LOAD')
        tree=self.original.render(chosen)
        root=tree.getroot()
        components=root.find(f'.//{art.S}g[@id="components-base"]')
        active=root.find(f'.//{art.S}g[@id="components-active"]')
        for parent in list(root.iter()):
            for child in list(parent):
                tag=child.get('id','')
                if tag in {f'{prefix}-{item}' for prefix in ('base','selected') for item in (('ldc','la','lb','lc') if load_type=='R' else ('la','lb','lc'))}:
                    parent.remove(child)
                elif load_type=='R' and child.tag==art.S+'text' and child.get('x')=='1285' and child.get('y')=='337':
                    parent.remove(child)
        for phase in art.PHASES:
            y=art.Y[phase]
            art.line(components,art.X['coil_start'],y,art.X['feed_start'],y,art.C['ink'],3.4)
            if conducting_pair is not None and f'V{phase.upper()}' in chosen.sources:
                art.line(active,art.X['coil_start'],y,art.X['feed_start'],y,art.C['active'],4.8)
        if load_type=='R':
            art.line(components,art.X['load'],293,art.X['load'],373,art.C['ink'],3.4)
            if conducting_pair is not None:
                art.line(active,art.X['load'],293,art.X['load'],373,art.C['active'],4.8)
        headings=root.find(f'.//{art.S}g[@id="headings"]')
        legend=root.find(f'.//{art.S}g[@id="legend"]')
        for area in (headings,legend):
            for child in list(area):
                area.remove(child)
        art.txt(headings,65,78,'RECTIFIER · '+('PURE RESISTIVE LOAD' if load_type=='R' else 'RESISTIVE–INDUCTIVE LOAD'),size=32,bold=True)
        art.txt(headings,65,120,('Ideal AC sources  ·  No commutation overlap  ·  No DC reactor' if load_type=='R' else 'Ideal AC sources  ·  No commutation overlap  ·  DC smoothing reactor present'),size=18,color=art.C['muted'])
        art.element(headings,'rect',x=1180,y=46,width=285,height=80,rx=13,fill='#EAF0F7',stroke=art.C['border'])
        art.txt(headings,1195,73,'CURRENT STATE',size=13,bold=True,color=art.C['muted'])
        label='ALL SCRs OFF' if conducting_pair is None else ' + '.join(state_at_pair(conducting_pair))
        art.txt(headings,1195,105,label,size=22,bold=True,color=art.C['active'] if conducting_pair is not None else art.C['ink'])
        art.math_formula(legend,74,757,[('α','variable'),(' = ','roman'),(f'{p.alpha_deg:g}','roman'),('°','unit'),('  ·  ','roman'),('θ','variable'),(' = ','roman'),(f'{theta:g}','roman'),('°','unit')],size=21)
        reason=('The SCR pair carries current while the selected line voltage is positive.'
                if conducting_pair is not None else
                'No conducting path: the load current and DC voltage are both zero.')
        art.txt(legend,74,791,reason,size=17)
        art.txt(legend,74,820,('Double-pulse/wide gating is assumed after zero-current intervals.' if load_type=='R' else 'The load reactor stores energy and can sustain current through negative DC voltage.'),size=14,color=art.C['muted'])
        art.element(root,'desc').text=('Ideal R load with zero commutation overlap, no AC/DC reactors and no negative current.' if load_type=='R' else 'RL load with ideal AC-side commutation; the DC reactor stores energy and can maintain continuous current.')
        return tree


def state_at_pair(pair_index:int)->tuple[str,str]:
    hi,lo=PAIRS[pair_index]
    return UPPER[hi], LOWER[lo]


def apply_plot_style()->None:
    plt.rcParams.update({'font.family':'DejaVu Sans','mathtext.fontset':'stix','font.size':10,
                         'axes.titlesize':11,'axes.labelsize':9,'svg.fonttype':'none',
                         'figure.facecolor':'white','axes.facecolor':'white',
                         'axes.edgecolor':'#bccbd8','axes.spines.top':False,
                         'axes.spines.right':False})


def make_waveform_plot(w:LoadWaveforms,source:Path,active_window:tuple[float,float]|None=None)->None:
    """Export four synchronized vector panels for voltage, current and valves."""
    apply_plot_style()
    fig,ax=plt.subplots(4,1,figsize=(12,8.4),sharex=True,layout='constrained')
    th=w.theta_deg
    colors=('#d63248','#196bad','#119999')
    for j,label in enumerate((r'$v_a$',r'$v_b$',r'$v_c$')):
        ax[0].plot(th,w.phase[j],color=colors[j],lw=1.35,label=label)
    ax[0].set_ylim(-1.3*max(abs(w.phase.flatten())),1.3*max(abs(w.phase.flatten())))
    ax[0].set_ylabel(r'$v_\mathrm{phase}$ (p.u.)')
    for j,label in enumerate((r'$v_{ab}$',r'$v_{bc}$',r'$v_{ca}$')):
        ax[1].plot(th,w.line[j],color=colors[j],lw=1.25,label=label)
    ax[1].plot(th,w.dc_v,color='#b32840',lw=2.2,label=r'$v_\mathrm{dc}$')
    ax[1].set_ylim(-2.1,2.1);ax[1].set_ylabel('Voltage (p.u.)')
    ax[2].plot(th,w.dc_v,label=r'$v_\mathrm{dc}$',color='#126b9f',lw=1.6)
    ax[2].plot(th,w.dc_i,label=r'$i_\mathrm{dc}$',color='#ce2d45',lw=2.0)
    ax[2].set_ylim(-0.65,max(2.1,float(w.dc_i.max())*1.15));ax[2].set_ylabel('DC (p.u.)')
    for label,color in zip(SCR_NAMES,('#e32940','#6f8caa','#124f8b','#72a68d','#10a2a2','#9f92b4')):
        ax[3].plot(th,w.scr[label],label=label,color=color,lw=1.45)
    ax[3].set_ylim(-0.05,max(2.1,float(w.dc_i.max())*1.1));ax[3].set_ylabel('SCR current (p.u.)')
    ax[-1].set_xlabel(r'Electrical angle $\theta$ ($^\circ$)')
    for a in ax:
        a.set_xlim(0,360);a.set_xticks(np.arange(0,361,60));a.grid(alpha=.19)
        a.legend(loc='upper right',ncol=4,fontsize=8,framealpha=.9)
        if active_window:
            lo,hi=active_window
            if lo<=hi:a.axvspan(lo,hi,color='#e13348',alpha=.10)
            else:
                a.axvspan(0,hi,color='#e13348',alpha=.10)
                a.axvspan(lo,360,color='#e13348',alpha=.10)
    fig.suptitle(f"{w.load_type} LOAD · $\\alpha={w.alpha_deg:.0f}^\\circ$ · Ideal AC commutation ($\\mu=0^\\circ$)",fontweight='bold',fontsize=14)
    source.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(source,format='svg')
    fig.savefig(source.with_suffix('.png'),dpi=125)
    plt.close(fig)


def make_comparison(r:LoadWaveforms,rl:LoadWaveforms,target:Path)->None:
    """Use identical scales to compare memoryless and energy-storing loads."""
    apply_plot_style()
    f,axs=plt.subplots(2,2,figsize=(14,7.7),sharex=True,layout='constrained')
    for column,signal,title in [(0,r,'R LOAD'),(1,rl,'RL LOAD')]:
        axs[0,column].plot(signal.theta_deg,signal.dc_v,color='#17699a',lw=1.8,label=r'$v_\mathrm{dc}$')
        axs[0,column].axhline(0,color='#9aaec0',lw=.7)
        axs[0,column].set_title(title,fontweight='bold')
        axs[0,column].set_ylabel('Voltage (p.u.)')
        axs[1,column].plot(signal.theta_deg,signal.dc_i,color='#cc304c',lw=2,label=r'$i_\mathrm{dc}$')
        axs[1,column].set_ylabel('Current (p.u.)')
        axs[1,column].set_xlabel(r'Electrical angle $\theta$ ($^\circ$)')
        for a in (axs[0,column],axs[1,column]):
            a.set_xlim(0,360);a.set_xticks(np.arange(0,361,60));a.grid(alpha=.16)
            a.legend(loc='upper right',fontsize=9)
    for a in axs[0]:a.set_ylim(-.6,2)
    for a in axs[1]:a.set_ylim(0,2.1)
    f.suptitle(r'Pure $R$ versus $RL$ load — same firing angle, different current dynamics',fontweight='bold')
    target.parent.mkdir(parents=True,exist_ok=True)
    f.savefig(target,format='svg');f.savefig(target.with_suffix('.png'),dpi=125)
    plt.close(f)


def make_sheet(circuit:Path,plot:Path,target:Path)->None:
    """Build a standalone editable-SVG teaching sheet without rasterization."""
    import copy
    svg_ns=art.SVG_NS
    base=ET.parse(circuit).getroot()
    waveform=ET.parse(plot).getroot()
    sheet=ET.Element(art.S+'svg',{'viewBox':'0 0 1520 2040','width':'1520','height':'2040'})
    sheet.set('xmlns:xlink','http://www.w3.org/1999/xlink')
    top=art.element(sheet,'g',transform='translate(0,0)')
    top.append(copy.deepcopy(base))
    bottom=art.element(sheet,'g',transform='translate(65,860) scale(1.06)')
    waveform.set('width','1300');waveform.set('height','1050')
    bottom.append(copy.deepcopy(waveform))
    tree=ET.ElementTree(sheet)
    tree.write(target,encoding='utf-8',xml_declaration=True)
    from PIL import Image
    import cairosvg
    from io import BytesIO
    img1=Image.open(BytesIO(cairosvg.svg2png(url=str(circuit),output_width=1200))).convert('RGB')
    img2=Image.open(plot.with_suffix('.png')).convert('RGB')
    canvas=Image.new('RGB',(1200,1650),'white')
    canvas.paste(img1.resize((1200,671)),(0,0));canvas.paste(img2.resize((1200,850)),(0,710))
    canvas.save(target.with_suffix('.png'),optimize=True)


def build_all(out:Path)->dict:
    """Export reproducible R-load scenes and a matched R versus RL example."""
    out.mkdir(parents=True,exist_ok=True)
    src=ResistiveCircuitRenderer();manifest=[]
    angles=np.linspace(0,360,1801)
    for alpha in (0,30,75,90):
        p=LoadParameters(alpha_deg=alpha)
        signals=ResistiveLoad(p).sample(angles)
        conduction=alpha+min(22.5,(120-alpha)/2)
        states=[('conducting',conduction)]
        if alpha>60:
            states.append(('blocked',120+(alpha-60)/2))
        for kind,theta in states:
            pair,_=state_at_angle(signals,theta)
            name=f'rectifier_R_alpha_{alpha:03d}_{kind}'
            circ=out/'circuits'/f'{name}.svg'
            circ.parent.mkdir(parents=True,exist_ok=True)
            ET.ElementTree(src.render(p,theta,pair).getroot()).write(circ,encoding='utf-8',xml_declaration=True)
            waveform=out/'waveforms'/f'{name}.svg'
            window=(alpha,120) if kind=='conducting' else (120,60+alpha)
            make_waveform_plot(signals,waveform,window)
            sheet=out/'sheets'/f'{name}.svg';sheet.parent.mkdir(parents=True,exist_ok=True)
            make_sheet(circ,waveform,sheet)
            manifest.append({'name':name,'alpha_deg':alpha,'kind':kind,'theta_deg':theta,
                             'active_scrs':list(state_at_angle(signals,theta)[1]),
                             'blocked_fraction':float(np.mean(signals.blocked))})
    for k in range(6):
        p=LoadParameters(alpha_deg=30)
        theta=30+60*k+25
        name=f'rectifier_R_pair_{k+1:02d}'
        signal=ResistiveLoad(p).sample(angles)
        pair,_=state_at_angle(signal,theta)
        circ=out/'circuits'/f'{name}.svg'
        ET.ElementTree(src.render(p,theta,pair).getroot()).write(circ,encoding='utf-8',xml_declaration=True)
        manifest.append({'name':name,'theta_deg':theta,'alpha_deg':30,'active_scrs':list(state_at_angle(signal,theta)[1])})
    p=LoadParameters(alpha_deg=75,inductance_mH=8)
    r=ResistiveLoad(p).sample(angles)
    rl=ResistiveInductiveLoad(p).sample(angles)
    comparison=out/'comparisons'/'rectifier_R_vs_RL.svg'
    make_comparison(r,rl,comparison)
    rl_circ=out/'circuits'/'rectifier_RL_alpha_075.svg'
    q,_=state_at_angle(rl,127.5)
    ET.ElementTree(src.render(p,127.5,q,load_type='RL').getroot()).write(rl_circ,encoding='utf-8',xml_declaration=True)
    rl_plot=out/'waveforms'/'rectifier_RL_alpha_075.svg'
    make_waveform_plot(rl,rl_plot,(120,135))
    make_sheet(rl_circ,rl_plot,out/'sheets'/'rectifier_RL_alpha_075.svg')
    (out/'manifest_R.json').write_text(json.dumps({'model':'ideal R and dynamic RL, zero AC commutation inductance','examples':manifest},indent=2),encoding='utf-8')
    return {'individual_scenarios':len(manifest),'figure_root':str(out),
            'R_blocked_at_75':round(float(np.mean(r.blocked)),3),
            'RL_blocked_at_75':round(float(np.mean(rl.blocked)),3)}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output-dir',type=Path,default=Path('output_lcc/rectifier/resistive_load'))
    args=ap.parse_args()
    print(json.dumps(build_all(args.output_dir),indent=2))

if __name__=='__main__':
    main()
