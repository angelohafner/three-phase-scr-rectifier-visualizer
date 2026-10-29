/* Equal AC fundamental active-power comparison and infeasible-point regressions. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('fs'),vm=require('vm'),path=require('path');
const directory=path.resolve(__dirname,'../src');
for(const name of ['ccc_model','ccc_power_match'])
  vm.runInThisContext(fs.readFileSync(path.join(directory,name+'.js'),'utf8'),{filename:name});
const p={alpha:15,idc:.8,vPeak:1,LmH:.24,CmF:26,R:.012,f:60,qShunt:0};
const lcc=CCCModel.solve({...p,CmF:0});
const same=CCCModel.solve(p);
const matched=CCCPowerMatch.match(lcc,p);
assert(matched.valid,JSON.stringify(matched));
const measured=CCCPowerMatch.summarize(lcc,matched.ccc);
assert(Math.abs(matched.errorP)<2e-5,'Active power must match the target');
assert.equal(matched.ccc.params.idc,lcc.params.idc);
assert(Math.abs(measured.P_LCC-measured.P_CCC)<2e-5);
assert(measured.Q_CCC>measured.Q_LCC,'Nominal equal-P case should reveal a slightly higher CCC Q');
assert(same.powers.Q<lcc.powers.Q,'Same-alpha case should reveal lower CCC Q');
assert(measured.alpha_CCC>measured.alpha_LCC);
assert(Math.abs(measured.QoverP_CCC-measured.Q_CCC/measured.P_CCC)<1e-12);
assert(Math.abs(measured.PF1_CCC-matched.ccc.powers.pf)<1e-12);
let checked=0;
for(const alpha of [0,5,15,30,45,60])
  for(const capacitance of [12,26,73,100]){
    const settings={...p,alpha,CmF:capacitance};
    const reference=CCCModel.solve({...settings,CmF:0});
    const match=CCCPowerMatch.match(reference,settings);
    assert(match.valid,JSON.stringify({alpha,capacitance,match}));
    assert(Math.abs(match.errorP)<2e-5);
    assert.equal(match.ccc.params.idc,reference.params.idc);
    assert(match.alphaCCC>=0 && match.alphaCCC<=90);
    checked++;
  }
assert.equal(CCCPowerMatch.match(null,p).valid,false);
assert.equal(CCCPowerMatch.match(lcc,{...p,CmF:0}).valid,false);
const notFeasible=CCCPowerMatch.match({valid:true,params:{alpha:15,idc:.8},
  powers:{P:3}},p);
assert.equal(notFeasible.valid,false);
assert(!notFeasible.ccc,'Do not invent a CCC waveform for an infeasible target');
console.log('PASS: '+checked+' matched-power parameter cases, fair P/Q comparisons and infeasible operating points.');
