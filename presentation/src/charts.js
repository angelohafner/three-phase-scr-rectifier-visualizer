/* Continuous-cycle voltage and current chart renderer for the offline LCC lecture. */
'use strict';
const ChartView=(()=>{
 const colors=['#c43c55','#1d72a4','#008b8d','#87609b','#a77724','#587c78'];
 const strokes=[[],[7,4],[2,4],[9,3,2,3],[12,5],[3,3,10,3]];
 const palette={navy:'#18394e',muted:'#668094',grid:'#e8eef2',cyan:'#009caa',cursor:'#a72e43'};
 function serial(label,values,index=0,active=false){return {label,values,color:colors[index%6],dash:strokes[index%6],alpha:active?1:.66,width:active?2.3:1.4,emphasis:active};}
 function makeSeries(side,p,mode,active,selected='all'){
  const samples=Array.from({length:361},(_,angle)=>side==='hvdc'?{r:LCC.sample('rectifier',angle,p),i:LCC.sample('inverter',angle,p,LCC.OFFSET)}:LCC.sample(side,angle,p));
  const joint=side==='hvdc';
  const states=joint?{r:new Set(LCC.stateInfo(active.r).scrs),i:new Set(LCC.stateInfo(active.i).scrs)}:{single:new Set(LCC.stateInfo(active.id).scrs)};
  function make(name,signals,min,max){
   // All traces of a given physical quantity share the same global slider-range domain.
   const kind=FixedAxes.lccKind(name),[fixedMin,fixedMax]=FixedAxes.range(kind);
   return {name,series:signals,min:fixedMin,max:fixedMax,kind};
 }
  const groups=[];
  const source=station=>samples.map(x=>joint?x[station]:x);
  const stationNames=joint?[['r','Rectifier'],['i','Inverter']]:[['single',side==='inverter'?'Inverter':'Rectifier']];
  const phaseLabels=['vₐ','vᵦ','v𝒸'],lineLabels=['vₐᵦ','vᵦ𝒸','v𝒸ₐ'],acLabels=['iₐ','iᵦ','i𝒸'];
  function one(st,label,key,idx,em=false){return serial(label,source(st).map(x=>key(x)),idx,em)}
  for(const [st,title] of stationNames){
   if(mode==='phase'||mode==='line'){
    const key=mode==='phase'?'phase':'line';
    groups.push(make(title+' · '+(key==='phase'?'Phase voltages':'Line voltages')+' (p.u.)',
      (mode==='phase'?phaseLabels:lineLabels).map((label,j)=>one(st,label,d=>d[key][j],j)), -2*p.vPeak,2*p.vPeak));
    if(!joint)groups.push(make('AC phase currents (p.u.)',acLabels.map((label,j)=>one(st,label,d=>d.ac[j],j)), -1.4*p.idc,1.4*p.idc));
   }else if(mode==='scr'||mode==='vak'||mode==='valvePair'){
    let names=LCC.SCRS.filter(t=>selected==='all'||t===selected);
    if(mode==='scr'||mode==='valvePair')groups.push(make(title+' · SCR currents (p.u.)',names.map((t,j)=>one(st,t,d=>d.scr[t],LCC.SCRS.indexOf(t),states[st].has(t))),-0.08*p.idc,1.3*p.idc));
    if(mode==='vak'||mode==='valvePair')groups.push(make(title+' · SCR anode–cathode voltages (p.u.)',names.map(t=>one(st,`v_${'AK,'+t}`,d=>d.vak[t],LCC.SCRS.indexOf(t),states[st].has(t))),-2.2*p.vPeak,2.2*p.vPeak));
   }else if(mode==='dc'){
    if(joint){
      groups.push(make('DC voltages · common current-direction reference (p.u.)',[one('r','v_dc,r',d=>d.dc,1),one('i','v_dc,i',d=>d.dc,0)],-2*p.vPeak,2*p.vPeak));
      groups.push(make('Common pole current (p.u.)',[one('r','i_dc',d=>d.idc,0)],0,1.3*p.idc));
      break;
    }
    groups.push(make(title+' · signed DC voltage (p.u.)',[one(st,'v_dc',d=>d.dc,1),one(st,'v_ideal',d=>d.dcIdeal,4)],-2*p.vPeak,2*p.vPeak));
    groups.push(make(title+' · DC current (p.u.)',[one(st,'i_dc',d=>d.idc,0)],0,1.3*p.idc));
   }else{
    if(joint){
      // In joint overview, plot the common DC voltages once, followed by one
      // independent SCR-current group for each station.
      if(st==='r')groups.push(make('Both stations · signed DC voltages (p.u.)',
        [one('r','v_dc,r',d=>d.dc,1),one('i','v_dc,i',d=>d.dc,0)],-2*p.vPeak,2*p.vPeak));
      groups.push(make(title+' · SCR currents (p.u.)',LCC.SCRS.map(t=>one(st,t,d=>d.scr[t],LCC.SCRS.indexOf(t),states[st].has(t))),0,1.3*p.idc));
    }else{
      groups.push(make(title+' · Phase voltages (p.u.)',phaseLabels.map((label,j)=>one(st,label,d=>d.phase[j],j)),-1.3*p.vPeak,1.3*p.vPeak));
      groups.push(make(title+' · SCR currents (p.u.)',LCC.SCRS.map(t=>one(st,t,d=>d.scr[t],LCC.SCRS.indexOf(t),states[st].has(t))),0,1.3*p.idc));
      groups.push(make(title+' · signed DC voltage and current (p.u.)',[one(st,'v_dc',d=>d.dc,1),one(st,'i_dc',d=>d.idc,0)],-2*Math.max(p.vPeak,p.idc),2*Math.max(p.vPeak,p.idc)));
    }
   }
  }
  return groups;
 }
 function render(canvas,side,p,windows,active,theta,mode='overview',selected='all',focusedPanel=null){
   if(!canvas||!canvas.isConnected)return;
   const bounds=canvas.getBoundingClientRect(),w=Math.max(190,bounds.width),h=Math.max(125,bounds.height);
   const dpr=Math.min(2,devicePixelRatio||1),iw=Math.round(w*dpr),ih=Math.round(h*dpr);
   if(canvas.width!==iw||canvas.height!==ih){canvas.width=iw;canvas.height=ih;}
   const g=canvas.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,w,h);
   const complete=makeSeries(side,p,mode,active,selected);
   const groups=Number.isInteger(focusedPanel)&&focusedPanel>=0&&focusedPanel<complete.length?
     [complete[focusedPanel]]:complete;
   const count=Math.max(groups.length,1);
   canvas.dataset.visiblePanels=JSON.stringify(groups.map(g=>g.name));
   canvas.dataset.axisPreset=FixedAxes.preset();
   canvas.dataset.axisClipped=String(groups.some(group=>
     group.series.some(line=>FixedAxes.outside(line.values,group.min,group.max))));
   canvas.dataset.axisMode='fixed';
   canvas.dataset.axisLimits=JSON.stringify(groups.map(g=>({kind:g.kind,min:g.min,max:g.max,x:[0,360]})));
   const enlarged=Number.isInteger(focusedPanel)&&groups.length===1;
   const gap=7,top=6,bottom=8,row=(h-top-bottom-gap*(count-1))/count,x0=45,x1=w-16;
   const xPos=a=>x0+(a/360)*(x1-x0);
   for(let groupIndex=0;groupIndex<groups.length;groupIndex++){
     const group=groups[groupIndex],y=top+groupIndex*(row+gap),t=y+(enlarged?53:25),b=y+row-19;
     const yPos=v=>b-(v-group.min)/(group.max-group.min)*(b-t);
     g.fillStyle=groupIndex%2===0?'#fbfdff':'#f5f9fb';g.fillRect(0,y,w,row);
     g.fillStyle=palette.navy;g.font='600 11px "Segoe UI",Arial';
     g.fillText(enlarged?group.name.replace(/^(Rectifier|Inverter) · /,''):group.name,
       11,y+15,w-22);
     for(let angle=0;angle<=360;angle+=60){const x=xPos(angle);g.strokeStyle=palette.grid;g.lineWidth=.9;g.beginPath();g.moveTo(x,t);g.lineTo(x,b);g.stroke();g.font='normal 9px "Segoe UI",Arial';g.fillStyle=palette.muted;g.fillText(`${angle}°`,Math.min(w-31,x-8),b+12);}
     for(let j=0;j<=4;j++){let yy=t+(b-t)*j/4;g.strokeStyle='#ebeff3';g.lineWidth=.8;g.beginPath();g.moveTo(x0,yy);g.lineTo(x1,yy);g.stroke();}
     // Every operating interval remains shaded as the sliders move.
     for(const [lo,hi] of windows||[]){if(hi<=lo)continue;g.fillStyle='rgba(0,156,170,.13)';g.fillRect(xPos(lo),t,xPos(hi)-xPos(lo),b-t);}
     if(group.min<0&&group.max>0){g.strokeStyle='#a5b8c3';g.beginPath();g.moveTo(x0,yPos(0));g.lineTo(x1,yPos(0));g.stroke();}
     for(const line of group.series.slice().sort((a,b)=>Number(a.emphasis)-Number(b.emphasis))){
       g.save();g.strokeStyle=line.color;g.lineWidth=line.width;g.globalAlpha=line.alpha;g.setLineDash(line.dash);
       g.beginPath();let open=false;
       line.values.forEach((value,k)=>{
         if(!Number.isFinite(value)){open=false;return;}
         const xx=xPos(k),yy=Math.max(t-1,Math.min(b+1,yPos(value)));
         if(!open){g.moveTo(xx,yy);open=true;}else g.lineTo(xx,yy);
       });g.stroke();g.restore();
     }
     const xc=xPos(theta);g.save();g.strokeStyle=palette.cursor;g.globalAlpha=.8;g.lineWidth=1.3;g.setLineDash([6,4]);g.beginPath();g.moveTo(xc,t);g.lineTo(xc,b);g.stroke();g.restore();
     g.font='normal 9px "Segoe UI",Arial';g.fillStyle=palette.muted;
     g.fillText(group.max.toFixed(1),3,t+8);g.fillText(group.min.toFixed(1),3,b);
     if(enlarged){
       // Keep legends on independent rows below the title in narrow views.
       let lx=x0,ly=y+30;
       for(const item of group.series){
         const need=Math.max(48,item.label.length*6.7+22);
         if(lx+need>x1&&ly<y+42){lx=x0;ly=y+42;}
         if(lx+need>x1)break;
         g.save();g.strokeStyle=item.color;g.lineWidth=1.8;
         g.globalAlpha=item.alpha;g.setLineDash(item.dash);
         g.beginPath();g.moveTo(lx,ly-3);g.lineTo(lx+13,ly-3);g.stroke();g.restore();
         MathUI.paint(g,item.label,lx+16,ly,{size:9,color:palette.navy});
         lx+=need;
       }
     }else{
       const visible=group.series.length>4&&w<660?group.series.slice(0,4):group.series;
       let lx=w-12;
       for(const item of [...visible].reverse()){
         const label=item.label,need=label.length*6.9+24;lx-=need;
         if(lx<Math.max(125,w*.34))break;
         g.save();g.strokeStyle=item.color;g.lineWidth=1.8;g.globalAlpha=item.alpha;g.setLineDash(item.dash);
         g.beginPath();g.moveTo(lx,y+12);g.lineTo(lx+15,y+12);g.stroke();g.restore();
         MathUI.paint(g,label,lx+18,y+15,{size:10,color:palette.navy});
       }
     }
   }
   canvas.dataset.plotLeft=String(x0);canvas.dataset.plotRight=String(x1);
 }
 return {render,makeSeries};
})();
