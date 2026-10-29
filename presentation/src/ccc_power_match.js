/* Compare LCC and CCC at identical fundamental AC active power. */
'use strict';
const CCCPowerMatch=(()=>{
 const DEFAULT_TOLERANCE=5e-7, LIMITS=[0,90];
 const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
 const ratio=(q,p)=>Math.abs(p)>1e-7?q/p:NaN;
 function match(reference,parameters,opts={}){
   if(!reference?.valid||!Number.isFinite(reference?.powers?.P))
     return {valid:false,error:'Valid LCC reference power is required.'};
   if(!(parameters?.CmF>0))
     return {valid:false,error:'A positive series capacitance is required for CCC.'};
   const targetP=reference.powers.P;
   const tol=opts.tolerance??DEFAULT_TOLERANCE;
   if(!(tol>0&&tol<.01))throw Error('Invalid power-match tolerance');
   const origin=clamp(Number(reference.params.alpha),...LIMITS);
   let evaluations=0;
   const memo=new Map();
   function evaluate(alpha){
     const x=clamp(alpha,...LIMITS),key=x.toFixed(10);
     if(memo.has(key))return memo.get(key);
     const result=CCCModel.solve({...parameters,alpha:x,qShunt:0});
     evaluations++;
     const value=result.valid?{valid:true,alpha:x,diff:result.powers.P-targetP,
       result}:{valid:false,alpha:x,diff:NaN,error:result.error};
     memo.set(key,value);return value;
   }
   function finalize(point){
     return {valid:true,method:'match-P1-by-CCC-firing-angle',targetP,
       actualP:point.result.powers.P,errorP:point.diff,
       alphaLCC:reference.params.alpha,alphaCCC:point.alpha,
       currentLCC:reference.params.idc,currentCCC:point.result.params.idc,
       ccc:point.result,evaluations};
   }
   const first=evaluate(origin);
   if(first.valid&&Math.abs(first.diff)<=tol)return finalize(first);
   let bracket=null;
   // Find the nearest feasible root around the LCC firing angle.
   for(const radius of [1,2,4,8,16,32,64,90]){
     const a=evaluate(origin-radius),b=evaluate(origin+radius);
     if(a.valid&&Math.abs(a.diff)<=tol)return finalize(a);
     if(b.valid&&Math.abs(b.diff)<=tol)return finalize(b);
     const sorted=[...memo.values()].filter(v=>v.valid).sort((a,b)=>a.alpha-b.alpha);
     const pairs=[];
     for(let k=1;k<sorted.length;k++){
       const p=sorted[k-1],q=sorted[k];
       if(p.diff*q.diff<0)pairs.push([p,q]);
     }
     if(pairs.length){
       pairs.sort((x,y)=>
         Math.abs((x[0].alpha+x[1].alpha)/2-origin)-
         Math.abs((y[0].alpha+y[1].alpha)/2-origin));
       bracket=pairs[0];break;
     }
   }
   if(!bracket){
     const finite=[...memo.values()].filter(v=>v.valid);
     return {valid:false,method:'match-P1-by-CCC-firing-angle',
       error:'The target active power cannot be reached with valid CCC firing angles from 0° to 90°. Choose another operating point.',
       targetP,alphaLCC:reference.params.alpha,
       exploredP:finite.length?[Math.min(...finite.map(v=>v.result.powers.P)),
         Math.max(...finite.map(v=>v.result.powers.P))]:null,evaluations};
   }
   let [lo,hi]=bracket;
   let best=Math.abs(lo.diff)<=Math.abs(hi.diff)?lo:hi;
   for(let k=0;k<22;k++){
     if(Math.abs(best.diff)<=tol)return finalize(best);
     const span=hi.alpha-lo.alpha;
     const sec=lo.alpha-lo.diff*(hi.alpha-lo.alpha)/(hi.diff-lo.diff);
     let candidate=sec;
     if(!Number.isFinite(candidate)||candidate<=lo.alpha+.15*span||
         candidate>=hi.alpha-.15*span)candidate=(lo.alpha+hi.alpha)/2;
     const mid=evaluate(candidate);
     if(!mid.valid)
       return {valid:false,targetP,alphaLCC:reference.params.alpha,
         error:'CCC switching became invalid inside the matched-power bracket.',evaluations};
     if(Math.abs(mid.diff)<Math.abs(best.diff))best=mid;
     if(mid.diff*lo.diff>0)lo=mid;else hi=mid;
     if(hi.alpha-lo.alpha<1e-7)break;
   }
   if(Math.abs(best.diff)<=tol)return finalize(best);
   return {valid:false,targetP,alphaLCC:reference.params.alpha,
     error:'CCC power matching did not meet numerical tolerance.',
     residual:best.diff,evaluations};
 }
 function summarize(lcc,ccc){
   const l=lcc.powers,c=ccc.powers;
   return {P_LCC:l.P,P_CCC:c.P,deltaP:c.P-l.P,
     Q_LCC:l.Q,Q_CCC:c.Q,deltaQ:c.Q-l.Q,
     QoverP_LCC:ratio(l.Q,l.P),QoverP_CCC:ratio(c.Q,c.P),
     PF1_LCC:l.pf,PF1_CCC:c.pf,
     mu_LCC:lcc.avgMu,mu_CCC:ccc.avgMu,
     alpha_LCC:lcc.params.alpha,alpha_CCC:ccc.params.alpha,
     idc_LCC:lcc.params.idc,idc_CCC:ccc.params.idc};
 }
 return {match,summarize,ratio,LIMITS,DEFAULT_TOLERANCE};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=CCCPowerMatch;
