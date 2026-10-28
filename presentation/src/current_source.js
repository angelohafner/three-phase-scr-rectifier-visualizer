/* Constant-DC-current LCC models, commutation and a bounded RLE PI controller. */
'use strict';
const CurrentSourceModel = (() => {
  const PHASES=['a','b','c'], UPPER=LCC.UPPER, LOWER=LCC.LOWER, PAIRS=LCC.PAIRS;
  const SCRS=LCC.SCRS;
  const radians=a=>a*Math.PI/180;
  const mod=LCC.mod;
  const phase=(a,p)=>PHASES.map((_,k)=>p.vPeak*Math.cos(radians(a+p.alphaR)-k*2*Math.PI/3));
  function overlap(p){
    // The inverter uses a separately assumed overlap and an extinction-angle constraint.
    if(p._csSide==='inverter'){
      const gamma=180-p.alphaI-p.muI;
      return gamma>=10&&p.muI>=0&&p.muI<60?
        {valid:true,mu:p.muI,mode:'assumed inverter'}:
        {valid:false,mu:NaN,error:'Inverter extinction margin must be at least 10°.'};
    }
    if(p.csOverlapMode!=='calculated')return {valid:true,mu:p.muR,mode:'illustrative'};
    const a=radians(p.alphaR),omega=2*Math.PI*60,L=p.csLc/1000;
    // Explicit illustrative bases: 1 kV phase peak and 1 kA DC, Z_base = 1 ohm.
    const phasePeakVolts=1000*p.vPeak,dcAmperes=1000*p.idc;
    const rhs=Math.cos(a)-2*omega*L*dcAmperes/(Math.sqrt(3)*phasePeakVolts);
    if(rhs < -1 || rhs > 1)return {valid:false,mu:NaN,error:'Insufficient commutation voltage: no complete current transfer.'};
    const mu=(Math.acos(rhs)-a)*180/Math.PI;
    if(mu<0 || mu>=60-1e-9)return {valid:false,mu,error:'The current cannot transfer within 60° using this simplified commutation model.'};
    return {valid:true,mu,mode:'calculated'};
  }
  function sample(angle,p,precomputed=null){
    const data=precomputed||overlap(p);
    if(!data.valid)return {valid:false,error:data.error,mu:data.mu};
    if(p._csSide==='inverter'){
      // The inverter reference already carries the correct reversed valve orientation.
      const ref=LCC.sample('inverter',angle,p,LCC.OFFSET),sel=ref.selected;
      const info=LCC.stateInfo(sel.id);
      const stationary=sel.overlap?info.scrs.find(x=>x!==info.outgoing&&x!==info.incoming):null;
      return {valid:true,theta:mod(angle,360),sector:sel.sector,mu:data.mu,
        state:sel.id,overlap:sel.overlap,transfer:sel.transfer,idc:p.idc,
        scr:ref.scr,ac:ref.ac,phase:ref.phase,line:ref.line,
        dc:ref.dc, // Already signed in the common rectifier-to-inverter DC current reference.
        outgoing:info.outgoing,incoming:info.incoming,stationary};
    }
    const a=mod(angle,360),sector=Math.floor(a/60),local=a-sector*60;
    const old=(sector+5)%6,now=sector,mu=data.mu;
    const active=mu>1e-10&&local<mu-1e-10;
    let fraction=1;
    if(active){
      if(data.mode==='calculated'){
        const alpha=radians(p.alphaR),delta=radians(local);
        const numerator=Math.cos(alpha)-Math.cos(alpha+delta);
        const denom=Math.cos(alpha)-Math.cos(alpha+radians(mu));
        fraction=Math.max(0,Math.min(1,numerator/denom));
      }else fraction=local/mu;
    }
    const src=phase(a,p),vline=[src[0]-src[1],src[1]-src[2],src[2]-src[0]];
    const scr=Object.fromEntries(SCRS.map(s=>[s,0]));
    for(const [k,w] of [[old,active?1-fraction:0],[now,active?fraction:1]]){
      const [hi,lo]=PAIRS[k];scr[UPPER[hi]]+=p.idc*w;scr[LOWER[lo]]+=p.idc*w;
    }
    const ac=PHASES.map((ph)=>scr[UPPER[ph]]-scr[LOWER[ph]]);
    const [oldHi,oldLo]=PAIRS[old],[newHi,newLo]=PAIRS[now];
    const vOld=src[PHASES.indexOf(oldHi)]-src[PHASES.indexOf(oldLo)];
    const vNew=src[PHASES.indexOf(newHi)]-src[PHASES.indexOf(newLo)];
    const oldSCR=[UPPER[oldHi],LOWER[oldLo]],newSCR=[UPPER[newHi],LOWER[newLo]];
    return {valid:true,theta:a,sector,mu,state:active?(sector===0?12:2*sector):2*sector+1,
      overlap:active,transfer:fraction,idc:p.idc,scr,ac,phase:src,line:vline,
      dc:active?(vOld+vNew)/2:vNew,
      outgoing:active?oldSCR.find(t=>!newSCR.includes(t)):null,
      incoming:active?newSCR.find(t=>!oldSCR.includes(t)):null,
      stationary:active?newSCR.find(t=>oldSCR.includes(t)):null};
  }
  const cache=new Map();
  function cycle(p){
    const key=JSON.stringify([p._csSide||'rectifier',p.csOverlapMode,p.alphaR,p.alphaI,p.muR,p.muI,p.idc,p.vPeak,p.csLc]);
    if(cache.has(key))return cache.get(key);
    const info=overlap(p);
    if(!info.valid)return {valid:false,error:info.error,mu:info.mu};
    const angle=Array.from({length:721},(_,k)=>k*.5);
    const data=angle.map(a=>sample(a,p,info));
    const value={valid:true,angle,data,mu:info.mu,mode:info.mode};
    cache.set(key,value);if(cache.size>12)cache.delete(cache.keys().next().value);
    return value;
  }
  function windows(p,theta,mu){
    const offset=p._csSide==='inverter'?LCC.OFFSET:0;
    const rel=mod(theta-offset,360),sector=Math.floor(rel/60),t=rel-sector*60;
    const base=offset+sector*60;
    const lo=t<mu?base:base+mu,hi=t<mu?base+mu:base+60;
    return LCC.splitWindow(lo,hi);
  }
  function window(p,theta,mu){return windows(p,theta,mu)[0];}
  function controller(p){
    const key='ctl'+JSON.stringify([p.idc,p.loadR,p.loadL,p.loadE,p.vPeak,p.csKp,p.csKi]);
    if(cache.has(key))return cache.get(key);
    const R=p.loadR,L=Math.max(0.0001,p.loadL/1000),E=p.loadE;
    const V0=3*Math.sqrt(3)/Math.PI*p.vPeak;
    const dt=.0005,maxTime=.35;
    const result={time:[],ref:[],current:[],alpha:[]};
    let i=Math.max(0,p.idc*.55),integral=0;
    for(let t=0;t<=maxTime+1e-9;t+=dt){
      const target=t<.08?p.idc*.55:p.idc;
      const alphaFF=Math.acos(Math.max(-1,Math.min(1,(E+R*target)/V0)))*180/Math.PI;
      const error=target-i;
      const trialIntegral=integral+error*dt;
      let alpha=alphaFF-p.csKp*error-p.csKi*trialIntegral;
      alpha=Math.max(5,Math.min(85,alpha));
      if(alpha>5.0001&&alpha<84.9999)integral=trialIntegral;
      const vdc=V0*Math.cos(radians(alpha));
      const di=(vdc-R*i-E)/L;
      i=Math.max(0,i+dt*di);
      result.time.push(t);result.ref.push(target);result.current.push(i);result.alpha.push(alpha);
    }
    cache.set(key,result);if(cache.size>12)cache.delete(cache.keys().next().value);
    return result;
  }
  function inverterPower(p){
    const inp={...p,idc:p.idc};
    let r=0,i=0;
    for(let angle=0;angle<360;angle++){
      r+=LCC.sample('rectifier',angle,inp).dc;
      i+=LCC.sample('inverter',angle,inp,LCC.OFFSET).dc; // Negative for inverter absorption from the DC link.
    }
    return {rectifier:r/360*p.idc,inverter:i/360*p.idc};
  }
  return {sample,overlap,cycle,window,windows,controller,inverterPower,PAIRS,SCRS,PHASES};
})();
