/* Offline 16:9 LCC lecture deck, including interactive state browsing. */
'use strict';
(() => {
 const DATA=JSON.parse(document.getElementById('presentation-data').textContent);
 const $=id=>document.getElementById(id);
 const params={alphaR:15,alphaI:145,muR:12,muI:15,idc:1,vPeak:1,speed:30,alphaLoad:75,loadR:1,loadL:8,loadE:.2,loadI0:.5,loadMode:'R',hAlpha:50,hR:12,hL:70,hV:120,hFrequency:60};
 const initial={...params};
 let theta=65,slideIndex=0,playing=false,raf=0,lastTick=0,mode='overview',selectedSCR='all',showReference=false,showExplanation=true;
 let cachedSVG='',cachedKey='',runtimeSchedule=[],deck=[];
 const stages=['rectifier','inverter','hvdc'];
 function slide(side,type,id=0){return {side,type,id};}
 deck=[slide('intro','title'),slide('intro','roadmap'),slide('fundamentals','chapter')];
 for(const lesson of ['scr_intro','r_circuit','r_delay','rl_circuit','after180','extinction','compare','commutation']){
   deck.push({side:'fundamentals',type:'fundamentals',lesson});
 }
 deck.push(slide('rectifier','chapter'));
 deck.push({side:'rectifier',type:'load',lesson:'r_intro',alpha:0});
 for(const alpha of [0,30,75,90])deck.push({side:'rectifier',type:'load',lesson:'r_case',alpha});
 deck.push({side:'rectifier',type:'load',lesson:'r_compare',alpha:75});
 deck.push({side:'rectifier',type:'load',lesson:'rl_intro',alpha:75});
 deck.push({side:'rectifier',type:'load',lesson:'le_intro',alpha:75});
 deck.push({side:'rectifier',type:'load',lesson:'rle_intro',alpha:75});
 deck.push({side:'rectifier',type:'load',lesson:'advanced_compare',alpha:75});
 for(let i=1;i<=12;i++)deck.push(slide('rectifier','state',i));
 deck.push(slide('inverter','chapter'));
 for(let i=1;i<=12;i++)deck.push(slide('inverter','state',i));
 deck.push(slide('hvdc','chapter'));
 for(let i=1;i<=24;i++)deck.push(slide('hvdc','state',i));
 deck.push(slide('end','end'));
 const iMap=Object.fromEntries(stages.map(side=>[side,deck.findIndex(x=>x.side===side&&x.type==='state')]));
 const chapterIndex=Object.fromEntries(stages.map(side=>[side,deck.findIndex(x=>x.side===side&&x.type==='chapter')]));
 function current(){return deck[slideIndex];}
 function activeStage(){return current().side==='fundamentals'?'fundamentals':stages.includes(current().side)?current().side:'rectifier';}
 function setTheta(a){theta=+(LCC.mod(a,360)).toFixed(2);}
 function startOfWindow(w){const [a,b]=w;return LCC.mod((a+b)/2,360);}
 function liveWindow(s=current()){
   if(s.type!=='state')return [];
   if(s.side==='hvdc'){const it=runtimeSchedule[s.id-1];return it?it.window:[];}
   return LCC.windows(s.id,s.side==='rectifier'?params.muR:params.muI,0);
 }
 function liveActive(s=current()){
   if(s.side==='hvdc'){const it=runtimeSchedule[s.id-1];return it?it:{id:s.id,r:1,i:1,window:[]};}
   return {id:s.id};
 }
 function goto(idx,opts={}){
   const next=Math.max(0,Math.min(deck.length-1,idx));
   const previous=slideIndex;slideIndex=next;
   if(current().type==='fundamentals'&&!opts.keepAngle&&next!==previous){
     const lesson=current().lesson;
     const beta=HalfWave.get(params,'RL').beta;
     const targets={scr_intro:30,r_circuit:85,r_delay:120,rl_circuit:195,after180:Math.min(beta-5,212),extinction:Math.max(181,beta-1),compare:200,commutation:215};
     setTheta(targets[lesson]??140);
   }
   if(current().type==='load'&&!opts.keepAngle&&next!==previous){
     params.alphaLoad=current().alpha;
     params.loadMode=({rl_intro:'RL',le_intro:'LE',rle_intro:'RLE'}[current().lesson]||'R');
     const a=current().alpha;
     setTheta((a>60&&current().lesson!=='rl_intro')?120+(a-60)/2:a+Math.min(25,(120-a)/2));
   }
   if(current().type==='state'&&!opts.keepAngle){
     const wins=liveWindow();if(wins.length)setTheta(startOfWindow(wins[0]));
   }
   cachedKey='';render();
 }
 function updateSchedule(){runtimeSchedule=LCC.jointSchedule(params.muR,params.muI,LCC.OFFSET);}
 function syncSlideFromAngle(){
   const s=current();if(s.type!=='state')return;
   const previous=slideIndex;
   if(s.side==='hvdc'){
     const i=runtimeSchedule.find(x=>x.window.some(w=>theta>=w[0]&&theta<w[1]));
     if(i)slideIndex=iMap.hvdc+i.id-1;
   }else{
     const state=LCC.at(theta,s.side==='rectifier'?params.muR:params.muI,0);
     slideIndex=iMap[s.side]+state.id-1;
   }
   // Preserve the SVG while the cursor remains in the same electrical state.
   if(slideIndex!==previous)cachedKey='';
 }
 function navDelta(v){pause();goto(slideIndex+v);}
 function stepState(v){pause();const s=current();if(s.type!=='state'){goto(iMap[activeStage()]);return;}
   let count=s.side==='hvdc'?runtimeSchedule.length:12;
   if(!count)return;
   const id=LCC.mod(s.id-1+v,count)+1;
   goto(iMap[s.side]+id-1);
 }
 function selectStage(stage){pause();goto(stage==='fundamentals'?deck.findIndex(s=>s.side==='fundamentals'&&s.type==='chapter'):chapterIndex[stage]);}
 function diagramSource(s,active){
   if(s.side==='hvdc')return DATA.diagrams.hvdc[`${active.r}:${active.i}`]||null;
   return DATA.diagrams[s.side][String(s.id)]||null;
 }
 function referenceSource(s){
   const refs=DATA.references[s.side];return refs?refs[String(s.id)]:null;
 }
 function shortName(side){return side==='rectifier'?'RECTIFIER':side==='inverter'?'INVERTER':'HVDC LINK';}
 function renderCircuit(s,active){
   const src=diagramSource(s,active),key=s.side+':'+(s.side==='hvdc'?active.r+':'+active.i:s.id);
   if(!src){$('circuit-host').innerHTML='<div class="empty-msg">No matching circuit state in the source gallery.</div>';return;}
   if(key===cachedKey)return;
   cachedKey=key;
   $('circuit-host').innerHTML=src;
   let svg=$('circuit-host').querySelector('svg');
   if(svg){svg.setAttribute('role','img');svg.setAttribute('aria-label',`${shortName(s.side)} conduction state ${s.id}`);}
 }
 function applyTransfer(){
   const s=current();if(s.type!=='state')return;
   const host=$('circuit-host');if(!host)return;
   const stations=s.side==='hvdc'?[['rectifier','r',0],['inverter','i',LCC.OFFSET]]:[[s.side,'',0]];
   const transferNotes=[];
   for(const [side,prefix,offset] of stations){
     const state=LCC.at(theta,side==='rectifier'?params.muR:params.muI,offset);
     if(!state.overlap)continue;
     const info=LCC.stateInfo(state.id),pct=Math.round(state.transfer*100);
     transferNotes.push(`${prefix?prefix.toUpperCase()+': ':''}${info.outgoing} → ${info.incoming} · ${pct}% transferred`);
     for(const [scr,weight] of [[info.outgoing,1-state.transfer],[info.incoming,state.transfer]]){
       const id=prefix?`scr-${prefix}_${scr.toLowerCase()}`:`selected-${scr.toLowerCase()}`;
       const el=host.querySelector('[id="'+id+'"]');if(el)el.style.opacity=String(.22+.78*weight);
     }
   }
   const text=$('angle-status');if(text)text.innerHTML=MathUI.angle('θ',theta)+(transferNotes.length?' · '+transferNotes.join(' | '):' · Normal conduction');
 }
 function renderPlots(){
   const s=current();if(s.type!=='state')return;
   const canvas=$('plot-canvas'),reference=$('reference-view');
   const src=referenceSource(s);
   canvas.hidden=showReference;reference.hidden=!showReference;
   $('reference-banner').hidden=!showReference;
   if(showReference){
     const key=s.side+':'+s.id;if(reference.dataset.key!==key){reference.innerHTML=src||'<p>No reference available</p>';reference.dataset.key=key;}
   }else{
     ChartView.render(canvas,s.side,params,liveWindow(),liveActive(),theta,mode,selectedSCR);
   }
 }
 function facts(s,a){
   let scr='',gamma=`${(180-params.alphaI-params.muI).toFixed(1)}°`;
   if(s.side==='hvdc'){
     const r=LCC.stateInfo(a.r),i=LCC.stateInfo(a.i);
     scr=`R: ${r.scrs.join(' / ')} | I: ${i.scrs.join(' / ')}`;
   }else scr=LCC.stateInfo(a.id).scrs.join(' / ');
   return `<div class="fact"><small>Conducting SCRs</small><strong style="font-size:13px">${scr}</strong></div><div class="fact"><small>Commutation / extinction</small><strong>μ=${s.side==='rectifier'?params.muR:params.muI}° · γ=${gamma}</strong></div>`;
 }
 function stateDetails(s){
   const a=liveActive(s);const w=liveWindow(s);
   const type=(s.side==='hvdc')?(a.rOverlap&&a.iOverlap?'Both stations in overlap':a.rOverlap?'Rectifier overlap':a.iOverlap?'Inverter overlap':'Normal at both stations'):(s.id%2===0?'Commutation overlap':s.side==='rectifier'?'Normal conduction with RL load':'Normal conduction');
   const overlap=type.toLowerCase().includes('overlap');
   const desc=s.side==='hvdc'?LCC.jointDescription(a):LCC.describe(s.side,s.id);
   const sub=s.side==='hvdc'?`Rectifier ${String(a.r).padStart(2,'0')} · Inverter ${String(a.i).padStart(2,'0')} · ${w.map(([lo,hi])=>`${lo.toFixed(1)}–${hi.toFixed(1)}°`).join(', ')}`
    :`Valves ${LCC.stateInfo(s.id).scrs.join(' + ')} · ${w.map(([lo,hi])=>`${lo.toFixed(1)}–${hi.toFixed(1)}°`).join(', ')}`;
   return {a,type,overlap,desc,sub};
 }
 // Update state-specific content without rebuilding the angle range input.
 // Replacing the input during its input event causes the browser to lose drag capture.
 function refreshStateInPlace(){
   const s=current();
   if(s.type!=='state'||!$('angle-range'))return;
   const {a,type,overlap,desc,sub}=stateDetails(s);
   const root=$('slide');
   root.querySelector('.tech-index').textContent=(s.side==='rectifier'?'01':s.side==='inverter'?'02':'03')+' · '+String(s.id).padStart(2,'0');
   root.querySelector('.tech-title h1').textContent=shortName(s.side)+' · '+type;
   root.querySelector('.tech-title p').textContent=sub;
   const badge=root.querySelector('.mode-badge');
   badge.className='mode-badge '+(overlap?'overlap':s.side==='hvdc'?'joint':'');
   badge.textContent=overlap?'OVERLAP':'NORMAL';
   root.querySelector('.explainer').innerHTML=desc;
   $('facts').innerHTML=facts(s,a);
   // The same range DOM element must survive all state transitions.
   $('angle-range').value=String(theta);
   renderCircuit(s,a);
   applyTransfer();
   renderPlots();
   updateSlideChrome();
 }
 let stateAngleFrame=0;
 function scheduleStateAngleRefresh(){
   if(stateAngleFrame)return;
   stateAngleFrame=requestAnimationFrame(()=>{
     stateAngleFrame=0;
     if(current().type!=='state')return;
     syncSlideFromAngle();
     refreshStateInPlace();
   });
 }
 function renderState(s){
   const {a,type,overlap,desc,sub}=stateDetails(s);
   const inner=`<div class="tech-head"><div class="tech-index">${s.side==='rectifier'?'01':s.side==='inverter'?'02':'03'} · ${String(s.id).padStart(2,'0')}</div><div class="tech-title"><h1>${shortName(s.side)} · ${type}</h1><p>${sub}</p></div><div class="mode-badge ${overlap?'overlap':s.side==='hvdc'?'joint':''}">${overlap?'OVERLAP':'NORMAL'}</div></div>
     <div class="workspace"><section class="panel"><div class="panel-head"><strong>01 / CIRCUIT & CONDUCTION PATH</strong><div class="panel-actions"><button class="soft-btn" id="zoom-btn" aria-label="Enlarge diagram">⤢ ENLARGE</button></div></div><div class="diagram-area" id="circuit-host"><span class="empty-msg">Loading vector circuit…</span><span class="diagram-tip">SVG · editable source in GitHub</span></div></section>
     <section class="panel"><div class="panel-head"><strong>02 / CONCEPTUAL WAVEFORMS</strong><div class="panel-actions"><select class="soft-btn" id="chart-mode" aria-label="Choose signals"><option value="overview">Overview</option><option value="phase">Phase voltages</option><option value="line">Line voltages</option><option value="scr">SCR currents</option><option value="vak">SCR voltages</option><option value="valvePair">SCR voltage &amp; current</option><option value="dc">DC quantities</option></select><label class="mini-select" title="Select SCR for current and voltage">SCR <select class="soft-btn" id="scr-filter">${['all',...LCC.SCRS].map(t=>`<option value="${t}">${t==='all'?'All SCRs':t}</option>`).join('')}</select></label><button class="soft-btn ${showReference?'active':''}" id="ref-btn">${showReference?'LIVE MODEL':'SOURCE SVG'}</button></div></div><div class="plot-wrapper" id="plot-wrapper"><canvas id="plot-canvas" aria-label="Interactive LCC voltage and current plots"></canvas><div class="reference" id="reference-view" hidden></div><span class="reference-banner" id="reference-banner" hidden>Reference SVG: nominal parameters, not updated by sliders</span></div></section></div>
     <div class="tech-note" id="explain-row" ${showExplanation?'':'hidden'}><div class="explainer">${desc}</div><div class="fact-grid" id="facts">${facts(s,a)}</div></div>
     <div class="timeline"><div class="timeline-top"><span class="timeline-status" id="angle-status">θ = ${theta.toFixed(1)}° · ${type}</span><div class="timeline-actions"><button id="step-prev" title="Previous conduction state">◀ STATE</button><button class="primary" id="play-btn">${playing?'❚❚ PAUSE':'▶ PLAY'}</button><button id="step-next" title="Next conduction state">STATE ▶</button></div></div><input class="angle-range" id="angle-range" type="range" min="0" max="359.75" step="0.01" value="${theta}" aria-label="Electrical angle in degrees"><div class="ticks"><span>0°</span><span>60°</span><span>120°</span><span>180°</span><span>240°</span><span>300°</span><span>360°</span></div></div>`;
   $('slide').className='slide technical';$('slide').innerHTML=inner;cachedKey='';
   $('chart-mode').value=mode;
   $('scr-filter').value=selectedSCR;
   $('scr-filter').addEventListener('change',e=>{selectedSCR=e.target.value;renderPlots();});
   $('chart-mode').addEventListener('change',e=>{mode=e.target.value;renderPlots();});
   $('ref-btn').onclick=()=>{showReference=!showReference;const b=$('ref-btn');b.textContent=showReference?'LIVE MODEL':'SOURCE SVG';b.classList.toggle('active',showReference);renderPlots();};
   $('step-prev').onclick=()=>stepState(-1);$('step-next').onclick=()=>stepState(1);
   $('play-btn').onclick=()=>togglePlay();
   $('angle-range').oninput=e=>{pause();setTheta(+e.currentTarget.value);scheduleStateAngleRefresh();};
   $('zoom-btn').onclick=()=>openZoom();
   $('plot-canvas').addEventListener('click',ev=>{
      const rect=ev.currentTarget.getBoundingClientRect(),left=38,right=rect.width-15;
      const local=ev.clientX-rect.left;const pos=(local-left)/(right-left);
      if(pos>=0&&pos<=1){pause();setTheta(Math.min(359.75,360*pos));$('angle-range').value=String(theta);scheduleStateAngleRefresh();}
   });
   renderCircuit(s,a);
   applyTransfer();
   renderPlots();
 }
 function renderLoadDetails(){
   if(current().type!=='load')return;
   const s=current(),compare=s.lesson==='r_compare',compareAll=s.lesson==='advanced_compare',which=compare||compareAll?'R':params.loadMode;
   const a=LoadModel.at(LoadCharts.model('R',params),theta),b=LoadModel.at(LoadCharts.model('RL',params),theta);
   const allStates=Object.fromEntries(['R','RL','LE','RLE'].map(m=>[m,LoadModel.at(LoadCharts.model(m,params),theta)]));
   const state=allStates[which];
   const key=compare?'compare:'+a.pair+':'+b.pair:compareAll?'compareAll:'+Object.values(allStates).map(a=>a.pair).join(':'):which+':'+state.pair;
   if(cachedKey!==key){
     const host=$('circuit-host');
     if(compare||compareAll){
       if(compareAll){host.innerHTML='<div class="quad-circuit">'+['R','RL','LE','RLE'].map(m=>'<div><div class="circuit-tag">'+m+' LOAD</div>'+(DATA.load_figures[m+':'+allStates[m].pair]||'')+'</div>').join('')+'</div>'; }
       else host.innerHTML='<div class="dual-circuit"><div><div class="circuit-tag">PURE R</div>'+(DATA.load_figures['R:'+a.pair]||'')+'</div><div><div class="circuit-tag">R + L</div>'+(DATA.load_figures['RL:'+b.pair]||'')+'</div></div>';
     }else host.innerHTML=DATA.load_figures[key]||'<div class="empty-msg">Circuit state unavailable</div>';
     cachedKey=key;
   }
   const show=s.lesson==='r_case'?'R load · alpha '+s.alpha+'°':s.lesson==='r_intro'?'Pure R introductory circuit':compare?'R versus RL':compareAll?'R/RL/LE/RLE comparison':which+' load';
   const conduction=state.pair<0?'ALL SCRs OFF':state.scrs.join(' + ');
   const label=compare?'R: '+(a.scrs.join('+')||'OFF')+' | RL: '+(b.scrs.join('+')||'OFF'):compareAll?'R, RL, LE, RLE · same firing angle':conduction;
   $('angle-status').innerHTML=MathUI.angle('θ',theta)+' · '+label;
   $('load-active').textContent=label;
   $('load-dc').innerHTML=compare?`R: ${a.dcCurrent.toFixed(2)} · RL: ${b.dcCurrent.toFixed(2)} ${MathUI.unit('p.u.')}`:compareAll?`Four DC load models`:state.dcCurrent.toFixed(2)+' '+MathUI.unit('p.u.');
   const details=compare?'At equal firing angle, R current follows voltage and RL inductance smooths current.':
     compareAll?'Compare pure R, damped RL, opposing DC source LE, and RLE. AC commutation inductance is distinct from the DC smoothing inductance.':
     which==='LE'?'LE is an initial-value trajectory: the source E opposes rectified voltage. With zero R there is no unique settled DC current; zero net inductor volt-seconds is required for periodic operation.':
     which==='RLE'?'RLE is a simplified HVDC equivalent. The rectifier voltage overcomes the opposing inverter-equivalent E; the R term dissipates energy and the L term controls current dynamics.':
     which==='R'?(state.pair<0?'All SCRs are blocking. No current flows through the resistor.':'A fired valve pair supplies the resistor. Current follows voltage immediately, with no stored magnetic energy.'):
     state.pair<0?'The RL current extinguished and waits for the next valid firing event.':'The DC reactor stores magnetic energy. Current can remain positive while the instantaneous DC voltage becomes negative.';
   $('load-explanation').innerHTML=details+' <span class="load-equation">'+(compare||compareAll?'':MathUI.formula(which))+'</span>';
   const floating=which==='R'||which==='RL'||which==='LE'||which==='RLE';
   const uncertainty=$('floating-note');if(uncertainty)uncertainty.hidden=!(state.pair<0&&floating&&!compare&&!compareAll&&['vak','valvePair'].includes($('load-chart-mode')?.value));
   const choice=$('load-choice');if(choice&&choice.value!==params.loadMode)choice.value=params.loadMode;
   LoadCharts.render($('load-plots'),compare?'compare':compareAll?'compareAll':which,params,theta,$('load-chart-mode')?.value||'overview',selectedSCR);
 }
 function renderLoadSlide(s){
   const isCompare=s.lesson==='r_compare',isAll=s.lesson==='advanced_compare';
   const which=({r_intro:'R',r_case:'R',rl_intro:'RL',le_intro:'LE',rle_intro:'RLE'}[s.lesson]||'R');
   const title=isAll?'RECTIFIER · R / RL / LE / RLE comparison':isCompare?'RECTIFIER · Comparing R and RL loads':
     s.lesson==='r_case'?`RECTIFIER · R load · firing angle ${s.alpha}°`:`RECTIFIER · ${which} load and DC current dynamics`;
   const subtitle=isAll?'The opposing DC source E introduces an inverter equivalent. RL smoothing and AC commutation overlap are separate phenomena.':
     isCompare?'Same AC source and firing angle, different DC inductance.':
     which==='LE'?'Lossless reactor and opposing DC voltage E: initial value, not an imposed steady state.':
     which==='RLE'?'Simplified DC link: opposing inverter voltage E, DC resistance R, smoothing inductance L.':
     which==='R'?'Observe firing delay and blocked intervals with no inductive energy storage.':'Energy storage permits conduction through temporarily negative DC voltage.';
   const choice='<label class="mini-select">LOAD <select class="soft-btn" id="load-choice">'+['R','RL','LE','RLE'].map(m=>`<option value="${m}">${m}</option>`).join('')+'</select></label>';
   const selectOptions='<option value="overview">Overview</option><option value="phase">Phase voltages</option><option value="line">Line voltages</option><option value="scr">SCR currents</option><option value="vak">SCR voltages</option><option value="valvePair">SCR voltage &amp; current</option><option value="dc">DC quantities</option>';
   const content=`<div class="tech-head"><div class="tech-index">01 · LOAD STUDY</div><div class="tech-title"><h1>${title}</h1><p>${subtitle}</p></div><div class="mode-badge ${isCompare||isAll?'joint':''}">${isCompare||isAll?'COMPARISON':MathUI.v('μ')+' = '+MathUI.num('0')+MathUI.unit('°')}</div></div>
   <div class="workspace load-workspace"><section class="panel"><div class="panel-head"><strong>01 / ELECTRICAL CIRCUIT</strong><div class="panel-actions">${isCompare||isAll?'<span class="soft-btn">LOAD COMPARISON</span>':choice}</div></div><div class="diagram-area load-diagram" id="circuit-host"></div></section>
   <section class="panel"><div class="panel-head"><strong>02 / ANALYTICAL WAVEFORMS</strong><div class="panel-actions"><select class="soft-btn" id="load-chart-mode" aria-label="Choose plotted quantities">${selectOptions}</select><label class="mini-select">SCR <select class="soft-btn" id="scr-filter">${['all',...LCC.SCRS].map(t=>`<option value="${t}">${t==='all'?'All SCRs':t}</option>`).join('')}</select></label></div></div><div class="plot-wrapper"><canvas id="load-plots" aria-label="Four DC load models and six SCR voltages"></canvas></div></section></div>
   <div class="tech-note"><div class="explainer" id="load-explanation"></div><div class="fact-grid"><div class="fact"><small>Conducting devices</small><strong id="load-active" style="font-size:12px;font-style:normal"></strong></div><div class="fact"><small>DC current</small><strong id="load-dc"></strong></div></div></div>
   <div class="floating-note" id="floating-note" hidden>Individual SCR voltage is undefined while both DC bus potentials float; no fictitious blocking-voltage trace is generated.</div>
   <div class="timeline"><div class="timeline-top"><span class="timeline-status" id="angle-status">${MathUI.angle('θ',theta)}</span><div class="timeline-actions"><button id="load-settings">⚙ PARAMETERS</button><button class="primary" id="play-btn">${playing?'❚❚ PAUSE':'▶ PLAY'}</button></div></div><input class="angle-range" id="angle-range" type="range" min="0" max="359.99" step="0.01" value="${theta}" aria-label="Electrical angle in degrees"><div class="ticks"><span>0°</span><span>60°</span><span>120°</span><span>180°</span><span>240°</span><span>300°</span><span>360°</span></div></div>`;
   $('slide').className='slide technical';$('slide').innerHTML=content;cachedKey='';
   if(!isCompare&&!isAll){$('load-choice').value=params.loadMode;$('load-choice').onchange=e=>{params.loadMode=e.target.value;cachedKey='';renderLoadDetails();};}
   $('load-chart-mode').onchange=()=>renderLoadDetails();
   $('scr-filter').value=selectedSCR;$('scr-filter').onchange=e=>{selectedSCR=e.target.value;renderLoadDetails();};
   $('load-settings').onclick=()=>switchOverlay('settings-overlay',true);
   $('play-btn').onclick=()=>togglePlay();
   $('angle-range').oninput=e=>{pause(false);setTheta(+e.target.value);renderLoadDetails();};
   $('load-plots').addEventListener('click',e=>{let rect=e.currentTarget.getBoundingClientRect();let pos=(e.clientX-rect.left-38)/(rect.width-53);if(pos>=0&&pos<=1){pause(false);setTheta(Math.min(359.75,360*pos));$('angle-range').value=theta;renderLoadDetails();}});
   renderLoadDetails();
 }

 function fundamentalsDetails(s){
   const data={
    scr_intro:['What Is a Thyristor?','Three terminals: anode, cathode and gate. The gate initiates forward conduction.'],
    r_circuit:['Half-Wave Rectifier with R Load','Current follows the source voltage immediately after firing.'],
    r_delay:['R Load · Effect of Firing Angle','Move the firing delay and observe the shrinking conduction interval.'],
    rl_circuit:['Half-Wave Rectifier with RL Load','An inductor stores energy and slows the change in current.'],
    after180:['Why Does the SCR Remain ON After 180°?','The source voltage reverses at 180°, but the current stays positive until extinction.'],
    extinction:['Natural Current Extinction','The dynamically calculated angle β marks the first zero of SCR current.'],
    compare:['R versus RL · Same Source, Different Current','Compare a resistive current and a delayed inductive current with fixed axes.'],
    commutation:['Natural Extinction versus Line Commutation','Current extinction in one SCR differs from transferring current between valves.']
   };
   return data[s.lesson]||['Thyristor Fundamentals','Single-phase SCR operation'];
 }
 function fundamentalsMessage(s,rl,r,point){
   const beta=rl.beta.toFixed(1);
   switch(s.lesson){
    case 'scr_intro':return 'An SCR conducts only after a valid gate pulse under forward bias. Removing the gate signal does not turn an ordinary SCR off.';
    case 'r_circuit':return `${MathUI.v('i','T')} = ${MathUI.v('v','s')} / ${MathUI.v('R')} during conduction. With pure R, current naturally falls to zero at ${MathUI.num('180')}${MathUI.unit('°')}.`;
    case 'r_delay':return `Increasing ${MathUI.v('α')} delays turn-on. For R, the SCR stops at ${MathUI.num('180')}${MathUI.unit('°')}; the gate cannot keep it conducting in reverse bias.`;
    case 'rl_circuit':return `${MathUI.v('L')}d${MathUI.v('i','T')}/d${MathUI.v('t')}+${MathUI.v('R')}${MathUI.v('i','T')}=${MathUI.v('v','s')}. The inductor stores ${MathUI.num('½')}${MathUI.v('L')}${MathUI.v('i','T')}² and current can extend beyond the source zero crossing.`;
    case 'after180':return (theta>=180&&theta<rl.beta)?
       `Between the fixed ${MathUI.num('180')}${MathUI.unit('°')} marker and ${MathUI.v('β')} = ${MathUI.num(beta)}${MathUI.unit('°')}, source voltage is negative while SCR current remains positive. The inductor releases stored energy.`:
       `Watch the interval from ${MathUI.num('180')}${MathUI.unit('°')} to the movable extinction marker ${MathUI.v('β')} = ${MathUI.num(beta)}${MathUI.unit('°')}. Move the cursor inside the shaded region.`;
    case 'extinction':return `The model finds ${MathUI.v('β')} = ${MathUI.num(beta)}${MathUI.unit('°')} by solving the RL equation. Current reaches zero naturally; the SCR then blocks. Real SCRs additionally require a holding-current and recovery margin.`;
    case 'compare':return `At the same firing angle, R has extinction at ${MathUI.num('180')}${MathUI.unit('°')}; RL extinguishes at ${MathUI.v('β')} = ${MathUI.num(beta)}${MathUI.unit('°')}. The comparison uses the same axes and source amplitude.`;
    case 'commutation':return `Here the SCR stops when its current reaches zero at ${MathUI.v('β')}. In a three-phase LCC, the next valve turns on and current transfers between phases during ${MathUI.v('μ')}; these are different phenomena.`;
   }
 }
 function renderFundamentalsDetails(){
   const s=current();if(s.type!=='fundamentals'||!$('fund-circuit-host'))return;
   const rl=HalfWave.get(params,'RL'),r=HalfWave.get(params,'R');
   const load=['scr_intro','r_circuit','r_delay'].includes(s.lesson)?'R':'RL';
   const m=load==='R'?r:rl,point=m.at(theta),on=point.on;
   const activeKey=s.lesson==='compare'?`compare:${r.at(theta).on}:${rl.at(theta).on}`:`${load}:${on}`;
   if(cachedKey!==activeKey){
     const asset=DATA.halfwave_figures;
     const src=label=>asset[label]||'<p>Missing SVG circuit</p>';
     $('fund-circuit-host').innerHTML=s.lesson==='compare'?
       `<div class="fund-dual"><div><span class="fund-tag">R LOAD</span>${src(`R:${r.at(theta).on?'on':'off'}`)}</div><div><span class="fund-tag">RL LOAD</span>${src(`RL:${rl.at(theta).on?'on':'off'}`)}</div></div>`:
       src(`${load}:${on?'on':'off'}`);
     cachedKey=activeKey;
   }
   const betaTxt=rl.beta.toFixed(1);
   $('fund-beta').innerHTML=MathUI.angle('β',load==='R'?180:rl.beta);
   $('fund-state').textContent=s.lesson==='compare'?`R: ${r.at(theta).on?'ON':'OFF'} · RL: ${rl.at(theta).on?'ON':'OFF'}`:on?'T1 conducting':'T1 blocking';
   $('fund-i').innerHTML=MathUI.angle('θ',theta)+' · '+MathUI.num(point.i.toFixed(2))+MathUI.unit(' A');
   $('fund-description').innerHTML=fundamentalsMessage(s,rl,r,point);
   $('fund-angle-status').innerHTML=MathUI.angle('θ',theta)+' · '+MathUI.angle('α',params.hAlpha)+' · '+MathUI.angle('β',rl.beta);
   const marker=$('fund-marker-status');if(marker)marker.innerHTML=(s.lesson==='after180'||s.lesson==='extinction')?
     `${MathUI.num('180')}${MathUI.unit('°')} fixed source zero · ${MathUI.v('β')} = ${MathUI.num(betaTxt)}${MathUI.unit('°')} (RL turn-off)`:
     `Conduction highlighted · ${MathUI.v('α')} = ${MathUI.num(params.hAlpha.toFixed(1))}${MathUI.unit('°')}`;
   const range=$('fund-angle');if(range)range.value=String(theta);
   for(const name of ['hAlpha','hR','hL','hV']){
     const el=$(name+'-fund'),out=$(name+'-fund-value');
     if(out)out.textContent=params[name].toFixed(name==='hL'?1:1)+({hAlpha:'°',hR:' Ω',hL:' mH',hV:' V'}[name]);
     if(el&&document.activeElement!==el)el.value=params[name];
   }
   HalfWave.render($('fund-waveforms'),params,theta,s.lesson,$('fund-mode').value);
 }
 function renderFundamentalsSlide(s){
   const [title,subtitle]=fundamentalsDetails(s);
   const controls=[['hAlpha',0,175,.1,'α','°'],['hR',2,45,.1,'R','Ω'],
                   ['hL',.5,140,.1,'L','mH'],['hV',40,260,.5,'V','V']];
   $('slide').className='slide technical fundamentals-slide';
   $('slide').innerHTML=`<div class="tech-head"><div class="tech-index">00 · FUNDAMENTALS</div><div class="tech-title"><h1>${title}</h1><p>${subtitle}</p></div><div class="mode-badge" id="fund-state">SCR</div></div>
    <div class="workspace fund-workspace"><section class="panel"><div class="panel-head"><strong>01 / HALF-WAVE SCR CIRCUIT</strong><div class="panel-actions"><span class="soft-btn" id="fund-beta">β</span></div></div><div class="diagram-area fund-diagram" id="fund-circuit-host"></div></section>
    <section class="panel"><div class="panel-head"><strong>02 / SYNCHRONIZED WAVEFORMS</strong><select class="soft-btn" id="fund-mode"><option value="overview">Overview</option><option value="voltages">Component voltages</option><option value="vak">SCR voltage & current</option><option value="energy">Inductor energy</option></select></div><div class="plot-wrapper"><canvas id="fund-waveforms" aria-label="Half-wave SCR waveforms with adjustable alpha, fixed 180 degree marker and moving beta marker"></canvas></div></section></div>
    <div class="fund-controlbar">${controls.map(([name,lo,hi,step,label,unit])=>`<label class="fund-tuner"><span>${MathUI.v(label)} <output id="${name}-fund-value">${params[name].toFixed(1)} ${unit}</output></span><input id="${name}-fund" type="range" min="${lo}" max="${hi}" step="${step}" value="${params[name]}"></label>`).join('')}</div>
    <div class="tech-note fund-note"><div class="explainer" id="fund-description"></div><div class="fact-grid"><div class="fact"><small>Instantaneous current</small><strong id="fund-i"></strong></div><div class="fact"><small>Reference markers</small><strong id="fund-marker-status"></strong></div></div></div>
    <div class="timeline"><div class="timeline-top"><span class="timeline-status" id="fund-angle-status"></span><div class="timeline-actions"><button id="fund-step-180">θ = 180°</button><button id="fund-step-beta">θ = β − 5°</button><button class="primary" id="play-btn">▶ PLAY</button></div></div><input class="angle-range" type="range" id="fund-angle" min="0" max="359.99" step="0.01" value="${theta}" aria-label="Electrical angle in degrees"><div class="ticks"><span>0°</span><span>60°</span><span>120°</span><span>180°</span><span>240°</span><span>300°</span><span>360°</span></div></div>`;
   cachedKey='';
   $('fund-mode').onchange=renderFundamentalsDetails;
   for(const name of ['hAlpha','hR','hL','hV']){
      $(name+'-fund').oninput=e=>{params[name]=+e.currentTarget.value;renderFundamentalsDetails();};
   }
   $('fund-angle').oninput=e=>{pause(false);setTheta(+e.currentTarget.value);renderFundamentalsDetails();};
   $('fund-step-180').onclick=()=>{pause(false);setTheta(180);renderFundamentalsDetails();};
   $('fund-step-beta').onclick=()=>{pause(false);setTheta(Math.max(0,HalfWave.get(params,'RL').beta-5));renderFundamentalsDetails();};
   $('play-btn').onclick=()=>togglePlay();
   $('fund-waveforms').onclick=e=>{const rect=e.currentTarget.getBoundingClientRect();let angle=360*(e.clientX-rect.left-43)/(rect.width-56);if(angle>=0&&angle<360){pause(false);setTheta(angle);renderFundamentalsDetails();}};
   renderFundamentalsDetails();
 }
 function renderHero(s){
   let title='',subtitle='',kicker='',stats='',extra='';
   if(s.type==='title'){
    kicker='POWER SYSTEMS · INTERACTIVE LEARNING';title='HVDC LCC<br>Current paths & commutation';
    subtitle='Begin with R, RL, LE and RLE loads. Then explore 48 SCR conduction states, natural commutation and a complete HVDC link, all in one offline lecture.';
    stats=[['04','Chapters'],['48','Reference states'],['360°','Continuous cycle'],['100%','Offline']];
   }else if(s.type==='roadmap'){
    kicker='THE LEARNING PATH';title='One concept<br>at a time.';
    subtitle='Begin with one SCR and a simple half-wave R/RL circuit. Discover natural extinction at β before learning the six-pulse rectifier, inverter and complete HVDC link.';
    stats=[['00','Fundamentals'],['01','Rectifier'],['02','Inverter'],['03','HVDC link']];
   }else if(s.type==='end'){
    kicker='END OF PRESENTATION';title='Explore further.';
    subtitle='Change the firing delay, overlap and DC current. Revisit individual SCR currents and compare them with the original editable vector illustrations.';
    stats=[['48','Circuit states'],['±','Polarity matters'],['μ','Current transfer'],['γ','Extinction margin']];
   }else{
    const chapter={fundamentals:['00 / THYRISTOR FUNDAMENTALS','How does an SCR turn off?','One SCR, one sinusoidal source and R/RL loads reveal the difference between voltage reversal and current extinction.','GATE → EXTINCTION'],rectifier:['01 / RECTIFIER','AC to DC','Follow one upper and one lower SCR through six normal states and six commutation overlaps.','CA → CC'],inverter:['02 / INVERTER','DC to AC','Trace the reversed energy flow, extinction margin and six SCR current transfers.','CC → CA'],hvdc:['03 / COMPLETE HVDC','Connect the two stations','Follow the pole current through both converters, smoothing reactors and metallic return.','HVDC LINK']}[s.side];
    kicker=chapter[0];title=chapter[1];subtitle=chapter[2];stats=[['12',s.side==='hvdc'?'Joint states (24)':'Conduction states'],['6','Commutation events'],['1','Full cycle'],[chapter[3],'Power flow']];
    if(s.side==='hvdc')stats[0]=['24','Joint states'];
    if(s.side==='fundamentals')stats=[['01','Single SCR'],['02','R and RL'],['180°','Voltage reversal'],['β','Current extinction']];
   }
   let blocks=stats.map(([n,label])=>`<div class="hero-stat"><strong>${n}</strong><span>${label}</span></div>`).join('');
   $('slide').className='slide';$('slide').innerHTML=`<section class="presentation-hero ${s.type==='chapter'?'chapter-hero':''}">${s.type==='chapter'?'<span class="chapter-index">'+(s.side==='rectifier'?'01':s.side==='inverter'?'02':'03')+'</span>':''}<div class="hero-kicker">${kicker}</div><h1 class="hero-title">${title}</h1><p class="hero-sub">${subtitle}</p><div class="hero-bottom">${blocks}</div><div class="hero-cta">Use <span class="keycap">←</span><span class="keycap">→</span> to navigate · <span class="keycap">O</span> for slide overview · <span class="keycap">F</span> for full screen</div></section>`;
 }
 function updateSlideChrome(){
   const s=current();
   $('page-counter').textContent=`${slideIndex+1} / ${deck.length}`;
   $('progress-fill').style.width=`${((slideIndex+1)/deck.length*100).toFixed(2)}%`;
   $('nav-fund').classList.toggle('active',s.side==='fundamentals');$('nav-rect').classList.toggle('active',s.side==='rectifier');$('nav-inv').classList.toggle('active',s.side==='inverter');$('nav-hvdc').classList.toggle('active',s.side==='hvdc');
   $('footer-prev').disabled=slideIndex===0;$('footer-next').disabled=slideIndex===deck.length-1;
   $('current-chapter').textContent=s.side==='fundamentals'?'CH 00 · THYRISTOR FUNDAMENTALS':s.side==='rectifier'?'CH 01 · RECTIFIER':s.side==='inverter'?'CH 02 · INVERTER':s.side==='hvdc'?'CH 03 · HVDC LINK':'HVDC LCC LEARNING LAB';
   $('settings-gamma').textContent=(180-params.alphaI-params.muI).toFixed(1)+'°';
 }
 function render(){
   updateSchedule();const s=current();
   if(s.type==='state')renderState(s);else if(s.type==='load')renderLoadSlide(s);else if(s.type==='fundamentals')renderFundamentalsSlide(s);else renderHero(s);
   updateSlideChrome();
 }
 function togglePlay(){if(playing){pause();return;}
   if(!['state','load','fundamentals'].includes(current().type)){goto(iMap[activeStage()]??deck.findIndex(s=>s.type==='fundamentals'));}
   playing=true;lastTick=0;render();raf=requestAnimationFrame(tick);
 }
 function pause(redraw=true){playing=false;if(raf)cancelAnimationFrame(raf);raf=0;lastTick=0;if(redraw&&current().type==='state'&&$('play-btn'))$('play-btn').textContent='▶ PLAY';}
 function tick(t){if(!playing)return;if(lastTick){const old=slideIndex;setTheta(theta+(t-lastTick)*params.speed/1000);if(current().type==='fundamentals'){renderFundamentalsDetails();}else if(current().type==='load'){const slider=$('angle-range');if(slider)slider.value=String(theta);renderLoadDetails();}else{syncSlideFromAngle();if(old!==slideIndex){render();}else{const slider=$('angle-range');if(slider)slider.value=String(theta);applyTransfer();renderPlots();}}}lastTick=t;raf=requestAnimationFrame(tick);}
 function updateParam(name,value){
   params[name]=+value;
   if(name==='alphaLoad')params.alphaLoad=Math.max(0,Math.min(119,params.alphaLoad));
   params.alphaI=Math.max(105,Math.min(169,params.alphaI));
   params.muI=Math.max(1,Math.min(50,params.muI));
   if(params.muI+params.alphaI>170){
     if(name==='muI')params.alphaI=170-params.muI;
     else params.muI=170-params.alphaI;
   }
   for(const key of Object.keys(params))if($(key+'-range')){
     $(key+'-range').value=params[key];
     $(key+'-value').textContent=Number(params[key]).toFixed(2)+(key.startsWith('alpha')||key.startsWith('mu')||key==='hAlpha'?'°':key==='loadL'||key==='hL'?' mH':key==='loadR'||key==='hR'?' Ω':key==='hV'?' V':key==='speed'?' °/s':' p.u.');
   }
   updateSchedule();if(current().type==='state'){syncSlideFromAngle();}cachedKey='';if(current().type==='fundamentals')renderFundamentalsDetails();else render();
 }
 function setupSettings(){
   const names=[['hAlpha',0,175,.1,'Half-wave firing angle '+MathUI.v('α')],['hR',2,45,.1,'Half-wave resistance '+MathUI.v('R')],['hL',.5,140,.1,'Half-wave inductance '+MathUI.v('L')],['hV',40,260,.5,'Half-wave source peak '+MathUI.v('V')],['alphaR',0,80,.1,'Rectifier firing delay '+MathUI.v('α','r')],['alphaI',105,169,.1,'Inverter firing delay '+MathUI.v('α','i')],['muR',1,50,.1,'Rectifier commutation overlap '+MathUI.v('μ','r')],['muI',1,50,.1,'Inverter commutation overlap '+MathUI.v('μ','i')],['alphaLoad',0,119,.1,'Introductory firing angle '+MathUI.v('α')],['loadR',.3,3,.1,'DC resistance '+MathUI.v('R')+' ('+MathUI.unit('Ω')+')'],['loadL',.1,25,.1,'Smoothing inductance '+MathUI.v('L')+' ('+MathUI.unit('mH')+')'],['loadE',0,1.8,.01,'Opposing source '+MathUI.v('E')+' ('+MathUI.unit('p.u.')+')'],['loadI0',0,2,.01,'Initial current '+MathUI.v('i','dc')+'('+MathUI.num('0')+')'],['idc',.2,2,.01,'Illustrative pole current '+MathUI.v('I','dc')],['vPeak',.2,2,.01,'AC peak voltage '+MathUI.v('V')],['speed',2,180,.1,'Animation speed']];
   $('settings-sliders').innerHTML=names.map(([n,lo,hi,step,label])=>`<div class="slider-row"><label for="${n}-range">${label}</label><output id="${n}-value"></output><input id="${n}-range" type="range" min="${lo}" max="${hi}" step="${step}" value="${params[n]}"></div>`).join('');
   let queued=false,lastInput=null;for(const [name] of names){$(name+'-range').addEventListener('input',e=>{lastInput=[name,e.target.value];if(!queued){queued=true;requestAnimationFrame(()=>{queued=false;if(lastInput)updateParam(lastInput[0],lastInput[1]);});}});}
   $('reset-btn').onclick=()=>{Object.assign(params,initial);updateParam('alphaR',initial.alphaR);};
   $('explain-btn').onclick=()=>{showExplanation=!showExplanation;$('explain-btn').textContent=showExplanation?'Hide explanations':'Show explanations';render();};
 }
 function switchOverlay(id,show){$(id).classList.toggle('open',show);$(id).setAttribute('aria-hidden',String(!show));}
 function openZoom(){if(!current()||current().type!=='state')return;const svg=$('circuit-host').querySelector('svg');if(!svg)return;
   $('zoom-content').innerHTML=svg.outerHTML;$('zoom-title').textContent=shortName(current().side)+' · STATE '+current().id;switchOverlay('zoom-overlay',true);
 }
 function overview(){pause();   const fundIntro='<div class="overview-section">00 · THYRISTOR FUNDAMENTALS</div><div class="overview-grid">'+deck.map((item,ix)=>item.type==='fundamentals'?'<button data-slide="'+ix+'">'+fundamentalsDetails(item)[0]+'</button>':'').join('')+'</div>';const intro='<div class="overview-section">RECTIFIER INTRODUCTION · R, RL, LE AND RLE</div><div class="overview-grid">'+deck.map((item,ix)=>(item.type==='load'?'<button data-slide="'+ix+'">'+(item.lesson==='r_case'?'R · '+item.alpha+'°':item.lesson==='r_intro'?'PURE R':item.lesson==='r_compare'?'R vs RL':item.lesson==='advanced_compare'?'ALL FOUR':item.lesson==='le_intro'?'LE LOAD':item.lesson==='rle_intro'?'RLE LOAD':'RL LOAD')+'</button>':'')).join('')+'</div>';
   const grids=stages.map(stage=>{
   const n=stage==='hvdc'?24:12;
   return `<div class="overview-section">${shortName(stage)} · ${n} states</div><div class="overview-grid">${Array.from({length:n},(_,k)=>{const ix=iMap[stage]+k,active=ix===slideIndex?'active':'';return `<button data-slide="${ix}" class="${active}">STATE ${String(k+1).padStart(2,'0')}<small>${stage==='hvdc'?'JOINT':(k%2?'OVERLAP':'NORMAL')}</small></button>`;}).join('')}</div>`;
 }).join('');
   $('overview-body').innerHTML=fundIntro+intro+grids;$('overview-body').querySelectorAll('[data-slide]').forEach(b=>b.addEventListener('click',()=>{switchOverlay('overview-overlay',false);goto(+b.dataset.slide); }));switchOverlay('overview-overlay',true);
 }
 function setup(){
   $('footer-prev').onclick=()=>navDelta(-1);$('footer-next').onclick=()=>navDelta(1);
   $('nav-fund').onclick=()=>selectStage('fundamentals');$('nav-rect').onclick=()=>selectStage('rectifier');$('nav-inv').onclick=()=>selectStage('inverter');$('nav-hvdc').onclick=()=>selectStage('hvdc');
   $('settings-open').onclick=()=>switchOverlay('settings-overlay',true);$('settings-close').onclick=()=>switchOverlay('settings-overlay',false);
   $('overview-open').onclick=overview;$('overview-close').onclick=()=>switchOverlay('overview-overlay',false);
   $('help-open').onclick=()=>switchOverlay('help-overlay',true);$('help-close').onclick=()=>switchOverlay('help-overlay',false);
   $('zoom-close').onclick=()=>switchOverlay('zoom-overlay',false);
   $('fullscreen-btn').onclick=()=>{if(!document.fullscreenElement)document.documentElement.requestFullscreen?.();else document.exitFullscreen?.();};
   $('close-zoom-layer').onclick=()=>switchOverlay('zoom-overlay',false);
   ['settings-overlay','overview-overlay','help-overlay'].forEach(id=>$(id).addEventListener('click',e=>{if(e.target===$(id))switchOverlay(id,false);}));
   document.addEventListener('keydown',e=>{
     if(e.target.matches('input,select,textarea'))return;
     if(e.key==='Escape'){['settings-overlay','overview-overlay','zoom-overlay','help-overlay'].forEach(id=>switchOverlay(id,false));return;}
     if(document.querySelector('.settings-overlay.open,.overview-overlay.open,.zoom-overlay.open,.help-overlay.open'))return;
     if(e.key==='ArrowRight'||e.key==='PageDown'||e.key===' '){e.preventDefault();navDelta(1);}else if(e.key==='ArrowLeft'||e.key==='PageUp'){e.preventDefault();navDelta(-1);}else if(e.key==='Home'){goto(0);}else if(e.key==='End'){goto(deck.length-1);}else if(e.key.toLowerCase()==='o'){overview();}else if(e.key.toLowerCase()==='f'){$('fullscreen-btn').click();}else if(e.key.toLowerCase()==='p'){togglePlay();}
   });
   window.addEventListener('resize',()=>{if(current().type==='state'&&!showReference)renderPlots();if(current().type==='load')renderLoadDetails();if(current().type==='fundamentals')renderFundamentalsDetails();});
   setupSettings();updateParam('alphaR',params.alphaR);goto(0);
   window.LCCPresentationTest={params,deck,getSlide:()=>current(),getIndex:()=>slideIndex,setSlide:i=>goto(i),setTheta:a=>{setTheta(a);syncSlideFromAngle();render();},at:LCC.at,sample:LCC.sample,halfWave:HalfWave.get,loadSample:LoadModel.sample,loadAt:LoadModel.at,schedule:()=>runtimeSchedule,reset:()=>Object.assign(params,initial)};
 }
 setup();
})();
