/* Offline Canvas waveforms with dash-coded, translucent traces and conduction bands. */
'use strict';
const LoadCharts = (() => {
 const colors=['#bf354d','#08768c','#94652e','#675ab0','#26866e','#bc6538'];
 const dashes=[[],[9,4],[2,4],[10,3,2,3],[7,4,2,4],[3,3,8,3]];
 const cache=new Map();
 function model(mode,params){
   const key=mode+JSON.stringify(LoadModel.config(params));
   if(!cache.has(key)){if(cache.size>=12)cache.clear();cache.set(key,LoadModel.sample(mode,params));}
   return cache.get(key);
 }
 function limits(draws,{symmetric=false,positive=false,minimum=0.25}={}) {
   const values=draws.flatMap(d=>d.data.filter(Number.isFinite));
   const minValue=values.length?Math.min(0,...values):0,maxValue=values.length?Math.max(0,...values):1;
   let lo=positive?0:minValue,hi=maxValue;
   if(symmetric){const b=Math.max(minimum,Math.abs(lo),Math.abs(hi))*1.13;return [-b,b];}
   hi=Math.max(minimum,hi,lo+.001);return [lo-(positive?0:Math.max(.04,(hi-lo)*.1)),hi+Math.max(.08,(hi-lo)*.12)];
 }
 function resize(canvas){
   const box=canvas.getBoundingClientRect(),w=Math.max(210,box.width),h=Math.max(180,box.height),d=Math.min(2,window.devicePixelRatio||1);
   canvas.width=Math.round(w*d);canvas.height=Math.round(h*d);const g=canvas.getContext('2d');g.setTransform(d,0,0,d,0,0);return {g,w,h};
 }
 function panel(g,rect,title,draws,theta,windows=[],opt={}) {
   const {x,y,w,h}=rect,top=y+29,bottom=y+h-24,left=x+45,right=x+w-12;
   if(bottom<=top+8)return;
   const bounds=limits(draws,opt),lo=bounds[0],hi=bounds[1];
   const px=a=>left+a/360*(right-left),py=v=>bottom-(v-lo)/(hi-lo)*(bottom-top);
   g.fillStyle='#ffffff';g.fillRect(x,y,w,h);
   g.fillStyle='#163e52';g.font='700 11px "Segoe UI",Arial,sans-serif';g.fillText(title,x+10,y+17);
   for(const [a,b] of windows){if(b>a){g.fillStyle='rgba(0,153,161,.095)';g.fillRect(px(a),top,px(b)-px(a),bottom-top);}}
   for(let a=0;a<=360;a+=60){const xx=px(a);g.strokeStyle='#e2edf0';g.lineWidth=1;g.setLineDash([]);g.beginPath();g.moveTo(xx,top);g.lineTo(xx,bottom);g.stroke();g.fillStyle='#6e8190';g.font='10px "Segoe UI",Arial,sans-serif';g.fillText(a+'°',Math.min(xx-7,right-22),bottom+13);}
   for(let i=0;i<=4;i++){const yy=top+(bottom-top)*i/4;g.strokeStyle='#eef2f3';g.beginPath();g.moveTo(left,yy);g.lineTo(right,yy);g.stroke();}
   if(lo<0&&hi>0){g.strokeStyle='#a4b8c2';g.beginPath();g.moveTo(left,py(0));g.lineTo(right,py(0));g.stroke();}
   g.fillStyle='#607786';g.font='10px "Segoe UI",Arial,sans-serif';g.fillText(hi.toFixed(2),x+3,top+6);g.fillText(lo.toFixed(2),x+3,bottom);
   g.save();g.beginPath();g.rect(left,top,right-left,bottom-top);g.clip();
   draws.forEach((d,k)=>{
     g.strokeStyle=d.color||colors[k%6];g.lineWidth=d.width||1.8;g.globalAlpha=d.opacity??.79;g.setLineDash(d.dash??dashes[k%6]);
     g.beginPath();let started=false;
     for(let j=0;j<d.data.length;j++){
       const v=d.data[j];if(!Number.isFinite(v)){started=false;continue;}
       const xx=px(j*360/(d.data.length-1)),yy=py(v);
       if(!started)g.moveTo(xx,yy);else g.lineTo(xx,yy);started=true;
     }
     g.stroke();g.setLineDash([]);g.globalAlpha=1;
   });
   g.restore();g.setLineDash([4,4]);g.strokeStyle='#bf3b4d';g.lineWidth=1.5;g.beginPath();g.moveTo(px(theta),top);g.lineTo(px(theta),bottom);g.stroke();g.setLineDash([]);
   let lx=Math.max(left+5,right-draws.length*66);
   for(let j=0;j<draws.length&&lx<right-18;j++){
     const d=draws[j];g.strokeStyle=d.color||colors[j%6];g.setLineDash(d.dash??dashes[j%6]);g.lineWidth=2;g.globalAlpha=d.opacity??.84;
     g.beginPath();g.moveTo(lx,y+14);g.lineTo(lx+12,y+14);g.stroke();g.setLineDash([]);g.globalAlpha=1;
     const width=TechnicalMath.draw(g,lx+15,y+18,d.label,{size:10});lx+=width+25;
   }
 }
 function wave(name,data,colorIdx){return {label:name,data,color:colors[colorIdx%6],dash:dashes[colorIdx%6],opacity:.82};}
 function plot(canvas,series,params,theta,mode='overview',focus='all') {
   if(!canvas||!canvas.isConnected)return;
   const {g,w,h}=resize(canvas),rows=[];
   const currents=Object.entries(series.scr).map(([t,d],i)=>wave(`i_{${t}}`,d,i));
   const voltages=Object.entries(series.scrVoltage).map(([t,d],i)=>wave(`v_{AK,${t.slice(1)}}`,d,i));
   function filtered(list){return focus==='all'?list:list.map(s=>({...s,opacity:s.label.endsWith(focus.slice(1)+'}')?.94:.18,width:s.label.endsWith(focus.slice(1)+'}')?2.7:1.1}));}
   const phase=series.phase.map((d,i)=>wave(['v_{a}','v_{b}','v_{c}'][i],d,i));
   const line=series.line.map((d,i)=>wave(['v_{ab}','v_{bc}','v_{ca}'][i],d,i));
   const ac=series.ac.map((d,i)=>wave(['i_{a}','i_{b}','i_{c}'][i],d,i));
   const dc=[wave('v_{dc}',series.voltage,1),wave('i_{dc}',series.current,0)];
   if(mode==='phase'){rows.push(['Phase voltages (pu)',phase,{symmetric:true}],['AC currents (pu)',ac,{symmetric:true}]);}
   else if(mode==='line'){rows.push(['Line voltages (pu)',line,{symmetric:true}],['DC-side voltage (pu)',[dc[0]],{symmetric:true}]);}
   else if(mode==='scr'){rows.push(['SCR currents (pu)',filtered(currents),{positive:true}],['DC current (pu)',[dc[1]],{positive:true}]);}
   else if(mode==='scrv'){
     rows.push(['SCR anode-to-cathode voltages (pu)',filtered(voltages),{symmetric:true}],['SCR current / DC current (pu)',filtered(currents),{positive:true}]);
   }else if(mode==='dc'){rows.push(['DC-side voltage (pu)',[dc[0]],{symmetric:true}],['DC load current (pu)',[dc[1]],{positive:true}]);}
   else {rows.push(['Phase voltages (pu)',phase,{symmetric:true}],['DC quantities (pu)',dc,{symmetric:true}]);}
   rows.push(['SCR currents (pu)',filtered(currents),{positive:true}]);
   const gap=6,pad=3,hh=(h-pad*2-gap*(rows.length-1))/rows.length;
   rows.forEach(([title,draw,opt],i)=>panel(g,{x:0,y:pad+i*(hh+gap),w,h:hh},title,draw,theta,series.windows,opt));
   canvas.dataset.plotLeft='45';canvas.dataset.plotRight=String(w-12);
 }
 function render(canvas,kind,params,theta,chartMode='overview',focus='all'){
   if(kind==='compare'){
     if(!canvas||!canvas.isConnected)return;
     const r=model('R',params),rl=model('RL',params),{g,w,h}=resize(canvas),gap=8,cw=(w-gap)/2,hh=(h-gap)/2;
     for(const [j,s,t] of [[0,r,'R'],[1,rl,'RL']]) {
       panel(g,{x:j*(cw+gap),y:0,w:cw,h:hh},t+' · DC voltage (pu)',[wave('v_{dc}',s.voltage,1)],theta,s.windows,{symmetric:true});
       panel(g,{x:j*(cw+gap),y:hh+gap,w:cw,h:hh},t+' · DC current (pu)',[wave('i_{dc}',s.current,0)],theta,s.windows,{positive:true});
     }
     return;
   }
   plot(canvas,model(kind,params),params,theta,chartMode,focus);
 }
 return {render,model,plot,limits};
})();
