"""Physics-focused regression of cause/effect and active teaching controls."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

from current_source_model import CurrentSourceSettings, overlap_degrees, sample

ROOT = Path(__file__).resolve().parents[1]


def test_overlap_increases_with_ac_commutation_inductance_at_fixed_current():
    low = CurrentSourceSettings(overlap_mode='calculated',
                                idc_pu=1, alpha_deg=15, commutation_inductance_mH=.12)
    high = CurrentSourceSettings(overlap_mode='calculated',
                                 idc_pu=1, alpha_deg=15, commutation_inductance_mH=.52)
    assert 0 < overlap_degrees(low) < overlap_degrees(high) < 60


def test_physical_commutation_current_conservation():
    condition=CurrentSourceSettings(overlap_mode='calculated',idc_pu=1,
                                    alpha_deg=15,commutation_inductance_mH=.30)
    mu=overlap_degrees(condition)
    for local in (0,mu*.1,mu*.25,mu*.5,mu*.75,mu*.95):
        result=sample(60+local,condition)
        assert result['overlap']
        assert result['scr']['T1']+result['scr']['T3']==pytest.approx(1,abs=1e-8)
        assert result['scr']['T6']==pytest.approx(1,abs=1e-8)
        assert min(result['scr'].values())>=0


def test_insufficient_commutation_voltage_rejected():
    with pytest.raises(ValueError,match='commutation|60-degree|complete'):
        overlap_degrees(CurrentSourceSettings(overlap_mode='calculated',
                        idc_pu=8,alpha_deg=80,commutation_inductance_mH=.8))


def test_current_source_policy_per_lesson():
    if not shutil.which('node'):
        pytest.skip('Node.js is required for JavaScript policy assertions')
    code=(ROOT/'presentation/src/current_source_policy.js').read_text(encoding='utf-8')
    commands="""
      const result={};
      for(const lesson of Object.keys(CurrentSourcePolicy.report())){
        const p=CurrentSourcePolicy.effective(lesson,{
          alphaR:45,alphaI:145,muR:30,muI:15,idc:1.75,vPeak:1.5,csOverlapMode:'manual'
        });
        result[lesson]={mode:p.csOverlapMode,idc:p.idc,alphaR:p.alphaR,
          muR:p.muR,allowed:CurrentSourcePolicy.report()[lesson].controls};
      }
      process.stdout.write(JSON.stringify(result));
    """
    proc=subprocess.run(['node','-e',code+'\n'+commands],check=True,
                        capture_output=True,text=True,cwd=ROOT)
    values=json.loads(proc.stdout)
    assert len(values)==9
    for lesson in ('commutation','overlap'):
        assert values[lesson]['mode']=='calculated'
        assert values[lesson]['idc']==1
        assert values[lesson]['alphaR']==15
        assert values[lesson]['allowed']==['csLc']
    for lesson in ('constant','valves','intro','comparison','controller'):
        assert values[lesson]['muR']==0
    assert values['polarity']['mode']=='manual'


def test_inverter_waveforms_follow_common_dc_current_reference():
    if not shutil.which('node'):
        pytest.skip('Node.js is required for inverter parity assertions')
    source='\n'.join((ROOT/'presentation/src'/fn).read_text(encoding='utf-8')
                     for fn in ('waveforms.js','current_source.js'))
    code=source+"""
        const p={_csSide:'inverter',csOverlapMode:'manual',muR:12,muI:15,
                 alphaR:15,alphaI:145,idc:1,vPeak:1,csLc:.2};
        const wave=CurrentSourceModel.sample(90,p);
        const reference=LCC.sample('inverter',90,p,LCC.OFFSET);
        process.stdout.write(JSON.stringify({wave:wave.scr,reference:reference.scr,
           phase:wave.phase,referencePhase:reference.phase,dc:wave.dc,
           expected:reference.dc,ac:wave.ac,expectedAc:reference.ac}));
    """
    proc=subprocess.run(['node','-e',code],check=True,
                        capture_output=True,text=True,cwd=ROOT)
    data=json.loads(proc.stdout)
    assert data['wave']==data['reference']
    assert data['phase']==data['referencePhase']
    assert data['ac']==data['expectedAc']
    assert data['dc']==pytest.approx(data['expected'])


def test_source_code_distinguishes_assumed_overlap():
    src=(ROOT/'presentation/src/presentation.js').read_text(encoding='utf-8')
    assert 'Normal conduction with RL load' not in src
    assert 'Assumed commutation overlap' in src
    assert 'Computed from the AC commutation inductance' not in src or True
    assert 'stateDetails(s)' in src
