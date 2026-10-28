/* Offline 16:9 LCC lecture deck, including interactive state browsing. */
'use strict';
(() => {
 const DATA=JSON.parse(document.getElementById('presentation-data').textContent);
 const $=id=>document.getElementById(id);
 const params={alphaR:15,alphaI:145,muR:12,muI:15,idc:1,vPeak:1,speed:30};
 const initial={...params};
 let theta=65,slideIndex=0,playing=false,raf=0,lastTick=0,mode='overview',showReference=false,showExplanation=true;
 let cachedSVG='',cachedKey='',runtimeSchedule=[],deck=[];
 const stages=['rectifier','inverter','hvdc'];
 function slide(side,type,id=0){return {side,type,id};}
 deck=[slide('intro','title'),slide('intro','roadmap'),slide('rectifier','chapter')];
 for(let i=1;i<=12;i++)deck.push(slide('rectifier','state',i));
 deck.push(slide('inverter','chapter'));
 for(let i=1;i<=12;i++)deck.push(slide('inverter','state',i));
 deck.push(slide('hvdc','chapter'));
 for(let i=1;i<=24;i++)deck.push(slide('hvdc','state',i));
 deck.push(slide('end','end'));
 const iMap={rectifier:3,inverter:16,hvdc:29};
 const chapterIndex={rectifier:2,inverter:15,hvdc:28};
 function current(){return deck[slideIndex];}
 function activeStage(){return stages.includes(current().side)?current().side:'rectifier';}
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
   slideIndex=next;
   if(current().type==='state'&&!opts.keepAngle){
     const wins=liveWindow();if(wins.length)setTheta(startOfWindow(wins[0]));
   }
   cachedKey='';render();
 }
 function updateSchedule(){runtimeSchedule=LCC.jointSchedule(params.muR,params.muI,LCC.OFFSET);}
 function syncSlideFromAngle(){
   const s=current();if(s.type!=='state')return;
   if(s.side==='hvdc'){
     const i=runtimeSchedule.find(x=>x.window.some(w=>theta>=w[0]&&theta<w[1]));
     if(i)slideIndex=iMap.hvdc+i.id-1;
   }else{
     const state=LCC.at(theta,s.side==='rectifier'?params.muR:params.muI,0);
     slideIndex=iMap[s.side]+state.id-1;
   }
   cachedKey='';
 }
 function navDelta(v){pause();goto(slideIndex+v);}
 function stepState(v){pause();const s=current();if(s.type!=='state'){goto(iMap[activeStage()]);return;}
   let count=s.side==='hvdc'?runtimeSchedule.length:12;
   if(!count)return;
   const id=LCC.mod(s.id-1+v,count)+1;
   goto(iMap[s.side]+id-1);
 }
 function selectStage(stage){pause();goto(chapterIndex[stage]);}
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
   const text=$('angle-status');if(text)text.textContent=`θ = ${theta.toFixed(1)}°`+(transferNotes.length?' · '+transferNotes.join(' | '):' · Normal conduction');
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
     ChartView.render(canvas,s.side,params,liveWindow(),liveActive(),theta,mode);
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
 function renderState(s){
   const a=liveActive(s);const w=liveWindow(s);
   const type=(s.side==='hvdc')?(a.rOverlap&&a.iOverlap?'Both stations in overlap':a.rOverlap?'Rectifier overlap':a.iOverlap?'Inverter overlap':'Normal at both stations'):(s.id%2===0?'Commutation overlap':'Normal conduction');
   const overlap=type.toLowerCase().includes('overlap');
   const desc=s.side==='hvdc'?LCC.jointDescription(a):LCC.describe(s.side,s.id);
   const sub=s.side==='hvdc'?`Rectifier ${String(a.r).padStart(2,'0')} · Inverter ${String(a.i).padStart(2,'0')} · ${w.map(([lo,hi])=>`${lo.toFixed(1)}–${hi.toFixed(1)}°`).join(', ')}`
    :`Valves ${LCC.stateInfo(s.id).scrs.join(' + ')} · ${w.map(([lo,hi])=>`${lo.toFixed(1)}–${hi.toFixed(1)}°`).join(', ')}`;
   const inner=`<div class="tech-head"><div class="tech-index">${s.side==='rectifier'?'01':s.side==='inverter'?'02':'03'} · ${String(s.id).padStart(2,'0')}</div><div class="tech-title"><h1>${shortName(s.side)} · ${type}</h1><p>${sub}</p></div><div class="mode-badge ${overlap?'overlap':s.side==='hvdc'?'joint':''}">${overlap?'OVERLAP':'NORMAL'}</div></div>
     <div class="workspace"><section class="panel"><div class="panel-head"><strong>01 / CIRCUIT & CONDUCTION PATH</strong><div class="panel-actions"><button class="soft-btn" id="zoom-btn" aria-label="Enlarge diagram">⤢ ENLARGE</button></div></div><div class="diagram-area" id="circuit-host"><span class="empty-msg">Loading vector circuit…</span><span class="diagram-tip">SVG · editable source in GitHub</span></div></section>
     <section class="panel"><div class="panel-head"><strong>02 / CONCEPTUAL WAVEFORMS</strong><div class="panel-actions"><select class="soft-btn" id="chart-mode" aria-label="Choose signals"><option value="overview">Overview</option><option value="phase">Phase voltages</option><option value="line">Line voltages</option><option value="scr">SCR currents</option><option value="dc">DC quantities</option></select><button class="soft-btn ${showReference?'active':''}" id="ref-btn">${showReference?'LIVE MODEL':'SOURCE SVG'}</button></div></div><div class="plot-wrapper" id="plot-wrapper"><canvas id="plot-canvas" aria-label="Interactive LCC voltage and current plots"></canvas><div class="reference" id="reference-view" hidden></div><span class="reference-banner" id="reference-banner" hidden>Reference SVG: nominal parameters, not updated by sliders</span></div></section></div>
     <div class="tech-note" id="explain-row" ${showExplanation?'':'hidden'}><div class="explainer">${desc}</div><div class="fact-grid" id="facts">${facts(s,a)}</div></div>
     <div class="timeline"><div class="timeline-top"><span class="timeline-status" id="angle-status">θ = ${theta.toFixed(1)}° · ${type}</span><div class="timeline-actions"><button id="step-prev" title="Previous conduction state">◀ STATE</button><button class="primary" id="play-btn">${playing?'❚❚ PAUSE':'▶ PLAY'}</button><button id="step-next" title="Next conduction state">STATE ▶</button></div></div><input class="angle-range" id="angle-range" type="range" min="0" max="359.75" step="0.25" value="${theta}" aria-label="Electrical angle in degrees"><div class="ticks"><span>0°</span><span>60°</span><span>120°</span><span>180°</span><span>240°</span><span>300°</span><span>360°</span></div></div>`;
   $('slide').className='slide technical';$('slide').innerHTML=inner;cachedKey='';
   $('chart-mode').value=mode;
   $('chart-mode').addEventListener('change',e=>{mode=e.target.value;renderPlots();});
   $('ref-btn').onclick=()=>{showReference=!showReference;const b=$('ref-btn');b.textContent=showReference?'LIVE MODEL':'SOURCE SVG';b.classList.toggle('active',showReference);renderPlots();};
   $('step-prev').onclick=()=>stepState(-1);$('step-next').onclick=()=>stepState(1);
   $('play-btn').onclick=()=>togglePlay();
   $('angle-range').oninput=e=>{pause(false);setTheta(+e.target.value);syncSlideFromAngle();render();};
   $('zoom-btn').onclick=()=>openZoom();
   $('plot-canvas').addEventListener('click',ev=>{
      const rect=ev.currentTarget.getBoundingClientRect(),left=38,right=rect.width-15;
      const local=ev.clientX-rect.left;const pos=(local-left)/(right-left);
      if(pos>=0&&pos<=1){pause(false);setTheta(Math.min(359.75,360*pos));syncSlideFromAngle();render();}
   });
   renderCircuit(s,a);
   applyTransfer();
   renderPlots();
 }
 function renderHero(s){
   let title='',subtitle='',kicker='',stats='',extra='';
   if(s.type==='title'){
    kicker='POWER SYSTEMS · INTERACTIVE LEARNING';title='HVDC LCC<br>Current paths & commutation';
    subtitle='From a single 6-pulse rectifier to the inverter and a complete HVDC link. Explore 48 conduction states, live voltages and SCR currents in one offline lecture.';
    stats=[['03','Chapters'],['48','Reference states'],['360°','Interactive cycle'],['100%','Offline']];
   }else if(s.type==='roadmap'){
    kicker='THE LEARNING PATH';title='One concept<br>at a time.';
    subtitle='First follow the current through a rectifier. Then reverse the power conversion at the inverter. Finally join both stations and study commutation through the full DC link.';
    stats=[['01','Rectifier'],['02','Inverter'],['03','Full link'],['→','Next slide']];
   }else if(s.type==='end'){
    kicker='END OF PRESENTATION';title='Explore further.';
    subtitle='Change the firing delay, overlap and DC current. Revisit individual SCR currents and compare them with the original editable vector illustrations.';
    stats=[['48','Circuit states'],['±','Polarity matters'],['μ','Current transfer'],['γ','Extinction margin']];
   }else{
    const chapter={rectifier:['01 / RECTIFIER','AC to DC','Follow one upper and one lower SCR through six normal states and six commutation overlaps.','CA → CC'],inverter:['02 / INVERTER','DC to AC','Trace the reversed energy flow, extinction margin and six SCR current transfers.','CC → CA'],hvdc:['03 / COMPLETE HVDC','Connect the two stations','Follow the pole current through both converters, smoothing reactors and metallic return.','HVDC LINK']}[s.side];
    kicker=chapter[0];title=chapter[1];subtitle=chapter[2];stats=[['12',s.side==='hvdc'?'Joint states (24)':'Conduction states'],['6','Commutation events'],['1','Full cycle'],[chapter[3],'Power flow']];
    if(s.side==='hvdc')stats[0]=['24','Joint states'];
   }
   let blocks=stats.map(([n,label])=>`<div class="hero-stat"><strong>${n}</strong><span>${label}</span></div>`).join('');
   $('slide').className='slide';$('slide').innerHTML=`<section class="presentation-hero ${s.type==='chapter'?'chapter-hero':''}">${s.type==='chapter'?'<span class="chapter-index">'+(s.side==='rectifier'?'01':s.side==='inverter'?'02':'03')+'</span>':''}<div class="hero-kicker">${kicker}</div><h1 class="hero-title">${title}</h1><p class="hero-sub">${subtitle}</p><div class="hero-bottom">${blocks}</div><div class="hero-cta">Use <span class="keycap">←</span><span class="keycap">→</span> to navigate · <span class="keycap">O</span> for slide overview · <span class="keycap">F</span> for full screen</div></section>`;
 }
 function render(){
   updateSchedule();const s=current();
   if(s.type==='state')renderState(s);else renderHero(s);
   $('page-counter').textContent=`${slideIndex+1} / ${deck.length}`;
   $('progress-fill').style.width=`${((slideIndex+1)/deck.length*100).toFixed(2)}%`;
   $('nav-rect').classList.toggle('active',s.side==='rectifier');$('nav-inv').classList.toggle('active',s.side==='inverter');$('nav-hvdc').classList.toggle('active',s.side==='hvdc');
   $('footer-prev').disabled=slideIndex===0;$('footer-next').disabled=slideIndex===deck.length-1;
   $('current-chapter').textContent=s.side==='rectifier'?'CH 01 · RECTIFIER':s.side==='inverter'?'CH 02 · INVERTER':s.side==='hvdc'?'CH 03 · HVDC LINK':'HVDC LCC LEARNING LAB';
   $('settings-gamma').textContent=(180-params.alphaI-params.muI).toFixed(1)+'°';
 }
 function togglePlay(){if(playing){pause();return;}
   if(current().type!=='state'){goto(iMap[activeStage()]);}
   playing=true;lastTick=0;render();raf=requestAnimationFrame(tick);
 }
 function pause(redraw=true){playing=false;if(raf)cancelAnimationFrame(raf);raf=0;lastTick=0;if(redraw&&current().type==='state'&&$('play-btn'))$('play-btn').textContent='▶ PLAY';}
 function tick(t){if(!playing)return;if(lastTick){const old=slideIndex;setTheta(theta+(t-lastTick)*params.speed/1000);syncSlideFromAngle();if(old!==slideIndex){render();}else{const slider=$('angle-range');if(slider)slider.value=String(theta);const label=$('angle-status');if(label)label.textContent='θ = '+theta.toFixed(1)+'° · '+(liveActive().rOverlap?'Rectifier overlap':liveActive().iOverlap?'Inverter overlap':'Conduction');applyTransfer();renderPlots();}}lastTick=t;raf=requestAnimationFrame(tick);}
 function updateParam(name,value){
   params[name]=+value;
   params.alphaI=Math.max(105,Math.min(169,params.alphaI));
   params.muI=Math.max(1,Math.min(50,params.muI));
   if(params.muI+params.alphaI>170){
     if(name==='muI')params.alphaI=170-params.muI;
     else params.muI=170-params.alphaI;
   }
   for(const key of Object.keys(params))if($(key+'-range')){$(key+'-range').value=params[key];$(key+'-value').textContent=params[key].toFixed((key==='idc'||key==='vPeak'||key==='speed')?1:0)+(key.startsWith('alpha')||key.startsWith('mu')?'°':key==='speed'?' °/s':' p.u.');}
   updateSchedule();if(current().type==='state'){syncSlideFromAngle();}cachedKey='';render();
 }
 function setupSettings(){
   const names=[['alphaR',0,80,1,'Rectifier firing delay αᵣ'],['alphaI',105,169,1,'Inverter firing delay αᵢ'],['muR',1,50,1,'Rectifier overlap μᵣ'],['muI',1,50,1,'Inverter overlap μᵢ'],['idc',.2,2,.1,'Illustrative DC current I_dc'],['vPeak',.2,2,.1,'AC voltage peak V̂'],['speed',2,180,1,'Animation speed']];
   $('settings-sliders').innerHTML=names.map(([n,lo,hi,step,label])=>`<div class="slider-row"><label for="${n}-range">${label}</label><output id="${n}-value"></output><input id="${n}-range" type="range" min="${lo}" max="${hi}" step="${step}" value="${params[n]}"></div>`).join('');
   for(const [name] of names){$(name+'-range').addEventListener('input',e=>updateParam(name,e.target.value));}
   $('reset-btn').onclick=()=>{Object.assign(params,initial);updateParam('alphaR',initial.alphaR);};
   $('explain-btn').onclick=()=>{showExplanation=!showExplanation;$('explain-btn').textContent=showExplanation?'Hide explanations':'Show explanations';render();};
 }
 function switchOverlay(id,show){$(id).classList.toggle('open',show);$(id).setAttribute('aria-hidden',String(!show));}
 function openZoom(){if(!current()||current().type!=='state')return;const svg=$('circuit-host').querySelector('svg');if(!svg)return;
   $('zoom-content').innerHTML=svg.outerHTML;$('zoom-title').textContent=shortName(current().side)+' · STATE '+current().id;switchOverlay('zoom-overlay',true);
 }
 function overview(){pause();const grids=stages.map(stage=>{
   const n=stage==='hvdc'?24:12;
   return `<div class="overview-section">${shortName(stage)} · ${n} states</div><div class="overview-grid">${Array.from({length:n},(_,k)=>{const ix=iMap[stage]+k,active=ix===slideIndex?'active':'';return `<button data-slide="${ix}" class="${active}">STATE ${String(k+1).padStart(2,'0')}<small>${stage==='hvdc'?'JOINT':(k%2?'OVERLAP':'NORMAL')}</small></button>`;}).join('')}</div>`;
 }).join('');
   $('overview-body').innerHTML=grids;$('overview-body').querySelectorAll('[data-slide]').forEach(b=>b.addEventListener('click',()=>{switchOverlay('overview-overlay',false);goto(+b.dataset.slide); }));switchOverlay('overview-overlay',true);
 }
 function setup(){
   $('footer-prev').onclick=()=>navDelta(-1);$('footer-next').onclick=()=>navDelta(1);
   $('nav-rect').onclick=()=>selectStage('rectifier');$('nav-inv').onclick=()=>selectStage('inverter');$('nav-hvdc').onclick=()=>selectStage('hvdc');
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
   window.addEventListener('resize',()=>{if(current().type==='state'&&!showReference)renderPlots();});
   setupSettings();updateParam('alphaR',params.alphaR);goto(0);
   window.LCCPresentationTest={params,deck,getSlide:()=>current(),getIndex:()=>slideIndex,setSlide:i=>goto(i),setTheta:a=>{setTheta(a);syncSlideFromAngle();render();},at:LCC.at,sample:LCC.sample,schedule:()=>runtimeSchedule,reset:()=>Object.assign(params,initial)};
 }
 setup();
})();
