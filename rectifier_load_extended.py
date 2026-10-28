#!/usr/bin/env python3
"""Independent Python R/RL/LE/RLE six-pulse teaching model and SVG/PDF-free plots.

The model is ideal, has no AC source inductance, and avoids claiming unique
steady state for undamped LE loads. Positive signed E opposes positive DC current.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import math
import numpy as np

PAIRS = ((0,2),(1,2),(1,0),(2,0),(2,1),(0,1))
SCRS = (('T1','T6'),('T3','T6'),('T3','T2'),('T5','T2'),('T5','T4'),('T1','T4'))
UPPER = ('T1','T3','T5')
LOWER = ('T2','T4','T6')
NAMES = ('T1','T2','T3','T4','T5','T6')
STEP = .25
N = 1440


@dataclass(frozen=True)
class DCLoad:
    """Ideal six-pulse bridge parameters with 1-ohm-equivalent normalization."""
    kind: str = 'RLE'
    alpha_deg: float = 75.0
    resistance_ohm: float = 1.0
    inductance_mH: float = 8.0
    emf_pu: float = 0.0
    phase_peak_pu: float = 1.0
    frequency_hz: float = 60.0

    def __post_init__(self):
        if self.kind not in ('R','RL','LE','RLE'):
            raise ValueError('Load must be R, RL, LE, or RLE')
        if not (0 <= self.alpha_deg < 170):
            raise ValueError('Firing angle outside 0..170 degrees')
        if self.phase_peak_pu <= 0 or self.frequency_hz <= 0:
            raise ValueError('Source parameters must be positive')
        if self.resistance_ohm < 0 or self.inductance_mH < 0 or not math.isfinite(self.emf_pu):
            raise ValueError('Invalid load parameters')
        if self.kind in ('R','RL','RLE') and self.resistance_ohm <= 0:
            raise ValueError('R must be positive for R/RL/RLE')
        if self.kind in ('LE','RLE') and self.inductance_mH <= 0:
            raise ValueError('L must be positive for LE/RLE')

    @property
    def r(self):
        return 0.0 if self.kind=='LE' else self.resistance_ohm

    @property
    def lh(self):
        return 0.0 if self.kind=='R' else self.inductance_mH/1000

    @property
    def e(self):
        return self.emf_pu if self.kind in ('LE','RLE') else 0.0


@dataclass
class DCTrace:
    theta: np.ndarray
    voltage: np.ndarray
    current: np.ndarray
    pair: np.ndarray
    phase: np.ndarray
    scr_current: dict[str,np.ndarray]
    scr_voltage: dict[str,np.ndarray]
    periodic: bool
    details: str


def phases(theta: float, peak: float):
    t=math.radians(theta)
    return np.array([peak*math.cos(t),peak*math.cos(t-2*math.pi/3),
                     peak*math.cos(t+2*math.pi/3)])


def valve_voltages(phase: np.ndarray, pair: int):
    """Return NaNs while both DC pole potentials are electrically floating."""
    if pair<0:
        return {name:math.nan for name in NAMES}
    upper,lower=PAIRS[pair]
    plus,minus=phase[upper],phase[lower]
    values={}
    for k in range(3):
        values[UPPER[k]]=float(phase[k]-plus)
        values[LOWER[k]]=float(minus-phase[k])
    return values


def sample(settings: DCLoad) -> DCTrace:
    """Numerically integrate repeated cycles; flag nonunique/aperiodic states."""
    dtheta=STEP
    dt=dtheta/(360*settings.frequency_hz)
    l=settings.lh
    r=settings.r
    e=settings.e
    count=24 if r==0 else min(120,max(16,math.ceil(l/r*settings.frequency_hz*14)))
    current=0.0
    last_sector=None
    previous_end=0
    stored=[]
    periodic=False
    for cycle in range(count+1):
        if cycle==count:
            stored=[]
        for j in range(N):
            angle=j*dtheta
            midpoint=angle+dtheta/2
            sector=math.floor((midpoint-settings.alpha_deg+1e-10)/60)
            pair=sector%6
            v=phases(midpoint,settings.phase_peak_pu)
            up,lo=PAIRS[pair]
            bridge=float(v[up]-v[lo])
            drive=bridge-e
            if sector!=last_sector:
                last_sector=sector
            if current>1e-11 or drive>1e-11:
                if l>0:
                    current=(current*math.exp(-r*dt/l)+drive/r*(-math.expm1(-r*dt/l))) if r else current+drive*dt/l
                else:
                    current=max(0.0,drive/r)
                if current<=1e-11:
                    current=0.0
                    pair=-1
            else:
                current=0.0
                pair=-1
            if cycle==count:
                stored.append((current,pair))
        if cycle==count-1:
            previous_end=current
        if cycle==count:
            periodic=abs(current-previous_end)<1e-5*max(1,abs(current)) and r>0
    angle=np.linspace(0,360,N+1)
    currents=np.array([stored[j%N][0] for j in range(N+1)])
    pairs=np.array([stored[j%N][1] for j in range(N+1)],dtype=int)
    p=np.array([phases(t,settings.phase_peak_pu) for t in angle])
    vdc=np.array([(p[j,PAIRS[pairs[j]][0]]-p[j,PAIRS[pairs[j]][1]]) if pairs[j]>=0 else e for j in range(N+1)])
    scr_i={name:np.array([currents[j] if pairs[j]>=0 and name in SCRS[pairs[j]] else 0.0 for j in range(N+1)]) for name in NAMES}
    volts={name:np.array([valve_voltages(p[j],int(pairs[j]))[name] for j in range(N+1)]) for name in NAMES}
    details=('Undamped LE: current depends on initial conditions; no unique attracting steady state.'
             if r==0 else 'Periodic steady state reached.' if periodic else 'No periodic steady state verified.')
    return DCTrace(angle,vdc,currents,pairs,p,scr_i,volts,periodic,details)


def save_plot(trace: DCTrace, target: Path, label: str) -> Path:
    """Create a publication-ready, MathText-formatted SVG with distinct line dashes."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','mathtext.fontset':'stix',
                         'svg.fonttype':'none','axes.spines.top':False,
                         'axes.spines.right':False,'font.size':10})
    colors=('#af3249','#0a7d8b','#a36d30','#6b60a0','#24836f','#ab6741')
    styles=('-', '--', ':', '-.', (0,(6,2,1,2)), (0,(2,3,7,3)))
    fig,axs=plt.subplots(3,1,figsize=(13,8.1),sharex=True,layout='constrained')
    axs[0].plot(trace.theta,trace.voltage,color=colors[1],linestyle='-',alpha=.84,label=r'$v_{\mathrm{dc}}$')
    axs[0].set_ylabel('DC voltage (pu)')
    axs[1].plot(trace.theta,trace.current,color=colors[0],linestyle='--',alpha=.84,label=r'$i_{\mathrm{dc}}$')
    axs[1].set_ylabel('DC current (pu)')
    for i,name in enumerate(NAMES):
        axs[2].plot(trace.theta,trace.scr_voltage[name],color=colors[i],linestyle=styles[i],
                    alpha=.78,label=rf'$v_{{AK,{i+1}}}$')
    axs[2].set_ylabel(r'$v_{AK}$ (pu)')
    axs[2].set_xlabel(r'Electrical angle $\theta$ ($^\circ$)')
    active=trace.pair>=0
    starts=np.where(np.diff(active.astype(int),prepend=0)==1)[0]
    ends=np.where(np.diff(active.astype(int),append=0)==-1)[0]
    for ax in axs:
        for a,b in zip(starts,ends):
            ax.axvspan(trace.theta[a],trace.theta[min(b,len(trace.theta)-1)],color='#0e9b9b',alpha=.075)
        ax.set_xlim(0,360);ax.set_xticks(np.arange(0,361,60));ax.grid(alpha=.16)
        ax.axhline(0,color='#a8b9bf',alpha=.65,linewidth=.7)
        ax.legend(loc='upper right',ncol=6,fontsize=9,framealpha=.9)
    fig.suptitle(label+': '+trace.details,fontsize=12,color='#173e56')
    target.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(target,format='svg')
    plt.close(fig)
    return target


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=Path('output_lcc/extended'))
    args=parser.parse_args()
    for kind in ('R','RL','LE','RLE'):
        settings=DCLoad(kind=kind,alpha_deg=70,emf_pu=-.4)
        trace=sample(settings)
        path=save_plot(trace,args.out/f'{kind.lower()}-scr-voltage.svg',kind)
        print(path)


if __name__=='__main__':
    main()
