/* Check physical model envelopes against fixed chart domains at slider endpoints. */
'use strict';
const fs=require('fs'),vm=require('vm'),path=require('path');
const dir=path.resolve(__dirname,'../src');
for(const name of ['waveforms','load_models','fixed_axes','charts','halfwave','current_source'])
  vm.runInThisContext(fs.readFileSync(path.join(dir,name+'.js'),'utf8'),{filename:name});
const p={alphaR:15,alphaI:145,muR:12,muI:15,idc:2,vPeak:2,
 alphaLoad:0,loadR:.2,loadL:.1,loadE:0,loadI0:2,csLc:.2,csKp:28,csKi:150,csOverlapMode:'manual',
 hAlpha:0,hR:2,hL:140,hV:260,hFrequency:60};
const failures=[];let checked=0;
function observe(name,vals,kind){
 const [lo,hi]=FixedAxes.range(kind);
 for(const n of vals){if(!Number.isFinite(n))continue;checked++;
   if(n<lo-1e-8||n>hi+1e-8){if(failures.length<10)failures.push([name,kind,n,lo,hi]);}}
}
for(const side of ['rectifier','inverter','hvdc'])for(const mode of ['overview','phase','line','scr','vak','valvePair','dc']){
 const active=side==='hvdc'?{r:1,i:1}:{id:1};
 for(const g of ChartView.makeSeries(side,p,mode,active))
   for(const s of g.series)observe(side+'.'+mode+'.'+s.label,s.values,g.kind);
}
for(const mode of ['R','RL','LE','RLE'])for(const alpha of [0,55,119])for(const E of [0,1.8]){
 const x=LoadModel.sample(mode,{...p,alphaLoad:alpha,loadE:E});
 observe(mode+'.voltage',x.voltage,'dcVoltage');
 observe(mode+'.current',x.current,mode==='LE'?'leCurrent':'loadCurrent');
 for(const a of x.phase)observe(mode+'.phase',a,'phaseVoltage');
 for(const a of x.line)observe(mode+'.line',a,'lineVoltage');
 for(const a of x.ac)observe(mode+'.ac',a,mode==='LE'?'leAcCurrent':'loadAcCurrent');
 for(const a of Object.values(x.vak))observe(mode+'.vak',a,'valveVoltage');
}
for(const mode of ['R','RL'])for(const alpha of [0,75,175]){
 const x=HalfWave.get({...p,hAlpha:alpha},mode);
 for(const key of ['vs','vo','vr','vl','vak'])observe('halfwave.'+key,x.sampled.map(q=>q[key]),'halfWaveVoltage');
 observe('halfwave.current',x.sampled.map(q=>q.i),'halfWaveCurrent');
 observe('halfwave.energy',x.sampled.map(q=>q.w),'halfWaveEnergy');
}
for(const R of [.2,.3,1,3])for(const L of [.1,1,10,30])for(const V of [.2,1,2]){
 const x=CurrentSourceModel.controller({...p,loadR:R,loadL:L,vPeak:V,loadE:0});
 observe('control.current',x.current,'controllerCurrent');
 observe('control.alpha',x.alpha,'firingAngle');
}
if(failures.length)throw Error(JSON.stringify(failures));
console.log(checked+' sampled model values within global fixed chart limits');
