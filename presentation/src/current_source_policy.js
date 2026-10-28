/* Per-lesson engineering constraints: only controls with causal effects are enabled. */
'use strict';
const CurrentSourcePolicy = (() => {
  const all=['idc','alphaR','muR','csLc','loadR','loadL','loadE'];
  const lessons={
    intro:{controls:['idc','alphaR','loadR','loadL','loadE'],model:true,charts:['auto','rle','dc','scr'],overlap:'none'},
    constant:{controls:['idc','alphaR'],charts:['auto','scr','dc','phase'],overlap:'none'},
    valves:{controls:['alphaR'],charts:['auto','scr','phase','dc'],overlap:'none',fixedIdc:1},
    commutation:{controls:['csLc'],charts:['auto','transfer','phase','scr','dc'],overlap:'calculated',fixedIdc:1,fixedAlphaR:15,fixedVPeak:1},
    overlap:{controls:['csLc'],charts:['auto','transfer','phase','scr','dc'],overlap:'calculated',fixedIdc:1,fixedAlphaR:15,fixedVPeak:1},
    comparison:{controls:['idc','alphaR','loadR','loadL','loadE'],model:true,charts:['auto','rle','dc'],overlap:'none'},
    controller:{controls:['idc','loadR','loadL','loadE'],charts:['auto','control','alphaControl'],overlap:'none',fixedAlphaR:15},
    polarity:{controls:['alphaR'],station:true,charts:['auto','scr','phase','dc','power'],overlap:'assumed',fixedIdc:1},
    transition:{controls:[],charts:['auto','dc','power'],overlap:'assumed',fixedIdc:1}
  };
  function forLesson(lesson){const spec=lessons[lesson];if(!spec)throw Error('Unknown teaching objective '+lesson);return spec;}
  function effective(lesson,p,side='rectifier'){
    const spec=forLesson(lesson),q={...p};
    if(spec.fixedIdc!==undefined)q.idc=spec.fixedIdc;
    if(spec.fixedAlphaR!==undefined)q.alphaR=spec.fixedAlphaR;
    if(spec.fixedVPeak!==undefined)q.vPeak=spec.fixedVPeak;
    if(spec.overlap==='none'){
      q.csOverlapMode='manual';q.muR=0;
    }else if(spec.overlap==='calculated'){
      q.csOverlapMode='calculated';
    }else{
      q.csOverlapMode='manual';
    }
    if(lesson==='polarity'&&side==='inverter')q._csSide='inverter';
    return q;
  }
  function enabled(lesson,control,side='rectifier'){
    const spec=forLesson(lesson);
    return spec.controls.includes(control)&&(lesson!=='polarity'||control!=='alphaR'||side==='rectifier') ||
      (lesson==='polarity'&&side==='inverter'&&control==='alphaI');
  }
  function normalizeChart(lesson,chart){const valid=forLesson(lesson).charts;return valid.includes(chart)?chart:'auto';}
  function report(){return Object.fromEntries(Object.keys(lessons).map(l=>[l,{...lessons[l],controls:[...lessons[l].controls]}]));}
  return {forLesson,effective,enabled,normalizeChart,all,report};
})();
