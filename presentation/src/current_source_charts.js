/* Six-pulse current-source waveforms: discrete topology, continuous cursor. */
'use strict';
const CurrentSourceCharts = (() => {
  const styles={
    T1:{color:'#c13b53',dash:[],alpha:.94},T3:{color:'#078795',dash:[7,4],alpha:.85},
    T5:{color:'#9367a8',dash:[2,4],alpha:.76},T2:{color:'#ba8743',dash:[8,3,2,3],alpha:.78},
    T4:{color:'#547c86',dash:[11,4],alpha:.71},T6:{color:'#235e9b',dash:[3,3,10,3],alpha:.86}
  };
  const base={navy:'#183b4e',grid:'#e5eef2',cursor:'#b83d52',blue:'#237ca3',red:'#c63f57',teal:'#068d97'};
  function draw(canvas,p,theta,chart='scr',s=null){
    if(!canvas?.isConnected)return;
    const result=CurrentSourceModel.cycle(p);
    const bounds=canvas.getBoundingClientRect();
    const w=Math.max(180,bounds.width),h=Math.max(130,bounds.height),dpr=Math.min(2,window.devicePixelRatio||1);
    if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){
      canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
    }
    const g=canvas.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,w,h);
    if(!result.valid){
      g.font='600 12px "Segoe UI",Arial';g.fillStyle='#b43d50';
      g.fillText('OUTSIDE MODEL OPERATING RANGE',14,30);
      g.font='11px "Segoe UI",Arial';g.fillText(result.error,14,53);
      canvas.dataset.valid='false';canvas.dataset.axisClipped='false';return;
    }
    canvas.dataset.valid='true';canvas.dataset.mu=result.mu.toFixed(4);
    const {angle,data}=result;
    const transfer=CurrentSourceModel.sample(theta,p,{valid:true,mu:result.mu,mode:result.mode});
    const selected=new Set([transfer.outgoing,transfer.incoming,transfer.stationary].filter(Boolean));
    const vals=[],target=(label,values,color,dash=[],opacity=.8,width=1.7,em=false)=>vals.push({label,values,color,dash,opacity,width,em});
    let title='',hiShade=true;
    if(chart==='scr'||chart==='transfer'){
      title=chart==='transfer'?'OUTGOING · INCOMING · STATIONARY SCR CURRENTS':'ALL SIX SCR CURRENTS';
      // The common SCR-current range is independent of the selected I_dc.
      const names=chart==='transfer'&&transfer.overlap?
        [transfer.outgoing,transfer.incoming,transfer.stationary]:CurrentSourceModel.SCRS;
      names.forEach(t=>{const sty=styles[t];target(t,data.map(d=>d.scr[t]),sty.color,sty.dash,
        selected.has(t)?.98:sty.alpha,selected.has(t)?2.4:1.7,selected.has(t));});
      target('i_dc',data.map(d=>d.idc),'#23485b',[11,6],.48,1.6);
    }else if(chart==='phase'){
      title='COMMUTATING AC PHASE VOLTAGES';
      ['v_a','v_b','v_c'].forEach((label,k)=>target(label,data.map(d=>d.phase[k]),
        ['#c43f57','#068e99','#4a75a5'][k],[[],[8,4],[2,4]][k],.85,k===0?2:1.55));
      if(transfer.overlap){
        const old=(transfer.sector+5)%6,now=transfer.sector;
        const [oldHi,oldLo]=CurrentSourceModel.PAIRS[old], [nowHi,nowLo]=CurrentSourceModel.PAIRS[now];
        const outgoingPhase=oldHi===nowHi?oldLo:oldHi;
        const incomingPhase=oldHi===nowHi?nowLo:nowHi;
        const i=CurrentSourceModel.PHASES.indexOf(outgoingPhase),j=CurrentSourceModel.PHASES.indexOf(incomingPhase);
        target('v_comm',data.map(d=>d.phase[j]-d.phase[i]),'#9f7637',[7,3,2,3],.76,2.0);
      }
    }else if(chart==='power'){
      title='SIGNED CONVERTER DC VOLTAGES (I_dc: RECTIFIER TO INVERTER)';
      target('v_dc,r',angle.map(t=>LCC.sample('rectifier',t,p).dc),'#237da2',[],.9,2.0);
      target('v_dc,i',angle.map(t=>LCC.sample('inverter',t,p,LCC.OFFSET).dc),'#ba3f58',[8,4],.87,2.0);
    }else if(chart==='alphaControl'){
      title='CURRENT CONTROLLER OUTPUT · FIRING ANGLE';
      const controlled=CurrentSourceModel.controller(p);
      target('α_r',controlled.alpha,'#237fa5',[7,4],.94,2);
      hiShade=false;
    }else if(chart==='dc'){
      title='DC CURRENT AND CONVERTER VOLTAGE';
      // DC quantities share one fixed per-unit chart domain.
      target('i_dc',data.map(d=>d.idc),base.red,[],.95,2.1);
      target('v_dc',data.map(d=>d.dc),base.blue,[7,4],.86,1.8);
    }else if(chart==='rle'){
      title='RLE RESPONSE VERSUS IDEAL CONSTANT CURRENT';
      const rle=LoadCharts.model('RLE',{...p,alphaLoad:p.alphaR});const iRLE=rle.current||[];
      // The fixed current range accommodates the complete RLE slider domain.
      target('i_RLE',iRLE,'#237ea1',[8,4],.87,2);
      target('I_ref',data.map(d=>d.idc),base.red,[],.93,2.1);
    }else if(chart==='control'){
      title='CURRENT-REGULATED RLE · AVERAGED ILLUSTRATION';
      const controlled=CurrentSourceModel.controller(p);
      const mapped=controlled.current;
      // The fixed controller-current domain accounts for the minimum L and R.
      target('I_ref',controlled.ref,base.teal,[7,4],.83,2);
      target('i_dc',mapped,base.red,[],.95,2.1);
      hiShade=false;
    }
    if(!vals.length)return;
    // Global parameter extrema determine each domain, never the live sampled peaks.
    const [low,high]=FixedAxes.range(FixedAxes.sourceKind(chart));
    canvas.dataset.axisMode='fixed';
    canvas.dataset.axisPreset=FixedAxes.preset();
    canvas.dataset.axisClipped=String(vals.some(line=>FixedAxes.outside(line.values,low,high)));
    canvas.dataset.axisLimits=JSON.stringify([{kind:FixedAxes.sourceKind(chart),min:low,max:high,x:chart==='control'||chart==='alphaControl'?[0,.35]:[0,360]}]);
    const x0=46,x1=w-12,y0=44,y1=h-26;
    const N=vals[0].values.length;
    const transient=chart==='control'||chart==='alphaControl';
    const xFor=(t)=>x0+(t/(transient?.35:360))*(x1-x0);
    const yFor=v=>y1-(v-low)/(high-low)*(y1-y0);
    g.fillStyle='#fafdfe';g.fillRect(0,0,w,h);
    g.fillStyle=base.navy;g.font='600 10px "Segoe UI",Arial';g.fillText(title,9,14);
    g.font='9px "Segoe UI",Arial';
    if(hiShade){
      const windows=CurrentSourceModel.windows(p,theta,result.mu);
      g.fillStyle=transfer.overlap?'rgba(192,92,57,.18)':'rgba(0,147,160,.105)';
      for(const win of windows){
        g.fillRect(xFor(win[0]),y0,xFor(win[1])-xFor(win[0]),y1-y0);
      }
    }else{
      g.fillStyle='rgba(0,145,159,.11)';g.fillRect(xFor(.08),y0,x1-xFor(.08),y1-y0);
    }
    const ticks=transient?[0,.05,.10,.15,.20,.25,.30,.35]:[0,60,120,180,240,300,360];
    for(const t of ticks){const x=xFor(t);g.strokeStyle=base.grid;g.lineWidth=.8;
      g.beginPath();g.moveTo(x,y0);g.lineTo(x,y1);g.stroke();
      g.fillStyle='#6a8391';g.font='normal 9px "Segoe UI",Arial';
      g.fillText(transient?t.toFixed(2)+' s':t+'°',Math.min(x1-26,x-8),h-9);
    }
    for(let j=0;j<=4;j++){
      const y=y0+(y1-y0)*j/4;g.strokeStyle='#e3ecf1';g.beginPath();g.moveTo(x0,y);g.lineTo(x1,y);g.stroke();
      g.fillStyle='#697e8e';g.fillText((high-(high-low)*j/4).toFixed(2),2,y+3);
    }
    if(low<0&&high>0){g.strokeStyle='#b2c1c8';g.setLineDash([2,3]);
      g.beginPath();g.moveTo(x0,yFor(0));g.lineTo(x1,yFor(0));g.stroke();g.setLineDash([]);}
    vals.forEach(line=>{
      g.save();g.strokeStyle=line.color;g.globalAlpha=line.opacity;g.lineWidth=line.width;g.setLineDash(line.dash);
      g.beginPath();let pen=false;
      line.values.forEach((v,k)=>{
        if(!Number.isFinite(v)){pen=false;return;}
        const xx=x0+k/(line.values.length-1)*(x1-x0),yy=Math.min(y1+2,Math.max(y0-2,yFor(v)));
        if(!pen){g.moveTo(xx,yy);pen=true;}else g.lineTo(xx,yy);
      });g.stroke();g.restore();
    });
    if(hiShade){const cursor=xFor(theta);g.save();g.strokeStyle=base.cursor;g.setLineDash([4,4]);
      g.globalAlpha=.85;g.lineWidth=1.3;g.beginPath();g.moveTo(cursor,y0);g.lineTo(cursor,y1);g.stroke();g.restore();}
    // Legibility depends on dashes and opacity, not just color.
    let lx=10;for(const l of vals){
      const required=20+(l.label.length+1)*6.1;if(lx+required>w-5)break;
      g.save();g.strokeStyle=l.color;g.globalAlpha=l.opacity;g.setLineDash(l.dash);
      g.lineWidth=l.width;g.beginPath();g.moveTo(lx,29);g.lineTo(lx+15,29);g.stroke();g.restore();
      MathUI.paint(g,l.label,lx+18,32,{size:9,color:base.navy});lx+=required;
    }
    canvas.dataset.station=p._csSide||'rectifier';
    canvas.dataset.plotMode=chart;
    canvas.dataset.lines=JSON.stringify(vals.map(x=>x.label));
    canvas.dataset.outgoing=transfer.outgoing||'';
    canvas.dataset.incoming=transfer.incoming||'';
  }
  return {draw};
})();
