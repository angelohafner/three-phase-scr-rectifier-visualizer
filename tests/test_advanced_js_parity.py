"""Cross-language reference checks for the conceptual RLE and LE models."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pytest

from lcc_advanced_loads import AdvancedLoadParameters,VoltageSourceLoad

ROOT=Path(__file__).resolve().parents[1]
JS=ROOT/'presentation/src/load_models.js'

@pytest.mark.parametrize('mode',['LE','RLE'])
@pytest.mark.parametrize('source',[.2,.7])
def test_python_javascript_waveforms_match(mode,source):
    if shutil.which('node') is None:
        pytest.skip('Node.js is not installed')
    params=replace(AdvancedLoadParameters(),source_voltage_pu=source)
    w=VoltageSourceLoad(params,mode).sample(np.linspace(0,360,1441))
    runner=r'''const vm=require('vm'),fs=require('fs');
const src=fs.readFileSync(process.argv[1],'utf8');
const ctx={Math,console};vm.createContext(ctx);
vm.runInContext(src+';globalThis.model=LoadModel;',ctx);
const params=JSON.parse(process.argv[2]);
const w=ctx.model.sample(params.mode,params);
console.log(JSON.stringify({i:w.current,v:w.voltage,pair:w.pair,blocked:w.vak.T1.map(x=>Number.isFinite(x))}));'''
    spec={'mode':mode,'alphaLoad':params.alpha_deg,'loadR':params.resistance_ohm,
          'loadL':params.inductance_mH,'loadE':source,'loadI0':params.initial_current_pu,
          'vPeak':params.phase_peak_pu}
    out=subprocess.run(['node','-e',runner,str(JS),json.dumps(spec)],capture_output=True,text=True,check=True)
    j=json.loads(out.stdout)
    assert np.allclose(j['i'],w.dc_i,rtol=1e-8,atol=1e-8)
    assert np.allclose(j['v'],w.dc_v,rtol=1e-8,atol=1e-8)
    assert np.array_equal(j['pair'],w.conducting_pair)
    assert np.array_equal(j['blocked'],w.conducting_pair>=0)
