/* Analytic educational model, ported from lcc_waveform_model.py. */
'use strict';
const LCC = (() => {
  const PAIRS = [['a','c'],['b','c'],['b','a'],['c','a'],['c','b'],['a','b']];
  const UPPER = {a:'T1',b:'T3',c:'T5'};
  const LOWER = {a:'T2',b:'T4',c:'T6'};
  const PHASES = ['a','b','c'];
  const SCRS = ['T1','T2','T3','T4','T5','T6'];
  const OFFSET = 30;
  function mod(n,m){return ((n%m)+m)%m;}
  function deg(x){return x*Math.PI/180;}
  function at(theta,mu,offset=0){
    let local=mod(theta-offset,360), sector=Math.min(5,Math.floor(local/60)), t=local-sector*60;
    let overlap=t<mu-1e-9;
    return {id:overlap?(sector===0?12:2*sector):(2*sector+1), sector, overlap,
      transfer:overlap?t/mu:1, phase:local};
  }
  function stateInfo(id){
    let sector=(id%2===0)?(id===12?0:id/2):(id-1)/2;
    const old=PAIRS[(sector+5)%6], now=PAIRS[sector];
    const overlap=id%2===0;
    const present=overlap?[old,now]:[now];
    const scrs=Array.from(new Set(present.flatMap(pair=>[UPPER[pair[0]],LOWER[pair[1]]])));
    const oldScrs=[UPPER[old[0]],LOWER[old[1]]], newScrs=[UPPER[now[0]],LOWER[now[1]]];
    const incoming=newScrs.find(s=>!oldScrs.includes(s))||null;
    const outgoing=oldScrs.find(s=>!newScrs.includes(s))||null;
    return {id,overlap,scrs,incoming:overlap?incoming:null,outgoing:overlap?outgoing:null,
      pairs:present.map(([a,b])=>a.toUpperCase()+'+/ '+b.toUpperCase()+'−')};
  }
  function windows(id,mu,offset=0){
    let sector=(id%2===0)?(id===12?0:id/2):(id-1)/2;
    let a=(sector*60+offset+(id%2===1?mu:0));
    let b=sector*60+offset+(id%2===1?60:mu);
    return splitWindow(a,b);
  }
  function splitWindow(a,b){
    if(b-a>360+1e-6)throw Error('Invalid time window');
    let ret=[],start=a,end=b;
    while(start<end-1e-8){let segEnd=Math.min(end,(Math.floor(start/360)+1)*360);
      let lo=mod(start,360),hi=lo+segEnd-start;
      if(hi-lo>1e-7)ret.push([+lo.toFixed(5),+Math.min(360,hi).toFixed(5)]);
      start=segEnd; if(segEnd>=end)break;
    }
    return ret;
  }
  function jointSchedule(muR,muI,offset=OFFSET){
    const arr=[0,360];
    for(const [off,mu] of [[0,muR],[offset,muI]])for(let k=0;k<6;k++){
      arr.push(+mod(off+60*k,360).toFixed(5));arr.push(+mod(off+60*k+mu,360).toFixed(5));
    }
    const cuts=Array.from(new Set(arr)).sort((a,b)=>a-b);
    return cuts.slice(0,-1).map((lo,i)=>{
      const hi=cuts[i+1],m=(lo+hi)/2;
      return {id:i+1,window:[[lo,hi]],r:at(m,muR).id,i:at(m,muI,offset).id,
        rOverlap:at(m,muR).overlap,iOverlap:at(m,muI,offset).overlap};
    }).filter(x=>x.window[0][1]-x.window[0][0]>1e-7);
  }
  function sample(side,theta,params,offset=0){
    const inv=side==='inverter',mu=inv?params.muI:params.muR,alpha=inv?params.alphaI:params.alphaR;
    const local=mod(theta-(inv?offset:0),360), sel=at(theta,mu,inv?offset:0);
    const sector=sel.sector, prev=(sector+5)%6,w=sel.transfer;
    const phaseAngle=deg(local+(inv?-(180-alpha):alpha));
    const v=[Math.cos(phaseAngle),Math.cos(phaseAngle-2*Math.PI/3),Math.cos(phaseAngle+2*Math.PI/3)].map(n=>n*params.vPeak);
    const voltages={a:v[0],b:v[1],c:v[2]};
    const lines=[v[0]-v[1],v[1]-v[2],v[2]-v[0]];
    const scr={T1:0,T2:0,T3:0,T4:0,T5:0,T6:0};
    for(const [k,weight] of [[prev,sel.overlap?1-w:0],[sector,sel.overlap?w:1]]){
      const [hi,lo]=PAIRS[k]; scr[UPPER[hi]]+=weight*params.idc; scr[LOWER[lo]]+=weight*params.idc;
    }
    const ac=PHASES.map(ph=>(scr[UPPER[ph]]-scr[LOWER[ph]])*(inv?-1:1));
    function lv(pair){return voltages[pair[0]]-voltages[pair[1]];}
    const vNew=lv(PAIRS[sector]),vOld=lv(PAIRS[prev]);
    return {phase:v,line:lines,scr,ac,dc:sel.overlap?(vNew+vOld)/2:vNew,dcIdeal:vNew,idc:params.idc,selected:sel};
  }
  function describe(side,id){
    let st=stateInfo(id); const direction=side==='rectifier'?'AC → DC':'DC → AC';
    if(st.overlap){return `${st.incoming} is taking over current from ${st.outgoing}. The two valves share the phase current during the illustrated overlap interval; another valve remains conducting. (${direction})`;}
    return `${st.scrs.join(' and ')} conduct the pole current. One upper and one lower SCR complete the bridge path. (${direction})`;
  }
  function jointDescription(j){
    let a=stateInfo(j.r),b=stateInfo(j.i);
    const s=[];
    s.push(a.overlap?`Rectifier: ${a.outgoing} → ${a.incoming} commutation.`:`Rectifier: ${a.scrs.join(' + ')}.`);
    s.push(b.overlap?`Inverter: ${b.outgoing} → ${b.incoming} commutation.`:`Inverter: ${b.scrs.join(' + ')}.`);
    if(a.overlap&&b.overlap)s.push('Both stations overlap simultaneously.');
    return s.join(' ');
  }
  return {PAIRS,SCRS,UPPER,LOWER,OFFSET,mod,at,windows,splitWindow,stateInfo,jointSchedule,sample,describe,jointDescription};
})();
