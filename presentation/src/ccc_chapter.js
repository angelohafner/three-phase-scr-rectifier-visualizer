/* Chapter 04 interactive engineering lab; uses validated six-pulse bridge waveforms. */
'use strict';
const CCCChapter=(()=>{
 // Four parameter-driven laboratories with one physical operating point each.
 const lessons=[
  ['lcc','01 · Reactive Power in LCC','Vary α, I_dc, AC voltage or L_c. Observe current displacement, Q and the calculated commutation overlap.','phasor','ac'],
  ['shunt','02 · Shunt Capacitor Compensation','Change the shunt capacitor bank. Compare converter Q, capacitive injection and the reactive power actually drawn from the grid.','power','ac'],
  ['series','03 · Series Capacitors and Commutation','Change C, L_c or I_dc and observe the dynamic capacitor contribution, net commutating voltage and the SCR current transfer.','drive','transfer'],
  ['compare','04 · LCC versus CCC · Active Power and Reactive Demand','Compare matched fundamental active power or identical settings. Observe P₁, Q₁, Q/P, displacement PF, α and μ.','compare','powerCompare']
 ];
 const names=['a','b','c'];
 let settings={alpha:15,idc:.8,vPeak:1,LmH:.24,CmF:26,R:.012,f:60,qShunt:.40};
 let mode='LCC',cursor=8,comparisonBasis='equal-power',cacheKey='',cached=null,needRepaint=null;
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
   const lab=currentLesson()[0],hasShunt=lab==='shunt';
   const p={...settings,CmF:mode==='LCC'?0:settings.CmF,
     qShunt:hasShunt?settings.qShunt:0};
   const key=JSON.stringify({parameters:p,lab,basis:comparisonBasis});
   if(key!==cacheKey){
     cacheKey=key;
     const lcc=CCCModel.solve({...p,CmF:0});
     let matched=null;
     let main=mode==='LCC'?lcc:CCCModel.solve(p);
     if(lab==='compare'&&comparisonBasis==='equal-power'){
       matched=CCCPowerMatch.match(lcc,p);
       main=matched.valid?matched.ccc:{valid:false,error:matched.error};
     }
     cached={main,lcc,matched,basis:comparisonBasis};
   }
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
   const shunt=currentLesson()[0]==='shunt';
   return nativeSchematics[(hasCap?'ccc':'lcc')+(shunt?'_shunt':'')];
 }
 function updateCircuit(point,hasCap,values,targetSvg=null){
   const svg=targetSvg||$('ch4-circuit')?.querySelector('svg[data-native-symbols="true"]');
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
   const dcLabel=svg.querySelector('#dc-current-label');
   if(dcLabel)dcLabel.textContent='I_dc = '+fmt(values.idc,2)+' p.u.';
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
 function barPlot(canvas,items,title){
   // Both teaching presets use deterministic Q-axis limits; no autoscaling.
   const box=canvas.getBoundingClientRect(),w=Math.max(200,box.width),
     h=Math.max(185,box.height),d=Math.min(2,window.devicePixelRatio||1);
   canvas.width=Math.round(w*d);canvas.height=Math.round(h*d);
   const ctx=canvas.getContext('2d');ctx.setTransform(d,0,0,d,0,0);
   ctx.fillStyle='#fbfdfe';ctx.fillRect(0,0,w,h);
   const full=FixedAxes.preset()==='full';
   const comparing=title.includes('COMPARISON');
   // Nominal Q differences remain legible without autoscaling during slider changes.
   const lo=full?-2.5:(comparing?0:-1.35),hi=full?2.5:(comparing?.85:1.45);
   const x0=45,x1=w-12,y0=43,y1=h-46;
   const Y=v=>y1-(v-lo)/(hi-lo)*(y1-y0);
   ctx.fillStyle='#24495e';ctx.font='600 11px "Segoe UI",Arial';
   ctx.fillText(title,10,16,w-20);
   if(comparing){
     ctx.fillStyle='#607b8b';ctx.font='10px "Segoe UI",Arial';
     const delta=items[1].value-items[0].value;
     const relative=Math.abs(items[0].value)>1e-9?100*delta/items[0].value:NaN;
     ctx.fillText('ΔQ₁ CCC − LCC = '+fmt(delta,4)+' p.u. ('+
       (relative>=0?'+':'')+fmt(relative,2)+'%)',12,32,w-24);
   }
   for(let k=0;k<=4;k++){
     const y=y0+k*(y1-y0)/4, val=hi-(hi-lo)*k/4;
     ctx.strokeStyle='#e6edf2';ctx.lineWidth=.8;ctx.beginPath();
     ctx.moveTo(x0,y);ctx.lineTo(x1,y);ctx.stroke();
     ctx.fillStyle='#6c8493';ctx.font='9px "Segoe UI",Arial';
     ctx.fillText(fmt(val,1),4,y+3);
   }
   const origin=Y(0);
   ctx.strokeStyle='#9eb0b9';ctx.lineWidth=1.2;
   ctx.beginPath();ctx.moveTo(x0,origin);ctx.lineTo(x1,origin);ctx.stroke();
   const cell=(x1-x0)/items.length;
   items.forEach((item,k)=>{
     const center=x0+(k+.5)*cell,wide=Math.min(46,cell*.54),
       value=Math.max(lo,Math.min(hi,item.value)),y=Y(value);
     ctx.fillStyle=item.color;
     ctx.fillRect(center-wide/2,Math.min(origin,y),wide,Math.max(1,Math.abs(y-origin)));
     ctx.fillStyle='#315468';ctx.font='600 10px "Segoe UI",Arial';
     ctx.fillText(fmt(item.value,3),center-20,
       value>=0?Math.max(y0+9,y-6):Math.min(y1-4,y+13));
     ctx.font='9px "Segoe UI",Arial';
     item.label.split('|').forEach((piece,j)=>
       ctx.fillText(piece,center-Math.min(36,piece.length*2.6),h-25+j*11));
   });
   canvas.dataset.axisMode='fixed';
   canvas.dataset.plotLimits=JSON.stringify({x:[0,items.length],y:[lo,hi]});
   canvas.dataset.axisClipped=String(items.some(item=>item.value<lo||item.value>hi));
 }

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
      const p=res.powers;
      barPlot(canvas,[{label:'Q|converter',value:p.Q,color:'#be3e57'},
        {label:'−Q|capacitor',value:-p.Qshunt,color:'#168d94'},
        {label:'Q|grid',value:p.Qgrid,color:'#ae7d34'}],
        'REACTIVE POWER AT THE AC BUS (p.u.)');
      return;
   }else if(kind==='powerCompare'){
      barPlot(canvas,[{label:'Q₁|LCC',value:old.powers.Q,color:'#287da4'},
        {label:'Q₁|CCC',value:res.powers.Q,color:'#bf3e57'}],
        comparisonBasis==='equal-power'?
          'CONVERTER Q₁ COMPARISON · EQUAL ACTIVE POWER (p.u.)':
          'CONVERTER Q₁ COMPARISON · SAME FIRING SETTINGS (p.u.)');
      return;
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
 function metrics(result,lcc,lab){
   const p=result.powers;
   if(lab==='lcc')return [
     ['Q₁ converter',fmt(p.Q,3)+' p.u.'],['P₁ converter',fmt(p.P,3)+' p.u.'],
     ['Overlap μ',fmt(result.avgMu,2)+'°'],['Displacement PF',fmt(p.pf,3)],
     ['I_dc imposed',fmt(settings.idc,2)+' p.u.']];
   if(lab==='shunt')return [
     ['Q converter',fmt(p.Q,3)+' p.u.'],['Q capacitor',fmt(p.Qshunt,3)+' p.u.'],
     ['Q from grid',fmt(p.Qgrid,3)+' p.u.'],
     ['PCC displacement PF',fmt(Math.abs(p.P)/Math.max(1e-9,Math.hypot(p.P,p.Qgrid)),3)],
     ['Overlap μ',fmt(result.avgMu,2)+'°']];
   if(lab==='series'){
     const capPeak=Math.max(...result.traces.flatMap(t=>t.capacitors.map(Math.abs)));
     return [['Overlap μ',fmt(result.avgMu,2)+'°'],['Q₁ converter',fmt(p.Q,3)+' p.u.'],
       ['P₁ converter',fmt(p.P,3)+' p.u.'],['Peak |v_C|',fmt(capPeak,3)+' p.u.'],
       ['Periodic error',fmt(result.residual,6)]];
   }
   // Fundamental AC P1 and Q1 are computed from the source voltage/current phasors.
   // Displacement power factor is distinct from true harmonic power factor.
   const m=CCCPowerMatch.summarize(lcc,result);
   return [['P₁ LCC',fmt(m.P_LCC,4)+' p.u.'],
     ['P₁ CCC',fmt(m.P_CCC,4)+' p.u.'],
     ['ΔP₁',fmt(m.deltaP,5)+' p.u.'],
     ['Q₁ LCC',fmt(m.Q_LCC,4)+' p.u.'],
     ['Q₁ CCC',fmt(m.Q_CCC,4)+' p.u.'],
     ['ΔQ₁',fmt(m.deltaQ,4)+' p.u.'],
     ['Q/P LCC',fmt(m.QoverP_LCC,3)],
     ['Q/P CCC',fmt(m.QoverP_CCC,3)],
     ['PF₁ LCC',fmt(m.PF1_LCC,3)],
     ['PF₁ CCC',fmt(m.PF1_CCC,3)],
     ['α LCC',fmt(m.alpha_LCC,2)+'°'],
     ['α CCC',fmt(m.alpha_CCC,2)+'°'],
     ['μ LCC',fmt(m.mu_LCC,2)+'°'],
     ['μ CCC',fmt(m.mu_CCC,2)+'°']];
 }
 function renderCircuits(lab,main,lcc,index){
   const host=$('ch4-circuit'),point=main.traces[index];
   if(lab==='compare'){
     host.innerHTML='<div class="ch4-compare-circuits">'+
       '<div class="ch4-compare-item"><span>LCC · α='+fmt(lcc.params.alpha,2)+'°</span>'+nativeSchematics.lcc+'</div>'+
       '<div class="ch4-compare-item"><span>CCC · α='+fmt(main.params.alpha,2)+'°</span>'+nativeSchematics.ccc+'</div></div>';
     const diagrams=host.querySelectorAll('svg[data-native-symbols="true"]');
     updateCircuit(lcc.traces[Math.min(lcc.traces.length-1,index)],false,settings,diagrams[0]);
     updateCircuit(point,true,settings,diagrams[1]);
     // Emphasize the commutation paths in the small side-by-side circuit tiles.
     // The full native vector geometry and provenance remain embedded in each SVG.
     for(const svg of diagrams){
       svg.dataset.fullViewBox=svg.getAttribute('viewBox');
       svg.setAttribute('viewBox','315 58 640 456');
     }
   }else{
     host.innerHTML=circuitSvg(point,lab==='series',settings);
     updateCircuit(point,lab==='series',settings);
   }
 }
 function refresh(lesson){
   if(!$('ch4-root'))return;
   const {main,lcc,matched}=getResults(),status=$('ch4-status');
   const lab=lesson[0];
   if(lab==='compare'){
     $('ch4-basis-detail').textContent=comparisonBasis==='equal-power'?
       'CCC α is calculated to match LCC fundamental AC P₁. I_dc, AC voltage, L_c, R and C are held fixed.':
       'Both converters use the same α and I_dc; their active powers can differ.';
   }
   if(!main.valid||!lcc.valid){
     status.className='ch4-status invalid';
     status.textContent='OUTSIDE VALID OPERATING RANGE · '+(main.error||lcc.error);
     for(const id of ['ch4-chart-a','ch4-chart-b']){
       const canvas=$(id),g=canvas.getContext('2d');
       g.clearRect(0,0,canvas.width,canvas.height);
       canvas.dataset.axisMode='invalid';
     }
     $('ch4-circuit').innerHTML='<div class="ch4-fault">No valid switching solution. Change α, I_dc, L_c or C. No artificial waveforms are shown.</div>';
     $('ch4-metrics').innerHTML='';$('ch4-warning').textContent='';return;
   }
   const idx=Math.min(main.traces.length-1,
     Math.floor(cursor*main.traces.length/360));
   status.className='ch4-status';
   if(lab==='compare'){
     status.textContent=comparisonBasis==='equal-power'?
       'EQUAL P₁ ≈ '+fmt(lcc.powers.P,4)+' p.u. · ΔP₁ = '+
       fmt(main.powers.P-lcc.powers.P,5)+' p.u. · α LCC = '+
       fmt(lcc.params.alpha,2)+'° / CCC = '+fmt(main.params.alpha,2)+'° · same I_dc':
       'SAME FIRING SETTINGS · α = '+fmt(lcc.params.alpha,2)+'° · P₁ LCC = '+
       fmt(lcc.powers.P,4)+' / CCC = '+fmt(main.powers.P,4)+' p.u.';
   }else{
     status.textContent=mode+' · μ = '+fmt(main.avgMu,2)+'° · Q₁ = '+
       fmt(main.powers.Q,3)+' p.u. · I_dc imposed';
   }
   renderCircuits(lab,main,lcc,idx);
   plot($('ch4-chart-a'),lesson[3],main,lcc);
   plot($('ch4-chart-b'),lesson[4],main,lcc);
   const readings=metrics(main,lcc,lab);
   $('ch4-metrics').style.setProperty('--ch4-metric-cols',
     String(lab==='compare'?7:readings.length));
   $('ch4-metrics').innerHTML=readings.map(([key,val])=>
     '<div class="ch4-metric"><small>'+key+'</small><strong>'+val+'</strong></div>').join('');
   $('ch4-cursor-value').textContent=fmt(cursor,0)+'°';
   for(const name of Object.keys(settings)){
     const output=$('ch4-'+name+'-value');
     if(output)output.textContent=fmt(settings[name],name==='alpha'||name==='CmF'?0:2);
   }
   const clipped=['ch4-chart-a','ch4-chart-b'].some(id=>$(id).dataset.axisClipped==='true');
   $('ch4-warning').textContent=clipped?
     'FOCUS limit exceeded. Use SCALE: FULL for the complete curve.':'';
 }
 function mount(root,lessonId){
   const lesson=lessons.find(x=>x[0]===lessonId)||lessons[0];
   const lab=lesson[0];
   mode=lab==='lcc'||lab==='shunt'?'LCC':'CCC';cacheKey='';
   root.className='slide technical ch4-slide';root.dataset.lesson=lab;root.id='slide';
   const allowed={
     lcc:['alpha','idc','vPeak','LmH'],
     shunt:['alpha','idc','vPeak','LmH','qShunt'],
     series:['alpha','idc','vPeak','LmH','CmF'],
     compare:['alpha','idc','vPeak','LmH','CmF']
   }[lab];
   const headings={
     lcc:['FUNDAMENTAL PHASORS','AC PHASE CURRENTS'],
     shunt:['REACTIVE POWER BALANCE','AC PHASE CURRENTS'],
     series:['NET COMMUTATING DRIVE','SCR CURRENT TRANSFER'],
     compare:['LCC / CCC CURRENT TRANSFER','REACTIVE POWER COMPARISON']
   }[lab];
   root.innerHTML='<div id="ch4-root" class="ch4-root" data-lesson="'+lab+'">'+
     '<div class="tech-head ch4-head"><div class="tech-index">04 · REACTIVE POWER LABS</div>'+
     '<div class="tech-title"><h1>'+lesson[1]+'</h1><p>'+lesson[2]+'</p></div>'+
     '<span class="ch4-index">'+(lessons.findIndex(x=>x[0]===lab)+1)+' / 4</span></div>'+
     '<div class="ch4-status" id="ch4-status"></div>'+
     (lab==='compare'?
       '<div class="ch4-basis"><label for="ch4-compare-basis">COMPARISON BASIS</label>'+
       '<select id="ch4-compare-basis">'+
       '<option value="equal-power">Same fundamental active power P₁ (CCC α adjusted)</option>'+
       '<option value="same-settings">Same firing angle and parameters</option>'+
       '</select><span id="ch4-basis-detail"></span></div>':'')+
     '<div class="ch4-space">'+
       '<section class="panel"><div class="panel-head"><strong>01 / CIRCUIT</strong>'+
       '<button type="button" class="ch4-enlarge" id="ch4-enlarge">⤢ ENLARGE</button></div>'+
       '<div class="ch4-circuit" id="ch4-circuit"></div></section>'+
       '<section class="panel"><div class="panel-head"><strong>02 / '+headings[0]+'</strong></div>'+
       '<div class="plot-wrapper"><canvas id="ch4-chart-a" aria-label="Synchronized converter waveform or phasor"></canvas></div></section>'+
       '<section class="panel"><div class="panel-head"><strong>03 / '+headings[1]+'</strong></div>'+
       '<div class="plot-wrapper"><canvas id="ch4-chart-b" aria-label="Synchronized current or reactive-power plot"></canvas></div></section></div>'+
     '<div class="ch4-controls" id="ch4-controls">'+
       fields.map(([id,label,unit,min,max,step])=>
         '<label class="ch4-control" data-control="'+id+'"><span>'+label+
         ' <output id="ch4-'+id+'-value">'+fmt(settings[id],2)+'</output> '+unit+'</span>'+
         '<input id="ch4-'+id+'" type="range" min="'+min+'" max="'+max+
         '" step="'+step+'" value="'+settings[id]+'"></label>').join('')+'</div>'+
     '<div class="ch4-metrics" id="ch4-metrics"></div>'+
     '<div class="ch4-notes"><p id="ch4-note">'+lesson[2]+'</p><span id="ch4-warning"></span></div>'+
     '<div class="timeline ch4-timeline"><div class="timeline-top"><span>θ = '+
       '<output id="ch4-cursor-value">'+fmt(cursor,0)+'°</output> · Move the angle cursor to follow SCR conduction.</span></div>'+
       '<input id="ch4-cursor" class="angle-range" type="range" min="0" max="359.8" step="0.2" value="'+cursor+'">'+
       '<div class="ticks"><span>0°</span><span>60°</span><span>120°</span><span>180°</span><span>240°</span><span>300°</span><span>360°</span></div>'+
     '</div></div>';
   if(lab==='compare'){
     $('ch4-compare-basis').value=comparisonBasis;
     $('ch4-compare-basis').onchange=e=>{
       comparisonBasis=e.target.value;cacheKey='';refresh(lesson);
     };
   }
   $('ch4-controls').style.setProperty('--ch4-active-cols',String(allowed.length));
   for(const [id] of fields){
     const control=$('ch4-'+id),visible=allowed.includes(id);
     control.disabled=!visible;
     control.closest('label').style.display=visible?'':'none';
     control.oninput=e=>{
       if(!visible)return;
       settings[id]=Number(e.currentTarget.value);cacheKey='';refresh(lesson);
     };
   }
   $('ch4-enlarge').onclick=()=>{
     const host=$('ch4-circuit');
     if(!host.querySelector('svg'))return;
     $('zoom-content').innerHTML=lab==='compare'?host.innerHTML:host.querySelector('svg').outerHTML;
     if(lab==='compare'){
       // The normal view emphasizes commutation; enlarge restores full circuit topology.
       $('zoom-content').querySelectorAll('svg[data-full-view-box]').forEach(svg=>
         svg.setAttribute('viewBox',svg.dataset.fullViewBox));
     }
     $('zoom-title').textContent='CH 04 · '+lesson[1];
     $('zoom-overlay').classList.add('open');
     $('zoom-overlay').setAttribute('aria-hidden','false');
   };
   $('ch4-cursor').oninput=e=>{cursor=Number(e.currentTarget.value);refresh(lesson);};
   refresh(lesson);
   needRepaint=()=>refresh(lesson);
 }
 function repaint(){if(needRepaint&&$('ch4-root'))needRepaint();}
 return {lessons,mount,repaint,settings,getResults,setSchematics,
   getComparisonBasis:()=>comparisonBasis,
   setComparisonBasis:value=>{
     if(!['equal-power','same-settings'].includes(value))
       throw Error('Unknown comparison basis');
     comparisonBasis=value;cacheKey='';
     if($('ch4-compare-basis'))$('ch4-compare-basis').value=value;
     if(currentLesson()[0]==='compare'&&$('ch4-root'))refresh(currentLesson());
   }};
})();