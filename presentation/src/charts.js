/* Canvas plot renderer: live signals derived from the same conceptual model. */
'use strict';
const ChartView = (() => {
  const palette={red:'#d92c46',redLight:'#e88d90',teal:'#00a6b2',blue:'#287fb4',gold:'#ce9338',grey:'#aabac6',ink:'#3c5870',grid:'#e6edf2'};
  function makeSeries(side,params,mode,active,theta){
    const thetas=Array.from({length:361},(_,i)=>i);
    const samples=thetas.map(theta=>side==='hvdc'?{
      r:LCC.sample('rectifier',theta,params),i:LCC.sample('inverter',theta,params,LCC.OFFSET)
    }:LCC.sample(side,theta,params));
    const unit='p.u.';
    function obj(label,color,fn,emphasis=false){return {label,color,values:samples.map(fn),emphasis};}
    const s=side==='hvdc';
    const rActive=new Set(s?LCC.stateInfo(active.r).scrs:[]),iActive=new Set(s?LCC.stateInfo(active.i).scrs:[]);
    const allActive=new Set(!s?LCC.stateInfo(active.id).scrs:[]);
    const groups=[];
    if(mode==='scrv'){
      const configs=s?[['Rectifier','rectifier',0,'r'],['Inverter','inverter',LCC.OFFSET,'i']]:
        [[side==='rectifier'?'Rectifier':'Inverter',side,0,'']];
      const strokeColors=[palette.red,palette.blue,palette.teal,'#8a64a5','#aa7834','#32866f'];
      const strokes=[[],[8,4],[2,3],[9,3,2,3],[5,4,1,4],[3,3,8,3]];
      for(const [name,station,offset,key] of configs){
        const volt=SCRVoltage.series(station,params,offset);
        const st=LCC.at(theta,station==='rectifier'?params.muR:params.muI,offset);
        const selected=new Set(LCC.stateInfo(st.id).scrs);
        groups.push({name:name+' · SCR anode-to-cathode voltages (pu)',
          min:-2*params.vPeak,max:2*params.vPeak,
          series:LCC.SCRS.map((t,j)=>({label:'v_{AK,'+t.substring(1)+'}',
            color:strokeColors[j],dash:strokes[j],values:volt[t],
            emphasis:params.scrFocus==='all'?selected.has(t):t===params.scrFocus,
            opacity:params.scrFocus==='all'?.79:(t===params.scrFocus?.96:.16)}))});
      }
      return groups;
    }
    if(s){
      if(mode==='phase'||mode==='line'){
        const key=mode==='phase'?'phase':'line';
        const labels=key==='phase'?['vₐ','vᵦ','v𝒸']:['vₐᵦ','vᵦ𝒸','v𝒸ₐ'];
        const colors=[palette.red,palette.blue,palette.teal];
        for(const [key2,name] of [['r','Rectifier'],['i','Inverter']]){
          groups.push({name:name+' · '+(mode==='phase'?'Phase voltages':'Line voltages')+' ('+unit+')',unit,
            min:-2*params.vPeak,max:2*params.vPeak,
            series:labels.map((label,j)=>obj(label,colors[j],d=>d[key2][key][j]))});
        }
        groups.push({name:'DC pole current ('+unit+')',min:0,max:Math.max(1.2,params.idc*1.3),series:[obj('i_dc',palette.red,d=>d.r.idc)]});
      }else if(mode==='dc'||mode==='idc'){
        groups.push({name:'Converter DC-side voltage ('+unit+')',min:-2*params.vPeak,max:2*params.vPeak,
          series:[obj('v_dc,r',palette.blue,d=>d.r.dc),obj('v_dc,i',palette.red,d=>d.i.dc)]});
        groups.push({name:'Illustrative DC current ('+unit+')',min:0,max:Math.max(1.2,params.idc*1.3),
          series:[obj('i_dc,r',palette.blue,d=>d.r.idc),obj('i_dc,i',palette.red,d=>d.i.idc)]});
        groups.push({name:'Power flow (conceptual)',min:-2.2*params.vPeak*params.idc,max:2.2*params.vPeak*params.idc,
          series:[obj('p_r',palette.blue,d=>d.r.dc*d.r.idc),obj('p_i',palette.red,d=>d.i.dc*d.i.idc)]});
      }else{
        groups.push({name:'Converter DC voltage ('+unit+')',min:-2*params.vPeak,max:2*params.vPeak,series:[obj('v_dc,r',palette.blue,d=>d.r.dc),obj('v_dc,i',palette.red,d=>d.i.dc)]});
        groups.push({name:'Rectifier SCR currents ('+unit+')',min:0,max:params.idc*1.25,series:LCC.SCRS.map(t=>obj('R'+t,rActive.has(t)?palette.red:palette.grey,d=>d.r.scr[t],rActive.has(t)))});
        groups.push({name:'Inverter SCR currents ('+unit+')',min:0,max:params.idc*1.25,series:LCC.SCRS.map(t=>obj('I'+t,iActive.has(t)?palette.red:palette.grey,d=>d.i.scr[t],iActive.has(t)))});
      }
    }else{
      const sfn=d=>d;
      if(mode==='phase'||mode==='line'){
        const key=mode==='phase'?'phase':'line';
        groups.push({name:(mode==='phase'?'Phase-to-neutral voltages':'Line-to-line voltages')+' ('+unit+')',min:-2*params.vPeak,max:2*params.vPeak,series:[0,1,2].map((j)=>obj((key==='phase'?['vₐ','vᵦ','v𝒸']:['vₐᵦ','vᵦ𝒸','v𝒸ₐ'])[j],[palette.red,palette.blue,palette.teal][j],d=>d[key][j]))});
        groups.push({name:'AC phase currents ('+unit+')',min:-params.idc*1.35,max:params.idc*1.35,series:[0,1,2].map(j=>obj(['iₐ','iᵦ','i𝒸'][j],[palette.red,palette.blue,palette.teal][j],d=>d.ac[j]))});
        groups.push({name:'DC-side voltage ('+unit+')',min:-2*params.vPeak,max:2*params.vPeak,series:[obj('v_dc',palette.red,d=>d.dc)]});
      }else if(mode==='scr'){
        groups.push({name:'Six SCR currents ('+unit+')',min:0,max:params.idc*1.25,series:LCC.SCRS.map(t=>obj(t,allActive.has(t)?palette.red:palette.grey,d=>d.scr[t],allActive.has(t)))});
        groups.push({name:'AC phase currents ('+unit+')',min:-params.idc*1.35,max:params.idc*1.35,series:[0,1,2].map(j=>obj(['iₐ','iᵦ','i𝒸'][j],[palette.red,palette.blue,palette.teal][j],d=>d.ac[j]))});
      }else if(mode==='dc'||mode==='idc'){
        groups.push({name:'DC voltage ('+unit+')',min:-2*params.vPeak,max:2*params.vPeak,series:[obj('v_dc',palette.red,d=>d.dc),obj('v_ideal',palette.grey,d=>d.dcIdeal)]});
        groups.push({name:'DC pole current ('+unit+')',min:0,max:params.idc*1.3,series:[obj('i_dc',palette.red,d=>d.idc)]});
      }else{
        groups.push({name:'Phase voltages ('+unit+')',min:-params.vPeak*1.2,max:params.vPeak*1.2,series:[0,1,2].map(j=>obj(['vₐ','vᵦ','v𝒸'][j],[palette.red,palette.blue,palette.teal][j],d=>d.phase[j]))});
        groups.push({name:'SCR currents ('+unit+')',min:0,max:params.idc*1.25,series:LCC.SCRS.map(t=>obj(t,allActive.has(t)?palette.red:palette.grey,d=>d.scr[t],allActive.has(t)))});
        groups.push({name:'DC voltage & current ('+unit+')',min:-2*Math.max(params.vPeak,params.idc),max:2*Math.max(params.vPeak,params.idc),series:[obj('v_dc',palette.blue,d=>d.dc),obj('i_dc',palette.red,d=>d.idc)]});
      }
    }
    return groups;
  }
  function render(canvas,side,params,windows,active,theta,mode='overview'){
    if(!canvas||!canvas.isConnected)return;
    const box=canvas.getBoundingClientRect(), w=Math.max(180,box.width),h=Math.max(120,box.height);
    const dpr=Math.min(2,window.devicePixelRatio||1); const iw=Math.round(w*dpr),ih=Math.round(h*dpr);
    if(canvas.width!==iw||canvas.height!==ih){canvas.width=iw;canvas.height=ih;}
    let g=canvas.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,w,h);
    const groups=makeSeries(side,params,mode,active,theta),n=groups.length;
    let padTop=8,padBottom=13,gap=6,row=(h-padTop-padBottom-(n-1)*gap)/n;
    const x0=38,x1=w-15,plotWidth=x1-x0;
    function xPos(angle){return x0+(angle/360)*plotWidth;}
    for(let j=0;j<n;j++){
      const group=groups[j],top=padTop+j*(row+gap),header=23;
      const y0=top+header,y1=top+row-19,plotHeight=Math.max(24,y1-y0);
      const ys=v=>y1-(v-group.min)/(group.max-group.min)*plotHeight;
      g.fillStyle=j%2===0?'#fbfdff':'#f7fafc';g.fillRect(0,top,w,row);
      g.fillStyle='#38566b';g.font='700 11px "Segoe UI",Arial,sans-serif';g.fillText(group.name,12,top+14);
      for(let ang=0;ang<=360;ang+=60){const x=xPos(ang);g.strokeStyle=palette.grid;g.lineWidth=1;g.beginPath();g.moveTo(x,y0);g.lineTo(x,y1);g.stroke();g.fillStyle='#7b92a3';g.font='9px Arial';g.fillText(String(ang)+'°',Math.min(w-25,x-7),y1+12);}
      for(let q=0;q<=4;q++){let yy=y1-q*plotHeight/4;g.strokeStyle='#edf2f6';g.beginPath();g.moveTo(x0,yy);g.lineTo(x1,yy);g.stroke();}
      for(const [lo,hi] of windows||[]){if(hi<=lo)continue;g.fillStyle='rgba(220,53,75,.095)';g.fillRect(xPos(lo),y0,xPos(hi)-xPos(lo),plotHeight);}
      const yy0=ys(0);if(yy0>=y0&&yy0<=y1){g.strokeStyle='#b2c5d0';g.lineWidth=1;g.beginPath();g.moveTo(x0,yy0);g.lineTo(x1,yy0);g.stroke();}
      const st=group.series.slice().sort((a,b)=>Number(a.emphasis)-Number(b.emphasis));
      for(const [index,series] of st.entries()){
        g.beginPath();let started=false;
        for(let k=0;k<series.values.length;k++){
          const val=series.values[k];
          if(!Number.isFinite(val)){started=false;continue;}
          const xx=xPos(k),yy=ys(val);
          if(!started)g.moveTo(xx,yy);else g.lineTo(xx,yy);
          started=true;
        }
        g.strokeStyle=series.color;
        g.lineWidth=series.emphasis?2.1:1.5;
        g.setLineDash(series.dash||[[],[7,3],[2,3],[9,3,2,3],[5,3,1,3],[3,3,9,3]][index%6]);
        g.globalAlpha=series.opacity??(series.color===palette.grey?.55:.79);
        g.stroke();g.setLineDash([]);g.globalAlpha=1;
      }
      const cursor=xPos(theta);g.strokeStyle='#c72741';g.setLineDash([5,3]);g.lineWidth=1.5;g.beginPath();g.moveTo(cursor,y0);g.lineTo(cursor,y1);g.stroke();g.setLineDash([]);
      g.fillStyle='#748c9c';g.font='10px Arial';g.fillText(Number(group.max).toFixed(1),5,y0+7);g.fillText(Number(group.min).toFixed(1),5,y1);
      const maxLegend=(mode==='scr'||mode==='scrv')?6:4;
      const legend=mode==='scrv'?group.series:(group.series.filter(s=>s.emphasis).length?group.series.filter(s=>s.emphasis):group.series);
      let lx=Math.max(145,w-(maxLegend*56)-14);g.font='10px Arial';
      for(const item of legend.slice(0,maxLegend)){g.strokeStyle=item.color;g.lineWidth=2;g.globalAlpha=.82;g.setLineDash(item.dash||[]);g.beginPath();g.moveTo(lx,top+8);g.lineTo(lx+11,top+8);g.stroke();g.setLineDash([]);g.globalAlpha=1;const lab=TechnicalMath.draw(g,lx+13,top+13,item.label,{size:10,color:'#4b6678'});lx+=Math.max(47,lab+24);if(lx>w-25)break;}
    }
    canvas.dataset.plotLeft=String(x0);canvas.dataset.plotRight=String(x1);
  }
  return {render};
})();
