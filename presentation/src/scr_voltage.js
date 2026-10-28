/* SCR anode-to-cathode voltage reconstructed from defined bridge-node potentials. */
'use strict';
const SCRVoltage = (() => {
  const NAMES=['T1','T2','T3','T4','T5','T6'];
  const UPPER={a:'T1',b:'T3',c:'T5'}, LOWER={a:'T2',b:'T4',c:'T6'};
  const FLOATING=Object.freeze(Object.fromEntries(NAMES.map(k=>[k,Number.NaN])));
  function evaluate(side,theta,params,offset=0){
    if(side!=='rectifier'&&side!=='inverter')throw Error('Unknown LCC station');
    const p=LCC.sample(side,theta,params,offset),st=p.selected;
    if(st.overlap)return {values:{...FLOATING},note:'Individual valve voltage unavailable during idealized commutation overlap',defined:false};
    const volts={a:p.phase[0],b:p.phase[1],c:p.phase[2]};
    const [plusPhase,minusPhase]=LCC.PAIRS[st.sector];
    const plus=volts[plusPhase],minus=volts[minusPhase],isInverter=side==='inverter';
    const values={};
    for(const phase of ['a','b','c']){
      values[UPPER[phase]]=isInverter?plus-volts[phase]:volts[phase]-plus;
      values[LOWER[phase]]=isInverter?volts[phase]-minus:minus-volts[phase];
    }
    return {values,defined:true,plus,minus,phase:volts,selected:st,
      note:'Ideal zero-overlap valve blocking voltages, derived from conducting bridge nodes'};
  }
  function series(side,params,offset=0){
    const series=Object.fromEntries(NAMES.map(n=>[n,[]]));
    for(let angle=0;angle<=360;angle++){
      const point=evaluate(side,angle,params,offset);
      for(const n of NAMES)series[n].push(point.values[n]);
    }
    return series;
  }
  return {evaluate,series,NAMES};
})();
