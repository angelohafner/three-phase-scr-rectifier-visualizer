/* Chapter 04 interactive engineering lab; uses validated six-pulse bridge waveforms. */
'use strict';
const CCCChapter=(()=>{
 const lessons=[
  ['origin','Why Does an LCC Converter Absorb Reactive Power?','The AC fundamental current is displaced from its terminal voltage. Harmonics must not be confused with displacement reactive power.','phasor','ac'],
  ['firing','Firing Angle and Fundamental Displacement','Vary α while maintaining the imposed DC current. Watch the current fundamental, Q and the bridge mean DC voltage.','phasor','dc'],
  ['overlap','Commutation Reactance and Current Overlap','The transformer leakage reactor limits current transfer. The overlap is calculated by the differential equation, not independently imposed.','drive','transfer'],
  ['phasors','Reading Converter Voltage and Current Phasors','The fundamental-frequency Q is calculated from the complex voltage and current phasors at the AC terminals.','phasor','ac'],
  ['stations','Rectifier versus Inverter Reactive Power','Rectifier waveforms are numerically solved here; inverter reactive-demand concepts are qualitative. The model does NOT simulate inverter-side SCR operation or an AC/DC power reversal.','phasor','dc'],
  ['shunt','What Does Shunt Compensation Actually Change?','A shunt capacitor supplies local capacitive vars; it does not change the idealized converter valve currents at a fixed AC bus voltage.','power','ac'],
  ['filters','Shunt Capacitors and Harmonic AC Filters','Fundamental-frequency reactive support and harmonic filtering are distinct functions. This laboratory solves the shunt fundamental Q, not filter resonances.','power','ac'],
  ['series','Where Do CCC Series Capacitors Belong?','Three series capacitors sit between transformer leakage paths and the valve bridge, not in parallel at the AC bus.','capacitors','ac'],
  ['states','The Series-Capacitor Voltage Is a Dynamic State','Each capacitor voltage follows dvc/dt = i/C and stores energy. Its waveform changes with valve conduction.','capacitors','dc'],
  ['central','How Series Capacitors Assist Thyristor Commutation','CORE LAB — the circuit, available commutating voltage and outgoing/incoming SCR currents share one numerical switching solution.','drive','transfer'],
  ['current','Follow Both SCR Currents During Commutation','A constant DC current imposes the sum of conducting valve currents, but the transfer waveform and μ are dynamically calculated.','drive','transfer'],
  ['ccc','Capacitor-Commutated Converter: Six-Pulse Laboratory','Six firing events per fundamental cycle, phase-capacitor states, switching-dependent reactor currents and periodic shooting.','capacitors','valves'],
  ['compare','Conventional LCC versus CCC, Same Conditions','Both switching models use the SAME AC/DC, firing, leakage and resistance parameters. The metrics report independent μ, Q₁ and initial commutating drive for each topology.','compare','transfer'],
  ['grid','AC Voltage Sensitivity and Grid Strength','Explore imposed bus-voltage variations. The surrounding Thevenin grid and commutation-failure recovery are NOT solved by this stiff-source model.','power','drive'],
  ['limits','Operating Limits, Validation and Conclusions','Invalid firing, uncompleted commutation or failed periodic shooting must be reported, never replaced by invented current waveforms.','power','capacitors']
 ];
 const names=['a','b','c'];
 let settings={alpha:15,idc:.8,vPeak:1,LmH:.24,CmF:26,R:.012,f:60,qShunt:.40};
 let mode='CCC',cursor=8,cacheKey='',cached=null,previousC=26,needRepaint=null;
 const $=id=>document.getElementById(id),fmt=(x,n=2)=>Number.isFinite(x)?x.toFixed(n):'—';
 const fields=[['alpha','α firing','°',0,60,1],['idc','I DC','p.u.',.3,1.2,.05],['vPeak','V phase pk','p.u.',.8,1.2,.05],
   ['LmH','L commutation','mH',.12,.38,.01],['CmF','C series','mF',12,100,1],['qShunt','Q shunt','p.u.',0,1.2,.05]];
 const fixedBounds=(kind)=>{
   const full=typeof FixedAxes!=='undefined'&&FixedAxes.preset()==='full';
   const domains={current:full?[-.05,1.6]:[-.02,1.35],voltage:full?[-3.5,3.5]:[-2.4,2.4],signedCurrent:full?[-1.8,1.8]:[-1.4,1.4],
    cap:full?[-1.3,1.3]:[-.55,.55],power:full?[-2,2]:[-1.1,1.4],dc:full?[-3.5,3.5]:[-2,2]};
   return domains[kind]||domains.voltage;
 };
 function getResults(){
   const hasShunt=['shunt','filters'].includes(currentLesson()[0]);
   const p={...settings,CmF:mode==='LCC'?0:settings.CmF,
     qShunt:hasShunt?settings.qShunt:0};const key=JSON.stringify(p);
   if(key!==cacheKey){cacheKey=key;cached={main:CCCModel.solve(p),lcc:CCCModel.solve({...p,CmF:0})};}
   return cached;
 }
 function currentLesson(){return lessons.find(l=>l[0]===$('ch4-root')?.dataset.lesson)||lessons[0];}
 let nativeSchematics=null;
 function setSchematics(values){
   const required=['lcc','ccc','lcc_shunt','ccc_shunt'];
   if(!values||required.some(key=>!values[key]||!values[key].includes('data-native-symbols="true"')))
     throw Error('Missing native Schemdraw Chapter 04 schematic variants');
   nativeSchematics=values;
 }
 function circuitSvg(point,hasCap,values){
   if(!nativeSchematics)throw Error('Native Schemdraw diagrams not loaded');
   const shunt=['shunt','filters'].includes(currentLesson()[0]);
   return nativeSchematics[(hasCap?'ccc':'lcc')+(shunt?'_shunt':'')];
 }
 function updateCircuit(point,hasCap,values){
   const svg=$('ch4-circuit')?.querySelector('svg[data-native-symbols="true"]');
   if(!svg)return;
   const amps=point?.current||[0,0,0],capVolts=point?.capacitors||[0,0,0];
   const upper={a:'T1',b:'T3',c:'T5'},lower={a:'T2',b:'T4',c:'T6'};
   for(const [k,phase] of names.entries()){
     const current=amps[k],active=Math.abs(current)>0.025;
     svg.querySelectorAll('[data-wire-phase="'+phase+'"]').forEach(w=>
       w.setAttribute('data-active',String(active)));
     for(const [valve,conducting] of [[upper[phase],current>0.025],[lower[phase],current<-.025]]){
       const symbol=svg.querySelector('[data-valve="'+valve+'"]');
       if(symbol)symbol.setAttribute('data-active',String(conducting));
     }
     const iText=svg.querySelector('#live-current-'+phase);
     if(iText)iText.textContent='i'+phase+' = '+fmt(current,2)+' p.u.';
     const capacitor=svg.querySelector('#live-capacitor-'+phase);
     if(capacitor)capacitor.textContent='vC'+phase+' = '+fmt(capVolts[k],3)+' p.u.';
   }
   const shuntText=svg.querySelector('#live-shunt');
   if(shuntText)shuntText.textContent='Q shunt = '+fmt(values.qShunt*values.vPeak**2,2)+' p.u.';
   svg.dataset.dynamicState='synchronized';
 }
 function graph(canvas,tracks,opts={}){
   const rect=canvas.getBoundingClientRect(),w=Math.max(200,rect.width),h=Math.max(185,rect.height);
   const d=Math.min(2,window.devicePixelRatio||1);canvas.width=Math.round(w*d);canvas.height=Math.round(h*d);
   const ctx=canvas.getContext('2d');ctx.setTransform(d,0,0,d,0,0);ctx.clearRect(0,0,w,h);
   const [lo,hi]=fixedBounds(opts.kind||'voltage'),xEnd=opts.xEnd||360,x0=49,x1=w-14,y0=52,y1=h-34;
   const X=x=>x0+(x/xEnd)*(x1-x0),Y=y=>y1-(y-lo)/(hi-lo)*(y1-y0);
   ctx.fillStyle='#fbfdff';ctx.fillRect(0,0,w,h);ctx.fillStyle='#214960';ctx.font='600 12px "Segoe UI", Arial';ctx.fillText(opts.title||'',12,18,w-20);
   ctx.save();ctx.beginPath();ctx.rect(x0,y0,x1-x0,y1-y0);ctx.clip();
   if(opts.mu>0){ctx.fillStyle='#e8d9db90';ctx.fillRect(X(0),y0,X(opts.mu)-x0,y1-y0);}
   const ticks=xEnd===60?[0,10,20,30,40,50,60]:[0,60,120,180,240,300,360];
   for(const x of ticks){ctx.strokeStyle='#e8eff3';ctx.lineWidth=.7;ctx.beginPath();ctx.moveTo(X(x),y0);ctx.lineTo(X(x),y1);ctx.stroke();}
   for(let j=0;j<=4;j++){let y=y0+j*(y1-y0)/4;ctx.strokeStyle='#e5edf2';ctx.beginPath();ctx.moveTo(x0,y);ctx.lineTo(x1,y);ctx.stroke();}
   if(lo<0&&hi>0){ctx.strokeStyle='#a9bfcb';ctx.beginPath();ctx.moveTo(x0,Y(0));ctx.lineTo(x1,Y(0));ctx.stroke();}
   for(const tr of tracks){ctx.beginPath();ctx.strokeStyle=tr.color||'#bd3d56';ctx.lineWidth=tr.width||2;ctx.setLineDash(tr.dash||[]);
     let open=false;for(const q of tr.data){let x=q[0],y=q[1];if(x<0||x>xEnd||!Number.isFinite(y)){open=false;continue;}
       const yy=Y(y);if(!open)ctx.moveTo(X(x),yy);else ctx.lineTo(X(x),yy);open=true;
     }ctx.stroke();ctx.setLineDash([]);}
   if(opts.cursor!==undefined){ctx.strokeStyle='#b53e4e';ctx.setLineDash([4,4]);ctx.beginPath();ctx.moveTo(X(Math.min(xEnd,opts.cursor)),y0);ctx.lineTo(X(Math.min(xEnd,opts.cursor)),y1);ctx.stroke();ctx.setLineDash([]);}
   ctx.restore();ctx.font='10px "Segoe UI", Arial';ctx.fillStyle='#698092';
   for(const x of ticks){ctx.fillText(x+'°',Math.max(x0,Math.min(x1-22,X(x)-12)),h-13);}
   for(let j=0;j<=4;j++){const val=hi-j*(hi-lo)/4;ctx.fillText(fmt(val,Math.abs(hi)>5?0:1),3,y0+6+j*(y1-y0)/4);}
   let lx=12;for(const tr of tracks.slice(0,4)){ctx.fillStyle=tr.color||'#bd3d56';ctx.fillRect(lx,31,13,2);ctx.fillStyle='#37566a';ctx.font='9px "Segoe UI", Arial';ctx.fillText(tr.label,lx+16,34);lx+=Math.max(57,tr.label.length*6+28);}
   canvas.dataset.axisMode='fixed';canvas.dataset.plotLimits=JSON.stringify({x:[0,xEnd],y:[lo,hi]});
   canvas.dataset.axisClipped=String(tracks.some(t=>t.data.some(q=>Number.isFinite(q[1])&&(q[1]<lo||q[1]>hi))));
 }
 const line=(tr,fn,color,label)=>({label,color,data:tr.map(q=>[q.angle,fn(q)])});
 function plot(canvas,kind,res,old){
   const tr=res.traces,p=res.params,first=tr.filter(q=>q.angle<60),mu=res.mu[0];
   const source=idx=>tr.map(q=>[q.angle,q.source[idx]]);
   const current=idx=>tr.map(q=>[q.angle,q.current[idx]]);
   let opts={cursor,kind:'voltage',title:'',xEnd:360},series=[];
   if(kind==='drive'){
     const s=first,sign=-1;
     const supply=q=>sign*(q.source[2]-q.source[1]),assist=q=>-sign*(q.capacitors[2]-q.capacitors[1]);
     const drive=q=>supply(q)+assist(q)-sign*p.R*(q.current[2]-q.current[1]);
     series=[line(s,supply,'#287da4','AC line'),line(s,assist,'#c38a28','Capacitor'),
       line(s,drive,'#bc3c57','Net drive (incl. R)')];
     opts={title:'COMMUTATING VOLTAGE · FIRST 60° SECTOR',kind:'voltage',xEnd:60,mu,cursor};
   }else if(kind==='transfer'){
     series=[line(first,q=>Math.max(0,-q.current[2]),'#c13d56','Incoming T6'),line(first,q=>Math.max(0,-q.current[1]),'#227ca4','Outgoing T4'),
       line(first,q=>Math.max(0,q.current[0]),'#0e8693','Stationary T1')];
     opts={title:'SCR CURRENT TRANSFER · DYNAMIC μ',kind:'current',xEnd:60,mu,cursor};
   }else if(kind==='capacitors'){
     series=[line(tr,q=>q.capacitors[0],'#be3b56','v C,a'),line(tr,q=>q.capacitors[1],'#2a7ca5','v C,b'),line(tr,q=>q.capacitors[2],'#0c8f99','v C,c')];
     opts={title:'SERIES CAPACITOR VOLTAGES',kind:'cap',cursor};
   }else if(kind==='valves'){
     const names=['T1','T2','T3','T4','T5','T6'];
     const phases=[0,0,1,1,2,2],upper=[true,false,true,false,true,false];
     series=names.map((name,j)=>line(tr,q=>Math.max(0,(upper[j]?1:-1)*q.current[phases[j]]),
       ['#c13d55','#b57c31','#277fa3','#725ab3','#0b8c94','#60788a'][j],name));
     opts={title:'ALL SIX SCR VALVE CURRENTS',kind:'current',cursor};
   }else if(kind==='ac'){
     series=[{label:'i a',color:'#bc3c55',data:current(0)},{label:'i b',color:'#287da4',data:current(1)},
       {label:'i c',color:'#0b8892',data:current(2)}];opts={title:'AC PHASE CURRENT · SIX-PULSE BRIDGE',kind:'current',cursor};
     opts.kind='signedCurrent'; // Bipolar AC currents have their own fixed physical scale.
   }else if(kind==='dc'){
     series=[line(tr,q=>q.dc,'#bc3c56','v DC'),line(tr,q=>q.source[0],'#287da4','v a')];
     opts={title:'SIGNED BRIDGE DC VOLTAGE',kind:'dc',cursor};
   }else if(kind==='compare'){
     series=[line(tr,q=>Math.max(0,-q.current[2]),'#bc3c56','CCC incoming'),line(old.traces.filter(q=>q.angle<60),q=>Math.max(0,-q.current[2]),'#287da4','LCC incoming')];
     // The first trace is explicitly windowed to match the reference.
     series[0].data=first.map(q=>[q.angle,Math.max(0,-q.current[2])]);
     opts={title:'LCC AND CCC CURRENT TRANSFER',kind:'current',xEnd:60,mu,cursor};
   }else if(kind==='power'){
     const a=res.powers,bar=[['P',a.P],['Q conv',a.Q],['Q shunt',-a.Qshunt],['Q grid',a.Qgrid]];
     const make=bar.map(([label,value],i)=>({label,color:['#166f91','#be3e57','#139a8e','#ad7a34'][i],data:[[0,value],[60,value]]}));
     series=make;opts={title:'POWER ACCOUNTING · FIXED BUS VOLTAGE',kind:'power',xEnd:60};
   }else if(kind==='phasor'){
     const ph=res.powers.phasor,vr=ph.v,ir=ph.i,scale=1;
     const tip=(v)=>[v[0]*scale,v[1]*scale];
     const v=tip(vr),i=tip(ir);
     const w=canvas.getBoundingClientRect().width||300,h=canvas.getBoundingClientRect().height||250,d=Math.min(2,devicePixelRatio||1);
     canvas.width=Math.round(w*d);canvas.height=Math.round(h*d);const g=canvas.getContext('2d');g.setTransform(d,0,0,d,0,0);
     const ox=w*.50,oy=h*.57,full=FixedAxes.preset()==='full',range=full?1.8:1.35,r=Math.min(w*.37,h*.33)/range,vmap=t=>[ox+t[0]*r,oy-t[1]*r];
     g.fillStyle='#fbfdff';g.fillRect(0,0,w,h);g.fillStyle='#1c435c';g.font='600 12px "Segoe UI", Arial';g.fillText('FUNDAMENTAL VOLTAGE / CURRENT PHASORS',10,17,w-20);
     g.strokeStyle='#e1e9ee';g.lineWidth=1;g.beginPath();g.moveTo(20,oy);g.lineTo(w-20,oy);g.moveTo(ox,37);g.lineTo(ox,h-22);g.stroke();
     for(const [vector,color,label] of [[v,'#287da4','V 1'],[i,'#bc3c56','I 1']]){
       const [px,py]=vmap(vector);g.strokeStyle=color;g.lineWidth=3;g.beginPath();g.moveTo(ox,oy);g.lineTo(px,py);g.stroke();g.fillStyle=color;g.beginPath();g.arc(px,py,4,0,2*Math.PI);g.fill();g.font='600 11px "Segoe UI", Arial';g.fillText(label,px+5,py-7);
     }
     g.fillStyle='#355b71';g.font='12px "Segoe UI", Arial';g.fillText('Displacement φ = '+fmt(ph.angle,1)+'°',12,h-12);
     canvas.dataset.axisMode='fixed';canvas.dataset.axisClipped='false';canvas.dataset.plotLimits=JSON.stringify({x:[-range,range],y:[-range,range]});return;
   }
   graph(canvas,series,opts);
 }
 function firstCommutatingDrive(res){
   // Lower-group commutation T4 -> T6 uses the positive transfer-current convention.
   const t=res.traces[0],p=res.params,sign=-1;
   return sign*((t.source[2]-t.source[1])
      -(t.capacitors[2]-t.capacitors[1])
      -p.R*(t.current[2]-t.current[1]));
 }
 function metrics(res,ref,lessonId){
   if(lessonId==='compare'){
     // Compare two genuinely solved cases at identical AC, DC, firing and L/R settings.
     return [['LCC μ',fmt(ref.avgMu,2)+'°'],['CCC μ',fmt(res.avgMu,2)+'°'],
       ['Δμ CCC−LCC',fmt(res.avgMu-ref.avgMu,2)+'°'],
       ['LCC Q₁',fmt(ref.powers.Q,4)+' p.u.'],
       ['CCC Q₁',fmt(res.powers.Q,4)+' p.u.'],
       ['ΔQ₁ CCC−LCC',fmt(res.powers.Q-ref.powers.Q,4)+' p.u.'],
       ['LCC Ucomm(0°)',fmt(firstCommutatingDrive(ref),3)+' p.u.'],
       ['CCC Ucomm(0°)',fmt(firstCommutatingDrive(res),3)+' p.u.']];
   }
   const p=res.powers;
   return [['P AC',fmt(p.P,3)+' p.u.'],['Q converter',fmt(p.Q,3)+' p.u.'],['Q shunt',fmt(p.Qshunt,3)+' p.u.'],
     ['Q grid',fmt(p.Qgrid,3)+' p.u.'],['PF displacement',fmt(p.pf,3)],['Average μ',fmt(res.avgMu,2)+'°'],
     ['Balance P',fmt(p.imbalance,4)+' p.u.'],['Periodic error',fmt(res.residual,6)]];
 }
 function refresh(lesson){const root=$('ch4-root');if(!root)return;const {main,lcc}=getResults();
   const status=$('ch4-status');if(!main.valid){status.textContent='INVALID OPERATING POINT · '+main.error;status.className='ch4-status invalid';
      for(let id of ['ch4-chart-a','ch4-chart-b']){const c=$(id);const g=c.getContext('2d');g.clearRect(0,0,c.width,c.height);c.dataset.axisMode='invalid';}
      $('ch4-circuit').innerHTML='<div class="ch4-fault">Numerical solution unavailable. Adjust firing angle, capacitance or commutation inductance. No fabricated waveform is shown.</div>';
      $('ch4-metrics').innerHTML='';return;}
   status.className='ch4-status';status.textContent=`${mode} · ${fmt(main.avgMu,2)}° overlap · periodic convergence in ${main.iterations} shooting iterations · ideal fixed DC current`;
   const sample=main.traces[Math.min(main.traces.length-1,Math.floor(cursor*main.traces.length/360))];
   $('ch4-circuit').innerHTML=circuitSvg(sample,mode!=='LCC',settings);
    updateCircuit(sample,mode!=='LCC',settings);
   const panelA=lesson[3],panelB=lesson[4];plot($('ch4-chart-a'),panelA,main,lcc);plot($('ch4-chart-b'),panelB,main,lcc);
   $('ch4-metrics').innerHTML=metrics(main,lcc,lesson[0]).map(([lab,val])=>`<div class="ch4-metric"><small>${lab}</small><strong>${val}</strong></div>`).join('');
   $('ch4-cursor-value').textContent=fmt(cursor,0)+'°';
   for(const name of Object.keys(settings)){let output=$('ch4-'+name+'-value');if(output)output.textContent=fmt(settings[name],name==='alpha'||name==='CmF'?0:2);}
   const flag=$('ch4-warning');const clipped=['ch4-chart-a','ch4-chart-b'].some(id=>$(id).dataset.axisClipped==='true');
   flag.textContent=clipped?'Waveform outside FOCUS limits — choose SCALE: FULL for an uncropped global view.':'';
   if(lesson[0]==='central')$('ch4-note').textContent='The red net commutating drive includes source, instantaneous capacitor-voltage contribution AND the resistive redistribution term. Overlap follows 2XL·di_in/dθ = (e_in − e_out) − (vc,in − vc,out) − R(i_in − i_out). Both currents and capacitor voltages come from the same periodic solution.';
 }
 function mount(root,lessonId){const lesson=lessons.find(x=>x[0]===lessonId)||lessons[0];
   if(lesson[0]==='compare'){mode='CCC';cacheKey='';}
   root.className='slide technical ch4-slide';root.dataset.lesson=lesson[0];root.id='slide';
   root.innerHTML=`<div id="ch4-root" class="ch4-root" data-lesson="${lesson[0]}"><div class="tech-head ch4-head"><div class="tech-index">04 · REACTIVE POWER / CCC</div>
     <div class="tech-title"><h1>${lesson[1]}</h1><p>${lesson[2]}</p></div><span class="ch4-index">${lessons.findIndex(x=>x[0]===lesson[0])+1} / ${lessons.length}</span></div>
     <div class="ch4-status" id="ch4-status"></div>
     <div class="ch4-space">
       <section class="panel"><div class="panel-head"><strong>01 / ELECTRICAL CIRCUIT</strong><button type="button" class="ch4-enlarge" id="ch4-enlarge" aria-label="Enlarge native Schemdraw circuit">⤢ ENLARGE</button></div><div class="ch4-circuit" id="ch4-circuit"></div></section>
       <section class="panel"><div class="panel-head"><strong>02 / VOLTAGE / PHASOR</strong></div><div class="plot-wrapper"><canvas id="ch4-chart-a" aria-label="Synchronized CCC voltage or phasor graph"></canvas></div></section>
       <section class="panel"><div class="panel-head"><strong>03 / CURRENT / POWER</strong></div><div class="plot-wrapper"><canvas id="ch4-chart-b" aria-label="Synchronized CCC current or power graph"></canvas></div></section>
     </div><div class="ch4-controls"><label class="ch4-model-choice">TOPOLOGY <select id="ch4-mode"><option value="CCC">CCC · Series C</option><option value="LCC">LCC · Bypass C</option></select></label>
     ${fields.map(([id,label,unit,min,max,step])=>`<label class="ch4-control"><span>${label} <output id="ch4-${id}-value">${fmt(settings[id],2)}</output> ${unit}</span><input id="ch4-${id}" type="range" min="${min}" max="${max}" step="${step}" value="${settings[id]}"></label>`).join('')}</div>
     <div class="ch4-metrics" id="ch4-metrics"></div><div class="ch4-notes"><p id="ch4-note">${lesson[2]}</p><span id="ch4-warning"></span></div>
     <div class="timeline ch4-timeline"><div class="timeline-top"><span>θ = <output id="ch4-cursor-value">${fmt(cursor,0)}°</output> · The pointer selects one instant; both plots keep fixed scales.</span></div>
     <input id="ch4-cursor" class="angle-range" type="range" min="0" max="359.8" step="0.2" value="${cursor}"><div class="ticks"><span>0°</span><span>60°</span><span>120°</span><span>180°</span><span>240°</span><span>300°</span><span>360°</span></div></div></div>`;
   $('ch4-enlarge').onclick=()=>{
      const svg=$('ch4-circuit')?.querySelector('svg');
      if(!svg)return;
      $('zoom-content').innerHTML=svg.outerHTML;
      $('zoom-title').textContent='CH 04 · NATIVE SCHEMDRAW · '+mode;
      const overlay=$('zoom-overlay');
      overlay.classList.add('open');
      overlay.setAttribute('aria-hidden','false');
    };
    $('ch4-mode').value=mode;
    if(lesson[0]==='compare'){
      $('ch4-mode').disabled=true;
      $('ch4-mode').title='Both LCC and CCC are calculated and displayed simultaneously';
    }
   $('ch4-mode').onchange=e=>{mode=e.target.value;cacheKey='';const c=$('ch4-CmF');c.disabled=mode==='LCC';refresh(lesson);};
   $('ch4-CmF').disabled=mode==='LCC';
   for(const [id] of fields){$( 'ch4-'+id).oninput=e=>{settings[id]=+e.target.value;cacheKey='';refresh(lesson);};}
   // Shunt variation changes the PCC reactive balance, not the bridge dynamics.
   const shuntVisible=['shunt','filters'].includes(lesson[0]);
   const shuntInput=$('ch4-qShunt');
   shuntInput.disabled=!shuntVisible;
   // Hide the entire inactive control: an old positive setting must not
   // imply a connected shunt bank on lessons where there is none.
   shuntInput.closest('label').style.display=shuntVisible?'':'none';
   $('ch4-cursor').oninput=e=>{cursor=+e.target.value;refresh(lesson);};
   refresh(lesson);
   needRepaint=()=>refresh(lesson);
 }
 function repaint(){if(needRepaint&&$('ch4-root'))needRepaint();}
 return {lessons,mount,repaint,settings,getResults,setSchematics};
})();