"""Independent sign-consistency regression for both LCC converter stations."""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]


def test_signed_inverter_dc_voltage_and_power_are_identical_across_models():
    if not shutil.which('node'):
        pytest.skip('Node.js is required for electrical cross-model verification')
    src='\n'.join((ROOT/'presentation/src'/n).read_text(encoding='utf-8')
        for n in ('waveforms.js','current_source.js','charts.js'))
    test=src+'''
    const p={alphaR:15,alphaI:145,muR:12,muI:15,idc:1,vPeak:1,
      csOverlapMode:'manual',csLc:.2};
    const n=360,avg=f=>Array.from({length:n},(_,x)=>f(x)).reduce((a,b)=>a+b,0)/n;
    const vR=avg(x=>LCC.sample('rectifier',x,p).dc);
    const vI=avg(x=>LCC.sample('inverter',x,p,LCC.OFFSET).dc);
    const vCs=avg(x=>CurrentSourceModel.sample(x,{...p,_csSide:'inverter'}).dc);
    const powers=CurrentSourceModel.inverterPower(p);
    const plot=ChartView.makeSeries('inverter',p,'dc',LCC.stateInfo(1),'all');
    const plotted=plot[0].series[0].values.reduce((a,b)=>a+b,0)/plot[0].series[0].values.length;
    const joint=ChartView.makeSeries('hvdc',p,'dc',{r:1,i:1},'all');
    const plotJoint=joint[0].series[1].values.reduce((a,b)=>a+b,0)/joint[0].series[1].values.length;
    console.log(JSON.stringify({vR,vI,vCs,powers,plotted,plotJoint}));
    '''
    result=subprocess.run(['node','-e',test],capture_output=True,text=True,check=True,cwd=ROOT)
    values=json.loads(result.stdout)
    assert values['vR']>0
    assert values['vI']<0
    assert values['powers']['rectifier']>0
    assert values['powers']['inverter']<0
    assert values['vI']==pytest.approx(values['vCs'],abs=1e-9)
    assert values['vI']==pytest.approx(values['powers']['inverter'],abs=1e-9)
    assert values['vI']==pytest.approx(values['plotted'],abs=0.015)
    assert values['vI']==pytest.approx(values['plotJoint'],abs=0.015)
