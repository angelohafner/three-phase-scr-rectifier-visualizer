/* Physical observables for the six-pulse series-capacitor commutation laboratory. */
'use strict';
const CCCSeriesSensitivity=(()=>{
 const REFERENCE_CAPS=Object.freeze([8,12,26,50,73,100]);
 const VOLTAGE_BASE_V=1000; // The normalized phase-voltage peak is referred to 1 kV.
 const CURRENT_BASE_A=1000; // The normalized current is referred to 1 kA.
 const IMPEDANCE_BASE=VOLTAGE_BASE_V/CURRENT_BASE_A;
 function terms(point,params){
   if(!point||!params)throw Error('A solved commutation trace is required');
   // Lower-group first-sector T4 -> T6 reference used throughout Chapter 04.
   const ac=-(point.source[2]-point.source[1]);
   const capacitor=point.capacitors[2]-point.capacitors[1];
   const resistive=params.R*(point.current[2]-point.current[1]);
   return {ac,capacitor,resistive,net:ac+capacitor+resistive};
 }
 function rms(values){
   return values.length?Math.sqrt(values.reduce((sum,v)=>sum+v*v,0)/values.length):NaN;
 }
 function fromSolved(result){
   if(!result?.valid||!result.traces?.length)
     return {valid:false,error:result?.error||'No valid switching solution'};
   const p=result.params,trace=result.traces;
   const cap=trace.flatMap(t=>t.capacitors);
   const phaseRms=[0,1,2].map(k=>rms(trace.map(t=>t.capacitors[k])));
   const energy=trace.map(t=>p.CmF>0?
     .5*(p.CmF/1000)*VOLTAGE_BASE_V**2*
     t.capacitors.reduce((sum,v)=>sum+v*v,0):0);
   const initial=terms(trace[0],p);
   return {valid:true,CmF:p.CmF,XL:2*Math.PI*p.f*(p.LmH/1000)/IMPEDANCE_BASE,
     XC:p.CmF>0?1/(2*Math.PI*p.f*(p.CmF/1000)*IMPEDANCE_BASE):0,
     mu:result.avgMu,P1:result.powers.P,Q1:result.powers.Q,pf1:result.powers.pf,
     voltagePeak:Math.max(...cap.map(Math.abs)),voltageRMS:rms(cap),
     perPhaseRMS:phaseRms,energyAverageJ:energy.reduce((sum,x)=>sum+x,0)/energy.length,
     energyPeakJ:Math.max(...energy),initial,
     capPeakContribution:Math.max(...trace.slice(0,Math.floor(trace.length/6))
       .map(t=>Math.abs(terms(t,p).capacitor)))};
 }
 function compare(main,reference){
   const a=fromSolved(main),b=fromSolved(reference);
   if(!a.valid||!b.valid)return {valid:false,error:a.error||b.error};
   return {valid:true,main:a,reference:b,
     dMu:a.mu-b.mu,dQ:a.Q1-b.Q1,dP:a.P1-b.P1,
     dVCPeak:a.voltagePeak-b.voltagePeak,
     dInitialCap:a.initial.capacitor-b.initial.capacitor,
     dInitialNet:a.initial.net-b.initial.net};
 }
 function sample(result,theta){
   if(!result?.valid)return {valid:false,error:result?.error||'Invalid operating point'};
   const trace=result.traces;
   const phase=Math.min(trace.length-1,Math.max(0,Math.floor(theta*trace.length/360)));
   const q=trace[phase],term=terms(q,result.params);
   const cF=result.params.CmF/1000;
   const energy=.5*cF*VOLTAGE_BASE_V**2*
     q.capacitors.reduce((sum,v)=>sum+v*v,0);
   return {valid:true,angle:q.angle,capacitors:[...q.capacitors],
     current:[...q.current],...term,energyJ:energy};
 }
 function sweep(params,capacitors=REFERENCE_CAPS){
   return capacitors.map(CmF=>{
     const result=CCCModel.solve({...params,CmF,qShunt:0});
     const observables=fromSolved(result);
     return {CmF,...observables};
   });
 }
 return {REFERENCE_CAPS,terms,fromSolved,compare,sample,sweep,VOLTAGE_BASE_V};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=CCCSeriesSensitivity;
