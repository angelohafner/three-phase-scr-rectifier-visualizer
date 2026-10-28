/* Ideal six-pulse R and continuous/discontinuous RL teaching models. */
'use strict';
const LoadModel=(()=>{
  const PAIRS=[[0,2],[1,2],[1,0],[2,0],[2,1],[0,1]];
  const SCRS=[['T1','T6'],['T3','T6'],['T3','T2'],['T5','T2'],['T5','T4'],['T1','T4']];
  const names=['T1','T2','T3','T4','T5','T6'];
  const resolution=.25,N=1440;
  const mod=(a,n)=>((a%n)+n)%n;
  const deg=x=>x*Math.PI/180;
  function phase(theta,v){let z=deg(theta);return [v*Math.cos(z),v*Math.cos(z-2*Math.PI/3),v*Math.cos(z+2*Math.PI/3)];}
  function fired(theta,alpha){const number=Math.floor((theta-alpha+1e-9)/60);return {pair:mod(number,6),elapsed:theta-(number*60+alpha),sector:number};}
  function voltage(theta,pair,v){let phases=phase(theta,v),[upper,lower]=PAIRS[pair];return phases[upper]-phases[lower];}
  function config(params){return {alpha:params.alphaLoad??75,R:params.loadR??1,L:params.loadL??8,E:params.loadE??.85,i0:params.loadI0??.3,v:params.vPeak??1,frequency:60};}
  function sample(mode,params){
    const p=config(params);
    if(!['R','RL','LE','RLE'].includes(mode)||p.R<=0||p.L<0||p.E<0||p.i0<0||p.alpha<0||p.alpha>=120)throw Error('Invalid load settings');
    if(mode==='LE'||mode==='RLE')return sampleVoltageLoad(mode,p);
    const series={theta:[],phase:[[],[],[]],line:[[],[],[]],voltage:[],current:[],pair:[],ac:[[],[],[]],scr:Object.fromEntries(names.map(x=>[x,[]]))};
    const theta=Array.from({length:N+1},(_,k)=>k*resolution);
    let current=0,pair=-1,oldSector=null;
    const storeI=new Array(N+1).fill(0),storePair=new Array(N+1).fill(-1),storeVoltage=new Array(N+1).fill(0);
    if(mode==='RL'&&p.L>0){
      const tau=360*p.frequency*(p.L/1000)/p.R;
      const factor=Math.exp(-resolution/tau);
      for(let cycle=0;cycle<7;cycle++){
        for(let j=0;j<N;j++){
          const ang=theta[j],fire=fired(ang,p.alpha);
          if(oldSector!==fire.sector){
            if(current>1e-10||voltage(ang,fire.pair,p.v)>0)pair=fire.pair;
            else pair=-1;
            oldSector=fire.sector;
          }
          let output=0;
          if(pair>=0){
            const u=voltage(ang+resolution/2,pair,p.v);
            current=current*factor+u/p.R*(1-factor);
            if(current<=1e-10){current=0;pair=-1;}else output=u;
          }else current=0;
          if(cycle===6){storeI[j]=current;storePair[j]=pair;storeVoltage[j]=output;}
        }
      }
      storeI[N]=storeI[0];storePair[N]=storePair[0];storeVoltage[N]=storeVoltage[0];
    }else{
      const duration=Math.min(60,120-p.alpha);
      for(let j=0;j<=N;j++){
        const fire=fired(theta[j],p.alpha),u=voltage(theta[j],fire.pair,p.v);
        const conducting=fire.elapsed>=-1e-8&&fire.elapsed<duration-1e-8&&u>0;
        storePair[j]=conducting?fire.pair:-1;
        storeVoltage[j]=conducting?u:0;
        storeI[j]=storeVoltage[j]/p.R;
      }
    }
    for(let j=0;j<=N;j++){
      const a=theta[j],ph=phase(a,p.v),pr=storePair[j],val=storeI[j];
      series.theta.push(a);series.current.push(val);series.voltage.push(storeVoltage[j]);series.pair.push(pr);
      for(let k=0;k<3;k++){series.phase[k].push(ph[k]);series.line[k].push(ph[k]-ph[(k+1)%3]);}
      for(const n of names)series.scr[n].push(pr>=0&&SCRS[pr].includes(n)?val:0);
      for(let k=0;k<3;k++)series.ac[k].push(series.scr[['T1','T3','T5'][k]][j]-series.scr[['T2','T4','T6'][k]][j]);
    }
    series.kind=mode;series.config=p;series.vak=valveVoltages(series.phase,series.pair);
    return series;
  }
  function valveVoltages(phases,pairs,operation='rectifier'){
    const polarity=operation==='inverter'?-1:1;
    const result=Object.fromEntries(names.map(name=>[name,[]]));
    for(let j=0;j<pairs.length;j++){
      const pair=pairs[j];
      if(pair<0){for(const n of names)result[n].push(NaN);continue;}
      const [up,low]=PAIRS[pair];
      const vp=phases[up][j],vn=phases[low][j];
      for(let k=0;k<3;k++){
        result[['T1','T3','T5'][k]].push(polarity*(phases[k][j]-vp));
        result[['T2','T4','T6'][k]].push(polarity*(vn-phases[k][j]));
      }
    }
    return result;
  }
  function sampleVoltageLoad(mode,p){
    if(p.L<=0)throw Error('LE and RLE require positive inductance');
    const theta=Array.from({length:N+1},(_,j)=>j*resolution);
    const storeI=new Array(N+1).fill(0),storePair=new Array(N+1).fill(-1),storeVoltage=new Array(N+1).fill(p.E);
    const dt=resolution/(360*p.frequency),R=mode==='RLE'?p.R:0,L=p.L/1000;
    const damp=R>0?Math.exp(-R*dt/L):1;
    let current=p.i0,pair=-1;
    for(let cycle=0;cycle<(mode==='RLE'?7:1);cycle++){
      let previousSector=null;
      for(let j=0;j<N;j++){
        const angle=theta[j],f=fired(angle+1e-9,p.alpha);
        if(f.sector!==previousSector){
          const prospective=voltage(angle+1e-9,f.pair,p.v);
          pair=current>1e-10||prospective>p.E?f.pair:-1;
          previousSector=f.sector;
        }
        if(pair>=0){
          const drive=voltage(angle+resolution/2,pair,p.v)-p.E;
          const next=R>0?(current*damp+(drive/R)*(1-damp)):(current+drive*dt/L);
          if(next<=1e-10){current=0;pair=-1;}else current=next;
        }else current=0;
        if(cycle===(mode==='RLE'?6:0)){
          storeI[j]=current;storePair[j]=pair;
          storeVoltage[j]=pair<0?p.E:voltage(angle,pair,p.v);
        }
      }
    }
    storeI[N]=mode==='LE'?storeI[N-1]:storeI[0];
    storePair[N]=mode==='LE'?storePair[N-1]:storePair[0];
    storeVoltage[N]=mode==='LE'?storeVoltage[N-1]:storeVoltage[0];
    const result={theta,phase:[[],[],[]],line:[[],[],[]],voltage:storeVoltage,current:storeI,pair:storePair,ac:[[],[],[]],scr:Object.fromEntries(names.map(x=>[x,[]])),kind:mode,config:p};
    for(let j=0;j<=N;j++){
      const ph=phase(theta[j],p.v),pr=storePair[j],value=storeI[j];
      for(let k=0;k<3;k++){result.phase[k].push(ph[k]);result.line[k].push(ph[k]-ph[(k+1)%3]);}
      for(const name of names)result.scr[name].push(pr>=0&&SCRS[pr].includes(name)?value:0);
      for(let k=0;k<3;k++)result.ac[k].push(result.scr[['T1','T3','T5'][k]][j]-result.scr[['T2','T4','T6'][k]][j]);
    }
    result.vak=valveVoltages(result.phase,result.pair);
    result.steadyState=mode==='LE'?'not-assumed':'damped-periodic';
    return result;
  }
  function activeWindow(series,theta){
    const idx=Math.min(N-1,Math.max(0,Math.round(mod(theta,360)/resolution)));
    const pair=series.pair[idx],start=idx;
    let lo=start,hi=start;
    while(lo>0&&series.pair[lo-1]===pair)lo--;
    while(hi<N-1&&series.pair[hi+1]===pair)hi++;
    let windows=[[lo*resolution,Math.min(360,(hi+1)*resolution)]];
    if(lo===0&&series.pair[N-1]===pair){
      let k=N-1;while(k>0&&series.pair[k-1]===pair)k--;
      if(k!==0)windows.push([k*resolution,360]);
    }
    return {pair,windows,blocked:pair<0};
  }
  function at(series,theta){const idx=Math.max(0,Math.min(N,Math.round(mod(theta,360)/resolution)));const pair=series.pair[idx];return {pair,theta:series.theta[idx],dcVoltage:series.voltage[idx],dcCurrent:series.current[idx],scrs:pair<0?[]:SCRS[pair]};}
  return {sample,at,fired,config,SCRS,PAIRS,phase,voltage,valveVoltages,activeWindow};
})();
