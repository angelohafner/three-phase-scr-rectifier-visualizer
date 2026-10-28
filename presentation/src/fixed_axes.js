/* Fixed chart domains derived from the full allowed slider ranges, not live traces. */
'use strict';
const FixedAxes = (() => {
  // Keep these extrema aligned with the settings and lesson-specific sliders.
  const controls=Object.freeze({
    phasePeakMax:2, dcCurrentMax:2, dcResistanceMin:.2,
    dcInductanceMinMilliHenry:.1, initialCurrentMax:2, frequencyHz:60,
    halfWaveVoltageMax:260, halfWaveResistanceMin:2,
    halfWaveInductanceMaxMilliHenry:140, controllerStepSeconds:.0005
  });
  const linePeak=Math.sqrt(3)*controls.phasePeakMax;
  const loadCurrentPeak=linePeak/controls.dcResistanceMin;
  // R=0 in LE: a conservative full-cycle integral bounds its initial-value trajectory.
  const leCurrentPeak=controls.initialCurrentMax+linePeak/
    (controls.frequencyHz*controls.dcInductanceMinMilliHenry/1000);
  const halfWaveCurrentPeak=controls.halfWaveVoltageMax/controls.halfWaveResistanceMin;
  const halfWaveEnergyPeak=.5*(controls.halfWaveInductanceMaxMilliHenry/1000)*
    halfWaveCurrentPeak**2;
  // The bounded controller voltage and explicit Euler step both limit positive current.
  const controllerVoltagePeak=3*Math.sqrt(3)/Math.PI*controls.phasePeakMax;
  const controllerCurrentPeak=Math.max(controllerVoltagePeak/controls.dcResistanceMin,
    controllerVoltagePeak*controls.controllerStepSeconds/
    (controls.dcInductanceMinMilliHenry/1000),controls.dcCurrentMax);
  const roundUp=(v,step,margin=1.05)=>Math.ceil(v*margin/step)*step;
  const phaseMax=roundUp(controls.phasePeakMax,.5);
  const lineMax=roundUp(linePeak,.5,1.1);
  const dcMax=roundUp(controls.dcCurrentMax,.5);
  const loadMax=roundUp(loadCurrentPeak,5,1.1);
  const leMax=roundUp(leCurrentPeak,50,1.02);
  const halfCurrentMax=roundUp(halfWaveCurrentPeak,10);
  const energyMax=roundUp(halfWaveEnergyPeak,100,1.01);
  const controlMax=roundUp(controllerCurrentPeak,5,1.1);
  const bounds=Object.freeze({
    phaseVoltage:[-phaseMax,phaseMax],
    lineVoltage:[-lineMax,lineMax],
    dcVoltage:[-lineMax,lineMax],
    valveVoltage:[-lineMax,lineMax],
    mixedDC:[-lineMax,lineMax],
    scrCurrent:[0,dcMax],
    poleCurrent:[0,dcMax],
    acCurrent:[-dcMax,dcMax],
    loadCurrent:[0,loadMax],
    loadAcCurrent:[-loadMax,loadMax],
    leCurrent:[0,leMax],
    leAcCurrent:[-leMax,leMax],
    controllerCurrent:[0,controlMax],
    firingAngle:[0,90],
    halfWaveVoltage:[-roundUp(controls.halfWaveVoltageMax,50),roundUp(controls.halfWaveVoltageMax,50)],
    halfWaveCurrent:[-roundUp(halfWaveCurrentPeak,10)*.1,halfCurrentMax],
    halfWaveEnergy:[0,energyMax]
  });
  // Focus is a second fixed, nominal teaching scale, not curve-driven autoscaling.
  // Full retains the original envelope derived from permitted parameter extrema.
  const focus=Object.freeze({
    phaseVoltage:[-1.5,1.5],lineVoltage:[-2,2],dcVoltage:[-2,2],
    valveVoltage:[-2,2],mixedDC:[-2,2],
    scrCurrent:[0,2.5],poleCurrent:[0,2.5],acCurrent:[-2.5,2.5],
    loadCurrent:[0,3],loadAcCurrent:[-3,3],
    leCurrent:[0,3],leAcCurrent:[-3,3],
    controllerCurrent:[0,3],firingAngle:[0,90],
    halfWaveVoltage:[-150,150],halfWaveCurrent:[0,15],
    halfWaveEnergy:[0,3]
  });
  let selectedPreset='focus';
  function preset(){return selectedPreset;}
  function setPreset(next){
    if(next!=='focus'&&next!=='full')throw Error('Unknown axis preset: '+next);
    selectedPreset=next;
  }
  function range(kind){
    if(!Object.prototype.hasOwnProperty.call(bounds,kind))throw Error('Unknown fixed axis: '+kind);
    return (selectedPreset==='focus'?focus:bounds)[kind].slice();
  }
  function outside(values,min,max){
    // Floating SCR voltages are undefined and intentionally skipped.
    return values.some(v=>Number.isFinite(v)&&(v<min-1e-8||v>max+1e-8));
  }
  function lccKind(title){
    if(title.includes('SCR anode–cathode voltages'))return 'valveVoltage';
    if(title.includes('SCR currents'))return 'scrCurrent';
    if(title.includes('AC phase currents'))return 'acCurrent';
    if(title.includes('Line voltages'))return 'lineVoltage';
    if(title.includes('Phase voltages'))return 'phaseVoltage';
    if(title.includes('voltage and current'))return 'mixedDC';
    if(title.includes('DC current')||title.includes('pole current'))return 'poleCurrent';
    if(title.includes('DC voltage')||title.includes('DC voltages'))return 'dcVoltage';
    throw Error('Unclassified LCC chart: '+title);
  }
  function loadKind(title,mode){
    if(title.includes('DC quantities'))return 'dcVoltage';
    if(title.includes('phase currents'))return mode==='LE'?'leAcCurrent':'loadAcCurrent';
    if(title.includes('SCR currents')||title.includes('DC output current')||title.includes('DC current')||title.includes('Selected SCR current'))return mode==='LE'?'leCurrent':'loadCurrent';
    if(title.includes('Line voltages'))return 'lineVoltage';
    if(title.includes('Phase voltages')||title.includes('phase voltages'))return 'phaseVoltage';
    if(title.includes('SCR voltages')||title.includes('SCR voltage'))return 'valveVoltage';
    if(title.includes('DC voltage')||title.includes('DC output voltage'))return 'dcVoltage';
    throw Error('Unclassified load chart: '+title);
  }
  function sourceKind(chart){
    return ({scr:'scrCurrent',transfer:'scrCurrent',phase:'lineVoltage',power:'dcVoltage',
      dc:'mixedDC',rle:'loadCurrent',control:'controllerCurrent',alphaControl:'firingAngle'})[chart];
  }
  return {controls,range,preset,setPreset,outside,lccKind,loadKind,sourceKind};
})();
