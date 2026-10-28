#!/usr/bin/env python3
"""Consistent SVG/PNG waveform charts and vector-only circuit/waveform sheets."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
import re
from xml.etree import ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from rectifier_model import CommutationSequence
from lcc_waveform_model import SCR_ID, StationCurves, WaveformConfig

SVGNS = 'http://www.w3.org/2000/svg'
S = '{'+SVGNS+'}'
ET.register_namespace('', SVGNS)
COLORS = ('#1f65a5', '#d18c19', '#159d87')
INK = '#1b283a'
RED = '#d62435'
GRID = '#d5e0e9'
MUTED = '#718091'


@dataclass(frozen=True)
class ViewSpec:
    """One exact drawing focus; no fabricated interval is allowed."""
    title: str
    explanation: str
    windows: tuple[tuple[float,float], ...]
    rectifier_state: int | None = None
    inverter_state: int | None = None
    combined_state: int | None = None
    alpha_r: float | None = None
    alpha_i: float | None = None
    mu_r: float | None = None
    mu_i: float | None = None
    gamma_i: float | None = None


class WaveformRenderer:
    """Plot with constant axes and highlighted intervals matching circuit figures."""

    def __init__(self, config: WaveformConfig):
        self.config = config
        plt.rcParams.update({
            'font.family': 'STIXGeneral',
            'mathtext.fontset': 'stix',
            'svg.fonttype': 'none',
            'font.size': 10.7,
            'axes.titlesize': 11,
            'axes.labelsize': 10.5,
            'legend.fontsize': 8.8,
            'axes.linewidth': .8,
            'savefig.facecolor': 'white',
            'figure.facecolor': 'white',
        })

    @staticmethod
    def _style(ax, *, ylim: tuple[float,float] | None = None) -> None:
        ax.set_xlim(0,360)
        ax.set_xticks([0,60,120,180,240,300,360])
        ax.grid(axis='x', color=GRID, linewidth=.7)
        ax.grid(axis='y', color=GRID, linewidth=.55, alpha=.75)
        ax.spines[['top','right']].set_visible(False)
        ax.spines[['bottom','left']].set_color('#9aa9b9')
        ax.tick_params(colors=MUTED, length=3)
        if ylim:
            ax.set_ylim(*ylim)

    @staticmethod
    def _shade(ax, view: ViewSpec) -> None:
        for lo,hi in view.windows:
            ax.axvspan(lo,hi,facecolor=RED,alpha=.115,zorder=0)
            ax.axvline(lo,color=RED,linewidth=.9,linestyle='--',alpha=.65)
            ax.axvline(hi,color=RED,linewidth=.9,linestyle='--',alpha=.65)

    @staticmethod
    def _emphasize(ax, x: np.ndarray, y: np.ndarray, view: ViewSpec,
                   *, linestyle: str = '-', width: float = 2.25) -> None:
        for lo,hi in view.windows:
            mask=(x>=lo-1e-9)&(x<=hi+1e-9)
            if np.count_nonzero(mask)>=2:
                ax.plot(x[mask],y[mask],color=RED,linewidth=width,
                        linestyle=linestyle,zorder=8)

    def _wave_stages(self, c: StationCurves, view: ViewSpec,
                     *, include_line: bool) -> list[tuple[str, str, list[tuple[np.ndarray,str,int]]]]:
        """Return plot descriptions with consistent per-signal axis ranges."""
        rows=[]
        side=('r' if c.operation=='rectifier' else 'i')
        if self.config.show_phase:
            rows.append((f'{c.label} · AC source voltages',r'$v_{a,b,c}$ (p.u.)',
                         [(c.phase_v[i],rf'$v_{{{p}}}$',i) for i,p in enumerate('abc')]))
        if self.config.show_line and include_line:
            rows.append((f'{c.label} · line-to-line voltages',r'$v_{LL}$ (p.u.)',
                         [(c.line_v[i],rf'$v_{{{p}}}$',i) for i,p in enumerate(('ab','bc','ca'))]))
        if self.config.show_scr:
            for group, scr in [('upper',('T1','T3','T5')),('lower',('T2','T4','T6'))]:
                rows.append((f'{c.label} · {group} SCR currents',r'$i_T$ (p.u.)',
                             [(c.scr_i[SCR_ID[k]],rf'$i_{{{k}}}$',i)
                              for i,k in enumerate(scr)]))
            rows.append((f'{c.label} · three-phase grid currents',r'$i_{a,b,c}$ (p.u.)',
                         [(c.ac_i[i],rf'$i_{{{p}}}$',i) for i,p in enumerate('abc')]))
        if self.config.show_dc:
            rows.append((f'{c.label} · positive DC pole-to-return voltage',r'$v_{\mathrm{dc}}$ (p.u.)',
                         [(c.dc_v_ideal,r'$v_{\mathrm{ideal}}$',0),
                          (c.dc_v_overlap,r'$v_{\mathrm{overlap}}$',1)]))
        return rows

    def plot(self, view: ViewSpec, rectifier: StationCurves | None,
             inverter: StationCurves | None, svg: Path, png: Path | None = None) -> Path:
        if rectifier is None and inverter is None:
            raise ValueError('A plot needs at least one station')
        both=rectifier is not None and inverter is not None
        stages=[]
        if rectifier is not None:
            stages.extend([(rectifier,row) for row in self._wave_stages(
                rectifier,view,include_line=True)])
        if inverter is not None:
            stages.extend([(inverter,row) for row in self._wave_stages(
                inverter,view,include_line=not both)])
        if self.config.show_idc:
            reference=rectifier if rectifier is not None else inverter
            stages.append((reference,('Common smoothed DC current' if both else 'Smoothed DC current',
                                     r'$i_{\mathrm{dc}}$ (p.u.)',
                                     [(reference.dc_i,r'$i_{\mathrm{dc}}$',0)])))
        if not stages:
            raise ValueError('No waveform panels are enabled')
        n=len(stages)
        fig,axes=plt.subplots(n,1,figsize=(14.4,max(6.2,1.51*n+1.45)),sharex=True,
                              constrained_layout=False)
        axes=np.atleast_1d(axes)
        for ax,(station,(title,ylab,curves)) in zip(axes,stages):
            self._shade(ax,view)
            x=station.theta
            kind='scr' if 'SCR currents' in title else ('dc_voltage' if 'pole-to-return voltage' in title else 'other')
            for j,(values,label,cindex) in enumerate(curves):
                color=COLORS[cindex]
                ls='--' if kind=='dc_voltage' and j==0 else '-'
                if kind=='dc_voltage':
                    color=MUTED if j==0 else '#15669f'
                ax.plot(x,values,color=color,linewidth=1.28,alpha=.92,linestyle=ls,label=label)
                if kind=='scr' and self.config.show_scr:
                    # The red overlay is limited to valve traces of the active state.
                    selected = view.rectifier_state if station.operation=='rectifier' else view.inverter_state
                    if selected is not None:
                        current_state=CommutationSequence(station.mu).state(selected)
                        valve_text=label.replace('$','')
                        if any(k in valve_text for k in current_state.scrs):
                            self._emphasize(ax,x,values,view)
                elif kind=='dc_voltage' and (j==len(curves)-1):
                    self._emphasize(ax,x,values,view,width=2.0)
                elif 'line-to-line voltages' in title:
                    sel=view.rectifier_state if station.operation=='rectifier' else view.inverter_state
                    if sel is not None:
                        st=CommutationSequence(station.mu).state(sel)
                        if st.is_overlap:
                            # A/B, B/C or C/A: the commutation-voltage source.
                            k_phase={'T1':'a','T2':'a','T3':'b','T4':'b','T5':'c','T6':'c'}
                            pa,pb=k_phase[st.outgoing],k_phase[st.incoming]
                            wanted=frozenset((pa,pb))
                            pairs=[frozenset(('a','b')),frozenset(('b','c')),frozenset(('c','a'))]
                            if wanted==pairs[j]:
                                self._emphasize(ax,x,values,view,width=2.0)
                        else:
                            pa,pb=st.pairs[0]
                            pairs=[frozenset(('a','b')),frozenset(('b','c')),frozenset(('c','a'))]
                            if frozenset((pa,pb))==pairs[j]:
                                self._emphasize(ax,x,values,view,width=2.0)
                elif 'AC source voltages' in title:
                    sel=view.rectifier_state if station.operation=='rectifier' else view.inverter_state
                    if sel is not None:
                        st=CommutationSequence(station.mu).state(sel)
                        involved={phase for pair in st.pairs for phase in pair}
                        if 'abc'[j] in involved:
                            self._emphasize(ax,x,values,view,width=1.8)
                elif 'grid currents' in title or 'Smoothed DC current' in title:
                    self._emphasize(ax,x,values,view,width=1.9)
            ax.set_title(title,loc='left',color=INK,pad=4,fontsize=10.4)
            ax.set_ylabel(ylab,fontsize=10.5)
            maxv=self.config.ac_peak
            curmax=max(np.max(np.abs(y)) for y,_,_ in curves)
            if kind=='dc_voltage':
                lim=max(2.4*maxv,curmax*1.12)
                axis_limit=(-.12*lim,lim)
            elif 'voltages' in title:
                lim=(1.86*maxv if 'line-to-line' in title else 1.16*maxv)
                axis_limit=(-lim,lim)
            elif kind=='scr':
                axis_limit=(-.08*self.config.dc_current,1.12*self.config.dc_current)
            elif 'currents' in title and 'grid' in title:
                axis_limit=(-1.14*self.config.dc_current,1.14*self.config.dc_current)
            else:
                axis_limit=(0,1.16*self.config.dc_current)
            self._style(ax,ylim=axis_limit)
            ax.legend(loc='upper right',ncol=min(len(curves),3),frameon=False,
                      fontsize=8.7,handlelength=2.7,bbox_to_anchor=(1.0,1.29))
        axes[-1].set_xlabel(r'Electrical angle $\theta$ ($^\circ$)',fontsize=11.8)
        fig.suptitle(view.title,fontsize=17,fontweight='bold',x=.083,y=.984,ha='left',color=INK)
        fig.text(.083,.947,view.explanation,ha='left',va='top',color='#596b7c',fontsize=9.8)
        angles=[]
        for key,value in [('r',view.alpha_r),('i',view.alpha_i)]:
            if value is not None:
                angles.append(rf'$\alpha_{{\mathrm{{{key}}}}}={value:g}^\circ$')
        for key,value in [('r',view.mu_r),('i',view.mu_i)]:
            if value is not None:
                angles.append(rf'$\mu_{{\mathrm{{{key}}}}}={value:g}^\circ$')
        if view.gamma_i is not None:
            angles.append(rf'$\gamma_{{\mathrm{{i}}}}={view.gamma_i:g}^\circ$')
        fig.text(.083,.912,'   |   '.join(angles),color=INK,fontsize=11,ha='left')
        fig.text(.083,.012,'Conceptual model only: ideal sinusoidal sources, constant DC current, linear current transfer during overlap;'
                 ' equal-reactance voltage average. Not an EMT solution.',color=MUTED,fontsize=9,ha='left')
        fig.subplots_adjust(left=.083,right=.976,top=.884,bottom=.066,hspace=.70)
        svg.parent.mkdir(parents=True,exist_ok=True)
        fig.savefig(svg,format='svg',metadata={'Creator':'LCC concept waveform generator'})
        if png is not None:
            fig.savefig(png,format='png',dpi=self.config.png_dpi)
        plt.close(fig)
        return svg


class FigureSynchronizer:
    """Build an editable one-file sheet without rasterizing the SVG circuits."""

    @staticmethod
    def _prefix_identifiers(root: ET.Element,prefix:str)->None:
        ids={e.get('id'): prefix+e.get('id') for e in root.iter() if e.get('id')}
        for node in root.iter():
            old=node.get('id')
            if old:
                node.set('id',ids[old])
            for key,value in list(node.attrib.items()):
                if '#'+next(iter(ids),'_') not in value and 'url(#' not in value and not key.endswith('href'):
                    continue
                updated=value
                for o,n in ids.items():
                    updated=updated.replace('url(#'+o+')','url(#'+n+')')
                    if (key.endswith('href') and updated=='#'+o):
                        updated='#'+n
                node.set(key,updated)

    @staticmethod
    def _nested(parent:ET.Element, svg_file:Path, width:float,height:float,
                x:float,y:float,prefix:str)->None:
        src=ET.parse(svg_file).getroot()
        viewbox=src.get('viewBox')
        if not viewbox:
            raise ValueError('SVG requires a viewBox: '+str(svg_file))
        el=copy.deepcopy(src)
        FigureSynchronizer._prefix_identifiers(el,prefix)
        el.attrib.update({'x':str(x),'y':str(y),'width':str(width),'height':str(height),
                          'preserveAspectRatio':'xMidYMid meet'})
        parent.append(el)

    def compose(self, circuit_svg:Path,wave_svg:Path,dest:Path,title:str,
                png:Path|None=None)->Path:
        source=ET.parse(circuit_svg).getroot()
        vb=source.get('viewBox','').split()
        if len(vb)!=4:
            raise ValueError('Circuit SVG has no valid viewBox')
        ratio=float(vb[3])/float(vb[2]); width=1700
        circuit_height=min(770,max(475,width*ratio))
        wave_svg_root=ET.parse(wave_svg).getroot()
        wv=wave_svg_root.get('viewBox','').split()
        if len(wv)!=4:
            raise ValueError('Waveform SVG has no valid viewBox')
        waveform_height=width*float(wv[3])/float(wv[2])
        height=int(circuit_height+waveform_height+220)
        root=ET.Element(S+'svg',{'width':str(width),'height':str(height),
                                 'viewBox':f'0 0 {width} {height}',
                                 'version':'1.1'})
        ET.SubElement(root,S+'title').text=title
        ET.SubElement(root,S+'rect',{'width':str(width),'height':str(height),'fill':'#ffffff'})
        ET.SubElement(root,S+'text',{'x':'50','y':'61','fill':INK,'font-size':'31',
                                     'font-family':'STIXGeneral,DejaVu Serif',
                                     'font-weight':'bold'}).text=title
        self._nested(root,circuit_svg,width-60,circuit_height,30,82,'circ-')
        y=circuit_height+105
        ET.SubElement(root,S+'line',{'x1':'50','x2':str(width-50),'y1':str(y-7),
                                     'y2':str(y-7),'stroke':'#d4dce5','stroke-width':'2'})
        self._nested(root,wave_svg,width-60,waveform_height,30,y,'wave-')
        dest.parent.mkdir(parents=True,exist_ok=True)
        ET.ElementTree(root).write(dest,encoding='utf-8',xml_declaration=True)
        if png is not None:
            # Raster previews are composed from existing PNGs. SVG remains all-vector.
            # This avoids slow CairoSVG rendering of deeply nested Matplotlib text.
            from PIL import Image, ImageDraw, ImageFont
            preview=circuit_svg.with_suffix('.png')
            wave_preview=wave_svg.with_suffix('.png')
            if not preview.exists():
                raise FileNotFoundError(f'Circuit PNG preview is required: {preview}')
            if not wave_preview.exists():
                raise FileNotFoundError(f'Waveform PNG preview is required: {wave_preview}')
            cw=1200
            with Image.open(preview) as cir, Image.open(wave_preview) as wav:
                ci=cir.convert('RGB')
                wa=wav.convert('RGB')
                ci=ci.resize((cw,round(ci.height*cw/ci.width)),Image.Resampling.LANCZOS)
                wa=wa.resize((cw,round(wa.height*cw/wa.width)),Image.Resampling.LANCZOS)
            output=Image.new('RGB',(cw,ci.height+wa.height+108),'white')
            draw=ImageDraw.Draw(output)
            font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',21)
            draw.text((30,20),title[:85],fill=INK,font=font)
            output.paste(ci,(0,65))
            draw.line((20,ci.height+73,cw-20,ci.height+73),fill=GRID,width=2)
            output.paste(wa,(0,ci.height+91))
            output.save(png,optimize=True)
        return dest
