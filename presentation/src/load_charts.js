/* R, RL, LE, RLE Canvas waveforms with current-window shading and math labeling. */
'use strict';
const LoadCharts=(()=>{
 const palette=['#c63b54','#1d72a4','#008c91','#8e65a4','#aa772a','#56836e'];
 const dashes=[[],[8,4],[2,4],[8,3,2,3],[12,4],[3,3,10,3]];
 const cache=new Map();
 function model(mode,params){
   const config=LoadModel.config(params),key=mode+JSON.stringify({alpha:config.alpha,R:mode==='LE'?0:config.R,L:mode==='R'?0:config.L,E:mode==='LE'||mode==='RLE'?config.E:0,i0:mode==='LE'||mode==='RLE'?config.i0:0,v:config.v,frequency:config.frequency});
   if(!cache.has(key)){if(cache.size>=16)cache.clear();cache.set(key,LoadModel.sample(mode,params));}
   return cache.get(key);
 }
 function view(canvas){
   const r=canvas.getBoundingClientRect(),w=Math.max(190,r.width),h=Math.max(130,r.height),d=Math.min(2,devicePixelRatio||1);
   if(canvas.width!==Math.round(w*d)||canvas.height!==Math.round(h*d)){canvas.width=Math.round(w*d);canvas.height=Math.round(h*d);}
   const g=canvas.getContext('2d');g.setTransform(d,0,0,d,0,0);g.clearRect(0,0,w,h);return {g,w,h};
 }
 function drawPanel(g,rect,title,lines,max,min,theta,windows,blocked=false,modelMode='R'){
   const kind=FixedAxes.loadKind(title,modelMode),fixed=FixedAxes.range(kind);
   [min,max]=fixed;
   const secondary=title.includes('DC quantities')?
     FixedAxes.range(modelMode==='LE'?'leCurrent':'loadCurrent'):null;
   const {x,y,w,h}=rect,top=y+24,bot=y+h-20,left=x+40,right=x+w-(secondary?43:13);
   const X=a=>left+(a/360)*(right-left),Y=v=>bot-(v-min)/(max-min)*(bot-top);
   const rightY=v=>bot-(v-secondary[0])/(secondary[1]-secondary[0])*(bot-top);
   g.fillStyle='#fbfdff';g.fillRect(x,y,w,h);
   g.font='600 11px "Segoe UI",Arial';g.fillStyle='#23435d';g.fillText(title,x+9,y+14);
   for(let j=0;j<=6;j++){const a=j*60,xx=X(a);g.strokeStyle='#e4edf3';g.lineWidth=.7;g.beginPath();g.moveTo(xx,top);g.lineTo(xx,bot);g.stroke();g.font='normal 9px "Segoe UI",Arial';g.fillStyle='#658192';g.fillText(`${a}°`,Math.min(x+w-29,xx-8),bot+13);}
   for(let j=0;j<=4;j++){const yy=top+(bot-top)*j/4;g.strokeStyle='#e9f0f4';g.beginPath();g.moveTo(left,yy);g.lineTo(right,yy);g.stroke();}
   for(const [lo,hi] of windows||[]){
     if(hi<=lo)continue;
     g.fillStyle=blocked?'rgba(162,168,175,.19)':'rgba(0,158,168,.14)';g.fillRect(X(lo),top,X(hi)-X(lo),bot-top);
   }
   if(min<0&&max>0){g.strokeStyle='#b1c1ce';g.beginPath();g.moveTo(left,Y(0));g.lineTo(right,Y(0));g.stroke();}
   const entries=lines.filter(Boolean);
   entries.forEach((ln,j)=>{
     const idx=ln.index??j;
     g.save();g.strokeStyle=ln.color||palette[idx%6];g.globalAlpha=ln.opacity??(j===0?.93:.66);g.lineWidth=ln.width??(j===0?2:1.3);g.setLineDash(ln.dash||dashes[idx%6]);g.beginPath();
     let started=false;
     ln.data.forEach((a,k)=>{if(!Number.isFinite(a)){started=false;return;}
       const xx=X(k*360/(ln.data.length-1)),mapped=secondary&&ln.label==='i_dc'?rightY(a):Y(a);
       const yy=Math.max(top-1,Math.min(bot+1,mapped));
       if(!started){g.moveTo(xx,yy);started=true;}else g.lineTo(xx,yy);
     });g.stroke();g.restore();
   });
   g.save();g.strokeStyle='#b23b53';g.globalAlpha=.82;g.setLineDash([5,4]);g.lineWidth=1.25;g.beginPath();g.moveTo(X(theta),top);g.lineTo(X(theta),bot);g.stroke();g.restore();
   g.font='normal 9px "Segoe UI",Arial';g.fillStyle='#6e8699';g.fillText(max.toFixed(1),x+3,top+8);g.fillText(min.toFixed(1),x+3,bot);
   if(secondary){
     // Voltage uses the left axis; current uses the independent fixed right axis.
     g.fillStyle='#b23b53';g.font='normal 9px "Segoe UI",Arial';
     for(let j=0;j<=4;j++){
       const v=secondary[1]-(secondary[1]-secondary[0])*j/4;
       g.fillText(v.toFixed(secondary[1]>50?0:1),right+5,top+(bot-top)*j/4+3);
     }
   }
   let pos=right-5;
   for(const ln of [...entries].reverse()){
     const need=ln.label.length*6.8+24;pos-=need;if(pos<x+130)break;
     g.save();g.strokeStyle=ln.color||palette[(ln.index||0)%6];g.globalAlpha=ln.opacity??.85;g.lineWidth=1.7;g.setLineDash(ln.dash||dashes[(ln.index||0)%6]);g.beginPath();g.moveTo(pos,y+11);g.lineTo(pos+13,y+11);g.stroke();g.restore();
     MathUI.paint(g,ln.label,pos+16,y+14,{size:10});
   }
   const clipped=entries.some(ln=>FixedAxes.outside(ln.data,
     secondary&&ln.label==='i_dc'?secondary[0]:min,
     secondary&&ln.label==='i_dc'?secondary[1]:max));
   return {kind,min,max,right:secondary,x:[0,360],model:modelMode,clipped};
 }
 function render(canvas,mode,params,theta,chartMode='overview',selected='all'){
   if(!canvas||!canvas.isConnected)return;
   const {g,w,h}=view(canvas),v=FixedAxes.range('dcVoltage')[1];
   const opts={color:palette[0],opacity:.9,width:2.1};
   const iMax=FixedAxes.range(mode==='LE'?'leCurrent':'loadCurrent')[1];
   if(mode==='compare'||mode==='compareAll'){
     const modes=mode==='compare'?['R','RL']:['R','RL','LE','RLE'];
     const cols=2,rows=Math.ceil(modes.length/2),gap=7,cw=(w-10-gap)/2,ch=(h-7-(rows-1)*gap)/rows;
     const axes=[];
     modes.forEach((which,j)=>{
       const s=model(which,params),win=LoadModel.activeWindow(s,theta);
       const x=5+(j%2)*(cw+gap),y=5+Math.floor(j/2)*(ch+gap);
       axes.push(drawPanel(g,{x,y,w:cw,h:ch},`${which} · DC quantities (p.u.)`,[
         {label:'v_dc',data:s.voltage,index:1,color:palette[1]},
         {label:'i_dc',data:s.current,index:0,color:palette[0]}
       ],Math.max(v,iMax),-.65*params.vPeak,theta,win.windows,win.blocked,which));
     });
     canvas.dataset.axisMode='fixed';canvas.dataset.axisPreset=FixedAxes.preset();
     canvas.dataset.axisClipped=String(axes.some(a=>a.clipped));
     canvas.dataset.axisLimits=JSON.stringify(axes);
     return;
   }
   const s=model(mode,params),win=LoadModel.activeWindow(s,theta);
   let plans=[];
   const phase=s.phase.map((data,j)=>({data,label:['vₐ','vᵦ','v𝒸'][j],index:j}));
   const lines=s.line.map((data,j)=>({data,label:['vₐᵦ','vᵦ𝒸','v𝒸ₐ'][j],index:j}));
   const ac=s.ac.map((data,j)=>({data,label:['iₐ','iᵦ','i𝒸'][j],index:j}));
   const scrs=Object.entries(s.scr).filter(([t])=>selected==='all'||selected===t).map(([label,data])=>({label,data,index:Number(label.slice(1))-1}));
   const vak=Object.entries(s.vak).filter(([t])=>selected==='all'||selected===t).map(([label,data])=>({label:`v_AK,${label}`,data,index:Number(label.slice(1))-1}));
   switch(chartMode){
    case 'phase':plans=[[`AC phase voltages (p.u.)`,phase,v,-v],[`AC phase currents (p.u.)`,ac,iMax,-iMax]];break;
    case 'line':plans=[[`Line voltages (p.u.)`,lines,v,-v],[`DC voltage (p.u.)`,[{label:'v_dc',data:s.voltage,index:1}],v,-.8*params.vPeak]];break;
    case 'scr':plans=[[`SCR currents (p.u.)`,scrs,iMax,0],[`DC current (p.u.)`,[{label:'i_dc',data:s.current,index:0}],iMax,0]];break;
    case 'vak':plans=[[`SCR voltages (p.u.) · floating intervals undefined`,vak,v,-v]];break;
    case 'valvePair':plans=[[`Selected SCR current (p.u.)`,scrs,iMax,0],[`Selected SCR voltage (p.u.)`,vak,v,-v]];break;
    case 'dc':plans=[[`DC output voltage (p.u.)`,[{label:'v_dc',data:s.voltage,index:1}],v,-v],[`DC output current (p.u.)`,[{label:'i_dc',data:s.current,index:0}],iMax,0]];break;
    default:plans=[[`Phase voltages (p.u.)`,phase,v,-v],[`DC quantities (p.u.)`,[{label:'v_dc',data:s.voltage,index:1},{label:'i_dc',data:s.current,index:0}],Math.max(iMax,v),-.7*params.vPeak],[`SCR currents (p.u.)`,scrs,iMax,0]];
   }
   const H=h/plans.length;
   const axes=[];
   plans.forEach(([title,values,max,min],j)=>axes.push(drawPanel(g,{x:0,y:j*H,w,h:H},title,values,max,min,theta,win.windows,win.blocked,mode)));
   canvas.dataset.axisMode='fixed';canvas.dataset.axisPreset=FixedAxes.preset();
   canvas.dataset.axisClipped=String(axes.some(a=>a.clipped));
   canvas.dataset.axisLimits=JSON.stringify(axes);
   if(chartMode==='vak'&&win.blocked){g.fillStyle='#4c687d';g.font='normal 10px "Segoe UI",Arial';g.fillText('Floating DC buses: individual vAK undefined.',50,Math.min(67,h/5));}
 }
 return {render,model};
})();
