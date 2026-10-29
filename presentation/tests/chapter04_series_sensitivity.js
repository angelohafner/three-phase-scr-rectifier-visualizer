/* Regress physical capacitor sensitivity and default visualization domains. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const dir=path.resolve(__dirname,'../src');
for(const name of ['ccc_model','ccc_series_sensitivity'])
  vm.runInThisContext(fs.readFileSync(path.join(dir,name+'.js'),'utf8'),{filename:name});
const base={alpha:15,idc:.8,vPeak:1,LmH:.24,R:.012,f:60,qShunt:0};
const tolerance=(x,y,tol)=>assert(Math.abs(x-y)<=tol,
  'Expected '+x+' and '+y+' to agree within '+tol);
const scenarios=[
 {name:'nominal',...base},
 {name:'higher firing angle',...base,alpha:60,LmH:.32,idc:.75,vPeak:.85},
 {name:'higher DC current',...base,alpha:30,LmH:.32,idc:1}
];
let cases=0;
for(const scenario of scenarios){
 const {name,...parameters}=scenario;
 const rows=CCCSeriesSensitivity.sweep(parameters,[8,12,26,50,73,100]);
 assert.equal(rows.length,6);
 for(let k=0;k<rows.length;k++){
   const row=rows[k],C=row.CmF;
   assert(row.valid,JSON.stringify({name,C,row}));
   const expectedXL=2*Math.PI*scenario.f*scenario.LmH/1000;
   const expectedXC=1/(2*Math.PI*scenario.f*C/1000);
   tolerance(row.XL,expectedXL,1e-12);
   tolerance(row.XC,expectedXC,1e-12);
   assert(row.voltagePeak>0&&row.voltageRMS>0&&row.energyPeakJ>row.energyAverageJ);
   assert(row.initial.net>0);
   const solved=CCCModel.solve({...parameters,CmF:C});
   const sampled=CCCSeriesSensitivity.sample(solved,0);
   tolerance(sampled.net,
     sampled.ac+sampled.capacitor+sampled.resistive,1e-12);
   tolerance(sampled.energyJ,
     .5*C/1000*1000**2*sampled.capacitors.reduce((s,v)=>s+v*v,0),1e-9);
   tolerance(row.initial.net,sampled.net,1e-10);
   if(k>0){
     assert(row.voltagePeak<rows[k-1].voltagePeak,
       'Capacitor phase-voltage peak did not decrease with C at '+name);
   }
   cases++;
 }
 assert(rows[0].mu+1<rows.at(-1).mu,
   'Smaller C must shorten the reference commutation overlap at '+name);
 assert(rows[0].initial.capacitor>rows.at(-1).initial.capacitor,
   'Stronger capacitor drive must be present at smaller C at '+name);
 const low=CCCModel.solve({...parameters,CmF:12});
 const reference=CCCModel.solve({...parameters,CmF:100});
 const difference=CCCSeriesSensitivity.compare(low,reference);
 assert(difference.valid);
 assert(difference.dMu<-1);
 assert(difference.dQ<0,'The curated matched-parameter scenario must show lower Q at C=12');
 if(name==='higher firing angle'){
   // This explains why the old 60-degree chart seemed insensitive to Q.
   assert(Math.abs(difference.dQ)<.01);
   assert(Math.abs(difference.dInitialCap)>.2);
 }
}
let numerical=CCCModel.solve({...base,CmF:26});
const cap=(theta)=>CCCSeriesSensitivity.sample(numerical,theta);
for(const angle of [1,3,6,15,25]){
 const start=cap(angle),next=cap(angle+.2);
 const h=.2*Math.PI/180;
 for(let k=0;k<3;k++){
   const empirical=(next.capacitors[k]-start.capacitors[k])/h;
   const target=numerical.params.XC*(start.current[k]+next.current[k])/2;
   tolerance(empirical,target,.035);
 }
}
const invalid=CCCModel.solve({...base,CmF:-1});
assert.equal(CCCSeriesSensitivity.fromSolved(invalid).valid,false);
assert.deepEqual(CCCSeriesSensitivity.REFERENCE_CAPS,[8,12,26,50,73,100]);
console.log('PASS: '+cases+' capacitor sensitivity cases, source/capacitor/resistor drive, capacitor energy, and first-order dynamical continuity.');
