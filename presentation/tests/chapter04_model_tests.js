/* Physics regression for the six-pulse capacitor-commutated teaching model. */
'use strict';
const assert=require('node:assert/strict');
const CCC=require('../src/ccc_model.js');
const close=(a,b,tol=.005)=>assert.ok(Math.abs(a-b)<=tol,`${a} vs ${b}, tolerance ${tol}`);
const nominal=CCC.solve({alpha:15,idc:.8,LmH:.24,CmF:26});
const plain=CCC.solve({alpha:15,idc:.8,LmH:.24,CmF:0});
assert.ok(nominal.valid&&plain.valid,'Both six-pulse models must find periodic operation');
assert.equal(nominal.mu.length,6);
assert.equal(nominal.traces.length,1800);
assert.ok(nominal.mu.every(mu=>mu>0&&mu<60));
assert.ok(nominal.powers.Q>0&&plain.powers.Q>0);
assert.ok(Math.abs(nominal.avgMu-plain.avgMu)>.4,'Series C must change the solved overlap');
assert.ok(Math.abs(nominal.powers.imbalance)<.005,'AC power, DC bridge power and losses must balance');
assert.ok(nominal.residual<.0002,'Capacitor solution must be periodic');
const currents=nominal.traces.map(x=>x.current);
for(const i of currents){close(i[0]+i[1]+i[2],0,1e-9);assert.ok(i.every(a=>Math.abs(a)<=.80001));}
const peak=nominal.traces.reduce((v,q)=>Math.max(v,...q.capacitors.map(Math.abs)),0);
assert.ok(peak>.02,'Series capacitor voltage must evolve rather than remain zero');
for(let j=0;j<nominal.traces.length-1;j++){
 const a=nominal.traces[j].capacitors,b=nominal.traces[j+1].capacitors;
 assert.ok(a.every((v,k)=>Math.abs(v-b[k])<.02),'Capacitor voltage must be continuous');
}
const lowerC=CCC.solve({CmF:12}),higherC=CCC.solve({CmF:80});
assert.ok(lowerC.valid&&higherC.valid);
assert.ok(Math.abs(lowerC.avgMu-higherC.avgMu)>1);
const lowerL=CCC.solve({LmH:.12}),higherL=CCC.solve({LmH:.38});
assert.ok(lowerL.valid&&higherL.valid);
assert.ok(higherL.avgMu>lowerL.avgMu,'Larger commutation reactor should increase overlap in nominal comparison');
const shunt=CCC.solve({qShunt:.55}),noShunt=CCC.solve({qShunt:0});
close(shunt.powers.Qgrid,noShunt.powers.Qgrid-.55*shunt.params.vPeak**2,1e-9);
close(shunt.powers.Q,noShunt.powers.Q,1e-9);
const refined=CCC.solve({samplesPerCycle:3600});
close(refined.avgMu,CCC.solve({samplesPerCycle:1800}).avgMu,.15);
close(refined.powers.Q,nominal.powers.Q,.005);
for(const input of [{CmF:-1},{LmH:0},{alpha:110},{idc:0}]){
 assert.equal(CCC.solve(input).valid,false,'Invalid input must not produce fabricated waveforms');
}
let count=0;
for(const alpha of [0,15,40,60])for(const idc of [.3,.8,1.2])for(const LmH of [.12,.24,.38])for(const CmF of [0,12,26,100]){
 const result=CCC.solve({alpha,idc,LmH,CmF});
 assert.ok(result.valid,JSON.stringify({alpha,idc,LmH,CmF,error:result.error}));
 assert.ok(Math.abs(result.powers.imbalance)<.01,'Steady state energy balance failed');
 count++;
}
console.log(`CCC/LCC six-pulse numerical checks passed (${count} parameter scenarios).`);