/* Lightweight, offline Canvas renderer for R/RL educational waveforms. */
'use strict';
const LoadCharts=(()=>{
 const colors={red:'#d33048',blue:'#1576a9',teal:'#159f9b',grey:'#bac9d2',ink:'#274a61',grid:'#e5ecf2'};
 const cache=new Map();
 function model(mode,p){const c=LoadModel.config(p),key=mode+JSON.stringify(c);if(!cache.has(key)){if(cache.size>8)cache.clear();cache.set(key,LoadModel.sample(mode,p));}return cache.get(key);}
 function resize(canvas){let box=canvas.getBoundingClientRect(),w=Math.max(170,box.width),h=Math.max(90,box.height),d=Math.min(window.devicePixelRatio||1,2);canvas.width=Math.round(w*d);canvas.height=Math.round(h*d);let g=canvas.getContext('2d');g.setTransform(d,0,0,d,0,0);return {g,w,h};}
 function panel(g,rect,title,draws,max,min,theta,axis=true){
  let {x,y,w,h}=rect;let top=y+24,bottom=y+h-20,left=x+38,right=x+w-12,H=bottom-top;
  g.fillStyle='#fbfdff';g.fillRect(x,y,w,h);g.font='700 11px Arial';g.fillStyle=colors.ink;g.fillText(title,x+9,y+14);
  function px(a){return left+(a/360)*(right-left)}
  function py(v){return bottom-(v-min)/(max-min)*H}
  for(let k=0;k<=6;k++){let xx=px(60*k);g.strokeStyle=colors.grid;g.lineWidth=1;g.beginPath();g.moveTo(xx,top);g.lineTo(xx,bottom);g.stroke();if(axis){g.fillStyle='#6a8394';g.font='9px Arial';g.fillText((60*k)+'°',xx-6,bottom+12)}}
  g.lineWidth=1;g.strokeStyle='#e2eaf0';for(let k=0;k<=4;k++){let yy=top+H*k/4;g.beginPath();g.moveTo(left,yy);g.lineTo(right,yy);g.stroke()}
  if(max>0&&min<0){g.beginPath();g.moveTo(left,py(0));g.lineTo(right,py(0));g.strokeStyle='#b0c1ce';g.stroke()}
  g.font='9px Arial';g.fillStyle='#7892a6';g.fillText(max.toFixed(1),x+1,top+9);g.fillText(min.toFixed(1),x+1,bottom);
  for(const d of draws){g.beginPath();let arr=d.data;for(let j=0;j<arr.length;j++){let xx=px(j*360/(arr.length-1)),yy=Math.max(top-2,Math.min(bottom+2,py(arr[j])));if(j===0)g.moveTo(xx,yy);else g.lineTo(xx,yy)}g.lineWidth=d.w||1.6;g.strokeStyle=d.color||colors.blue;g.globalAlpha=d.opacity||1;g.stroke();g.globalAlpha=1;}
  g.strokeStyle=colors.red;g.setLineDash([5,3]);g.lineWidth=1.4;g.beginPath();g.moveTo(px(theta),top);g.lineTo(px(theta),bottom);g.stroke();g.setLineDash([]);
  let labelX=right-9;g.font='9px Arial';for(let d of draws.slice().reverse()){let tw=g.measureText(d.label).width;labelX-=tw+23;g.fillStyle=d.color;g.fillRect(labelX,y+9,9,2);g.fillStyle='#536d7d';g.fillText(d.label,labelX+12,y+14);}
 }
 function render(canvas,kind,params,theta,chartMode='overview'){
  if(!canvas||!canvas.isConnected)return;
  const {g,w,h}=resize(canvas);g.clearRect(0,0,w,h);
  if(kind==='compare'){
   let R=model('R',params),RL=model('RL',params),margin=5,gap=10,cw=(w-2*margin-gap)/2,ch=(h-12)/2;
   [[R,'PURE R',margin],[RL,'R + L',margin+cw+gap]].forEach(([s,name,x])=>{
    panel(g,{x,y:5,w:cw,h:ch},name+' · v_dc', [{label:'v_dc',color:colors.blue,data:s.voltage,w:1.8}],2.1*params.vPeak,-.7*params.vPeak,theta,false);
    panel(g,{x,y:5+ch,w:cw,h:ch},name+' · i_dc', [{label:'i_dc',color:colors.red,data:s.current,w:2.0}],2.2*params.vPeak/params.loadR,0,theta,true);
   });return;
  }
  const s=model(kind,params),H=h/3;
  if(chartMode==='phase'){
    panel(g,{x:0,y:0,w,h:H},'Phase-to-neutral voltages (p.u.)',s.phase.map((data,j)=>({label:['vₐ','vᵦ','v𝒸'][j],color:[colors.red,colors.blue,colors.teal][j],data})),1.2*params.vPeak,-1.2*params.vPeak,theta);
    panel(g,{x:0,y:H,w,h:H},'AC phase currents (p.u.)',s.ac.map((data,j)=>({label:['iₐ','iᵦ','i𝒸'][j],color:[colors.red,colors.blue,colors.teal][j],data})),2.2*params.vPeak/params.loadR,-2.2*params.vPeak/params.loadR,theta);
  }else if(chartMode==='line'){
    panel(g,{x:0,y:0,w,h:H},'Line-to-line voltages (p.u.)',s.line.map((data,j)=>({label:['vₐᵦ','vᵦ𝒸','v𝒸ₐ'][j],color:[colors.red,colors.blue,colors.teal][j],data})),2.0*params.vPeak,-2.0*params.vPeak,theta);
    panel(g,{x:0,y:H,w,h:H},'Output voltage', [{label:'v_dc',data:s.voltage,color:colors.blue}],2.1*params.vPeak,-.7*params.vPeak,theta);
  }else if(chartMode==='scr'){
    panel(g,{x:0,y:0,w,h:H},'Six SCR currents (p.u.)',Object.entries(s.scr).map(([label,data],j)=>({label,color:[colors.red,colors.blue,colors.teal,'#5a9472','#9a78bb','#e89c40'][j],data,w:1.4})),2.2*params.vPeak/params.loadR,0,theta);
    panel(g,{x:0,y:H,w,h:H},'DC load current (p.u.)', [{label:'i_dc',data:s.current,color:colors.red,w:2.0}],2.2*params.vPeak/params.loadR,0,theta);
  }else {
    panel(g,{x:0,y:0,w,h:H},'Phase voltages (p.u.)',s.phase.map((data,j)=>({label:['vₐ','vᵦ','v𝒸'][j],color:[colors.red,colors.blue,colors.teal][j],data})),1.2*params.vPeak,-1.2*params.vPeak,theta);
    panel(g,{x:0,y:H,w,h:H},'DC voltage / current (p.u.)', [{label:'v_dc',data:s.voltage,color:colors.blue},{label:'i_dc',data:s.current,color:colors.red,w:2.3}],2.2*Math.max(params.vPeak,params.vPeak/params.loadR),-.7*params.vPeak,theta);
  }
  panel(g,{x:0,y:H*2,w,h:H},'SCR currents (p.u.)',Object.entries(s.scr).map(([label,data],j)=>({label,color:[colors.red,colors.blue,colors.teal,'#5a9472','#9a78bb','#e89c40'][j],data,w:1.4})),2.2*params.vPeak/params.loadR,0,theta);
 }
 return {render,model};
})();
