/* Independent, ideal six-pulse R/RL/LE/RLE load and SCR terminal-voltage model. */
'use strict';
const LoadModel = (() => {
  const PAIRS = [[0,2],[1,2],[1,0],[2,0],[2,1],[0,1]];
  const SCRS = [['T1','T6'],['T3','T6'],['T3','T2'],['T5','T2'],['T5','T4'],['T1','T4']];
  const UPPER = ['T1','T3','T5'], LOWER = ['T2','T4','T6'];
  const NAMES = ['T1','T2','T3','T4','T5','T6'];
  const ANGULAR_STEP = 0.25, N = Math.round(360 / ANGULAR_STEP);
  const mod = (a,n) => ((a % n) + n) % n;
  const degrees = a => a * Math.PI / 180;
  function phase(angle, v) {
    const x = degrees(angle);
    return [v*Math.cos(x), v*Math.cos(x-2*Math.PI/3), v*Math.cos(x+2*Math.PI/3)];
  }
  function fired(angle, alpha) {
    const sector = Math.floor((angle-alpha+1e-10)/60);
    return {pair:mod(sector,6), sector, elapsed:angle-(sector*60+alpha)};
  }
  function voltage(angle, pair, peak) {
    const ph = phase(angle,peak), [up,lo] = PAIRS[pair];
    return ph[up]-ph[lo];
  }
  function config(params) {
    return {alpha:params.alphaLoad??75, R:params.loadR??1, L:params.loadL??8,
      E:params.loadE??0, v:params.vPeak??1, frequency:params.loadFrequency??60};
  }
  function validate(mode,p) {
    if (!['R','RL','LE','RLE'].includes(mode)) throw Error('Unknown DC load');
    if (![p.alpha,p.R,p.L,p.E,p.v,p.frequency].every(Number.isFinite)) throw Error('Nonfinite load parameter');
    if (p.alpha<0||p.alpha>=170||p.v<=0||p.frequency<=0||p.R<0||p.L<0) throw Error('Invalid load settings');
    if (['R','RL','RLE'].includes(mode) && p.R<=0) throw Error('Selected load requires R>0');
    if (['LE','RLE'].includes(mode) && p.L<=0) throw Error('Selected load requires L>0');
  }
  function electrical(mode,p) {
    return {R:mode==='LE'?0:p.R, L:(mode==='R'?0:p.L), E:['R','RL'].includes(mode)?0:p.E};
  }
  function terminalVoltages(ph,pair) {
    const result = Object.fromEntries(NAMES.map(t=>[t,Number.NaN]));
    if (pair<0) return result;
    const [up,lo]=PAIRS[pair], plus=ph[up], minus=ph[lo];
    for(let k=0;k<3;k++) {
      result[UPPER[k]]=ph[k]-plus;
      result[LOWER[k]]=minus-ph[k];
    }
    return result;
  }
  function integrate(current, driving, r, L, dt) {
    if (L<=0) return Math.max(0, driving/r);
    if (r===0) return current+driving*dt/L;
    return current * Math.exp(-r*dt/L) + (driving/r)*(-Math.expm1(-r*dt/L));
  }
  function sample(mode,params) {
    const p=config(params);validate(mode,p);
    const eq=electrical(mode,p),dt=ANGULAR_STEP/(360*p.frequency), lh=eq.L/1000;
    const data={theta:[],phase:[[],[],[]],line:[[],[],[]],voltage:[],current:[],pair:[],
      ac:[[],[],[]],scr:Object.fromEntries(NAMES.map(n=>[n,[]])),
      scrVoltage:Object.fromEntries(NAMES.map(n=>[n,[]])),
      scrState:Object.fromEntries(NAMES.map(n=>[n,[]])),windows:[],kind:mode,config:p};
    // Repeated warm-up cycles remove the transient only when a periodic solution exists.
    let current=0,pair=-1,previousSector=null, previousEnd=0, steady=false;
    const warmup=eq.R===0?24:Math.min(120,Math.max(16,Math.ceil((eq.L/1000)/eq.R*p.frequency*14)));
    let final=[];
    for(let cycle=0;cycle<=warmup;cycle++) {
      const before=current;
      if(cycle===warmup) final=[];
      for(let j=0;j<N;j++) {
        const angle=j*ANGULAR_STEP, midpoint=angle+ANGULAR_STEP/2;
        const fire=fired(midpoint,p.alpha);
        if(fire.sector!==previousSector){
          // The next pair is requested at the firing boundary. The old pair
          // commutates only when there is positive current or forward drive.
          previousSector=fire.sector;
          pair=-1;
        }
        const u=voltage(midpoint,fire.pair,p.v), drive=u-eq.E;
        if(current>1e-11 || drive>1e-11) {
          pair=fire.pair;
          if(lh>0) current=integrate(current,drive,eq.R,lh,dt);
          else current=Math.max(0,drive/eq.R);
          if(current<=1e-11){current=0;pair=-1;}
        } else {current=0;pair=-1;}
        if(cycle===warmup) final.push({current,pair,voltage:pair>=0?u:eq.E});
      }
      if(cycle===warmup-1)previousEnd=current;
      if(cycle===warmup) steady=Math.abs(current-previousEnd)<1e-5*Math.max(1,Math.abs(current));
    }
    // Zero resistance and continuous current have no asymptotically unique
    // periodic attractor. Show the trace, but flag it as initialization-dependent.
    data.periodic=steady && eq.R>0;
    data.periodicityMessage=eq.R===0?'LE: no unique attracting steady state without damping; initial conditions matter.':
      (steady?'Periodic current verified after warm-up.':'No periodic solution reached with this configuration.');
    data.stable=eq.R>0&&steady;
    for(let j=0;j<=N;j++) {
      const a=j*ANGULAR_STEP, k=j%N, ph=phase(a,p.v), s=final[k], pr=s.pair;
      data.theta.push(a);data.current.push(s.current);data.pair.push(pr);
      data.voltage.push(pr>=0?ph[PAIRS[pr][0]]-ph[PAIRS[pr][1]]:eq.E);
      for(let m=0;m<3;m++){data.phase[m].push(ph[m]);data.line[m].push(ph[m]-ph[(m+1)%3]);}
      for(const n of NAMES){
        const conducting=pr>=0&&SCRS[pr].includes(n);
        data.scr[n].push(conducting?s.current:0);
      }
      const vk=terminalVoltages(ph,pr);
      for(const n of NAMES){
        const val=vk[n];data.scrVoltage[n].push(val);
        data.scrState[n].push(pr<0?'floating':(SCRS[pr].includes(n)?'conducting':val>1e-9?'forward':val< -1e-9?'reverse':'zero'));
      }
      for(let m=0;m<3;m++)data.ac[m].push(data.scr[UPPER[m]][j]-data.scr[LOWER[m]][j]);
    }
    let start=-1;
    for(let j=0;j<=N;j++){
      const conducting=j<N&&data.pair[j]>=0;
      if(conducting&&start<0)start=data.theta[j];
      if(!conducting&&start>=0){data.windows.push([start,data.theta[j]]);start=-1;}
    }
    return data;
  }
  function at(series, angle) {
    const idx=Math.min(N-1,Math.floor(mod(angle,360)/ANGULAR_STEP));
    const pair=series.pair[idx],scrs=pair<0?[]:SCRS[pair];
    return {pair,theta:mod(angle,360),dcVoltage:series.voltage[idx],dcCurrent:series.current[idx],
      scrs,scrVoltage:Object.fromEntries(NAMES.map(n=>[n,series.scrVoltage[n][idx]])),
      scrState:Object.fromEntries(NAMES.map(n=>[n,series.scrState[n][idx]])),periodic:series.periodic};
  }
  return {sample,at,config,fired,voltage,phase,terminalVoltages,PAIRS,SCRS,NAMES};
})();
