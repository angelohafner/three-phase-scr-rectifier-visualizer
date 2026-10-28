/* Ideal SCR half-wave R/RL educational model, with analytic natural extinction. */
'use strict';
const HalfWave = (() => {
  const RAD=Math.PI/180;
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const color={red:'#C33D53',blue:'#176F9E',teal:'#068F99',gold:'#B58439',grey:'#879AA4',grid:'#E3EDF0',ink:'#23485C'};
  function config(params,load='RL'){
    return {load,alpha:+params.hAlpha,R:+params.hR,L:load==='RL'?+params.hL:0,
      V:+params.hV,f:+(params.hFrequency||60)};
  }
  function model(settings){
    if (!['R','RL'].includes(settings.load) || !(settings.alpha>=0&&settings.alpha<180) ||
        !(settings.R>0&&settings.L>=0&&settings.V>0&&settings.f>0))throw Error('Invalid half-wave settings');
    const R=settings.R,L=settings.load==='RL'?settings.L/1000:0,V=settings.V;
    const alpha=settings.alpha*RAD,omega=2*Math.PI*settings.f;
    const phi=Math.atan2(omega*L,R),z=Math.hypot(R,omega*L);
    function iRaw(t){
      if(L===0)return V*Math.sin(t)/R;
      return V/z*(Math.sin(t-phi)-Math.sin(alpha-phi)*Math.exp(-(t-alpha)*R/(omega*L)));
    }
    let beta=180;
    if(L>0){
      let low=Math.PI,high=2*Math.PI;
      if(iRaw(low)>0){
        for(let k=0;k<90;k++){
          const mid=(low+high)/2;
          if(iRaw(mid)>0)low=mid;else high=mid;
        }
        beta=(low+high)/(2*RAD);
      }
    }
    function at(angle){
      const theta=((angle%360)+360)%360,t=theta*RAD;
      const vs=V*Math.sin(t);
      let on=theta>=settings.alpha&&theta<beta;
      let i=on?Math.max(0,iRaw(t)):0;
      if(i<1e-12){on=false;i=0;}
      const vo=on?vs:0,vr=R*i,vl=on&&L>0?vs-vr:0;
      return {theta,vs,vo,vr,vl,vak:on?0:vs,i,w:.5*L*i*i,on};
    }
    const sampled=Array.from({length:1441},(_,k)=>at(k*.25));
    return {config:settings,beta,at,sampled};
  }
  const cache=new Map();
  function get(params,load='RL'){
    const c=config(params,load),key=JSON.stringify(c);
    if(!cache.has(key)) {if(cache.size>12)cache.clear();cache.set(key,model(c));}
    return cache.get(key);
  }
  function view(canvas){
    const r=canvas.getBoundingClientRect();
    const width=Math.max(r.width,220),height=Math.max(r.height,180);
    const d=Math.min(2,window.devicePixelRatio||1);
    if(canvas.width!==Math.round(width*d)||canvas.height!==Math.round(height*d)){
      canvas.width=Math.round(width*d);canvas.height=Math.round(height*d);
    }
    const g=canvas.getContext('2d');g.setTransform(d,0,0,d,0,0);g.clearRect(0,0,width,height);
    return {g,width,height};
  }
  function graphPanel(g,rect,modelRef,theta,tracks,ymin,ymax,title,options={}){
    const {x,y,w,h}=rect,top=y+26,bottom=y+h-23,left=x+43,right=x+w-13;
    if(right<=left+2||bottom<=top+2)return;
    const X=a=>left+(a/360)*(right-left),Y=v=>bottom-(v-ymin)/(ymax-ymin)*(bottom-top);
    g.save();
    g.fillStyle='#FCFDFE';g.fillRect(x,y,w,h);
    g.font='600 10px "Segoe UI",Arial';g.fillStyle='#214B60';g.fillText(title,x+7,y+15);
    for(let angle=0;angle<=360;angle+=60){
      const xx=X(angle);g.strokeStyle=color.grid;g.lineWidth=.7;g.beginPath();g.moveTo(xx,top);g.lineTo(xx,bottom);g.stroke();
      g.font='9px "Segoe UI",Arial';g.fillStyle='#6E8795';g.fillText(`${angle}°`,Math.min(right-22,xx-9),bottom+14);
    }
    for(let j=0;j<=4;j++){
      const yy=top+(bottom-top)*j/4;g.beginPath();g.strokeStyle=color.grid;g.moveTo(left,yy);g.lineTo(right,yy);g.stroke();
      const v=ymax-(ymax-ymin)*j/4;g.font='8px "Segoe UI",Arial';g.fillStyle='#778B99';
      g.fillText(Math.abs(v)<1e-9?'0':v.toFixed(Math.abs(v)<1?2:0),x+4,yy+3);
    }
    const alpha=modelRef.config.alpha,beta=modelRef.beta;
    g.fillStyle='rgba(10,151,161,.075)';g.fillRect(X(alpha),top,Math.max(0,X(beta)-X(alpha)),bottom-top);
    if(beta>180.0001){
      g.fillStyle='rgba(197,141,49,.16)';g.fillRect(X(180),top,X(beta)-X(180),bottom-top);
      // On the source-voltage panel, shade its negative lobe only while current flows.
      if(options.negativeVoltage){
        const zero=Y(0);g.fillStyle='rgba(23,111,158,.16)';
        for(let a=180;a<beta;a+=.5){
          const value=modelRef.at(a).vs;
          const yy=Y(value);g.fillRect(X(a),zero,Math.max(1,X(a+.5)-X(a)),Math.max(0,yy-zero));
        }
      }
      // On the SCR-current panel, emphasize positive current after source reversal.
      if(options.positiveCurrent){
        g.fillStyle='rgba(195,61,83,.17)';const zero=Y(0);
        for(let a=180;a<beta;a+=.5){
          const yy=Y(modelRef.at(a).i);g.fillRect(X(a),yy,Math.max(1,X(a+.5)-X(a)),Math.max(0,zero-yy));
        }
      }
    }
    if(ymin<0&&ymax>0){g.strokeStyle='#B7C7CE';g.lineWidth=1;g.beginPath();g.moveTo(left,Y(0));g.lineTo(right,Y(0));g.stroke();}
    const dash=[[],[7,3],[2,3],[8,4,2,4]];
    for(let n=0;n<tracks.length;n++){
      const track=tracks[n];g.beginPath();g.strokeStyle=track.color;g.lineWidth=track.width||1.7;
      g.globalAlpha=track.opacity||.85;g.setLineDash(track.dash||dash[n%4]);
      let started=false;
      modelRef.sampled.forEach((q,k)=>{
        let val=q[track.key];if(!Number.isFinite(val)){started=false;return;}
        const xx=X(k*.25),yy=clamp(Y(val),top-.8,bottom+.8);
        if(!started){g.moveTo(xx,yy);started=true;}else g.lineTo(xx,yy);
      });g.stroke();g.globalAlpha=1;
    }
    g.setLineDash([]);
    const lines=[{a:alpha,color:color.teal,name:'α',dash:[4,5]},
                 {a:180,color:color.gold,name:'180°',dash:[2,4]}];
    // R-load extinction coincides with the fixed 180-degree zero crossing.
    if(beta>180.0001)lines.push({a:beta,color:color.red,name:'β',dash:[5,3]});
    for(const line of lines){
      const xx=X(line.a);g.beginPath();g.strokeStyle=line.color;g.setLineDash(line.dash);g.lineWidth=1.4;
      g.moveTo(xx,top);g.lineTo(xx,bottom);g.stroke();g.setLineDash([]);
      g.font='600 9px "Segoe UI",Arial';g.fillStyle=line.color;
      const fx=clamp(xx+2,left,right-25);
      if((line.name==='α'||line.name==='β')&&typeof MathUI!=='undefined'){
        MathUI.paint(g,line.name,fx,top+10,{size:10,color:line.color});
      } else g.fillText(line.name,fx,top+10);
    }
    g.beginPath();g.strokeStyle=color.red;g.lineWidth=1.5;g.setLineDash([3,3]);
    g.moveTo(X(theta),top);g.lineTo(X(theta),bottom);g.stroke();g.setLineDash([]);
    const topLegend=tracks.slice(0,3);let lx=right-10;
    for(const t of topLegend.reverse()){
      const label=t.label;lx-=49+(label.length>3?label.length*2:0);
      if(lx<left+55)break;
      g.strokeStyle=t.color;g.globalAlpha=t.opacity||.9;g.setLineDash(t.dash||[]);g.lineWidth=2;
      g.beginPath();g.moveTo(lx,y+11);g.lineTo(lx+14,y+11);g.stroke();g.setLineDash([]);g.globalAlpha=1;
      if(typeof MathUI!=='undefined')MathUI.paint(g,label,lx+17,y+15,{size:10,color:color.ink});
      else {g.font='10px Georgia';g.fillText(label,lx+17,y+15);}
    }
    g.restore();
  }
  function render(canvas,params,theta,lesson='rl',graphMode='overview'){
    if(!canvas||!canvas.isConnected)return;
    const {g,width:w,height:h}=view(canvas),rect={x:0,y:0,w,h};
    const rl=get(params,'RL'),r=get(params,'R'),compare=lesson==='compare';
    // Use the electrical load model that matches the circuit drawn on the slide.
    const resistiveOnly=['scr_intro','r_circuit','r_delay'].includes(lesson);
    const m=resistiveOnly?r:rl;
    // No inductor-only quantities may appear when the circuit contains only R.
    if(resistiveOnly&&graphMode==='energy')graphMode='overview';
    const v=m.config.V, imax=Math.max(1.2*v/m.config.R,rl.sampled.reduce((p,q)=>Math.max(p,q.i),0)*1.08);
    const vLimit=1.16*v;
    if(compare){
      const width=(w-12)/2,height=(h-8)/2;
      for(const [j,item] of [r,rl].entries()){
        const x=3+j*(width+6),name=j?'RL':'R';
        graphPanel(g,{x,y:0,w:width,h:height},item,theta,[
          {key:'vs',label:'v_s',color:color.blue,dash:[8,4]},
          {key:'vo',label:'v_o',color:color.red}],-vLimit,vLimit,`${name} · VOLTAGE (V)`,{negativeVoltage:true});
        graphPanel(g,{x,y:height+7,w:width,h:height},item,theta,[
          {key:'i',label:'i_T',color:color.red}],-.12*imax,imax,`${name} · CURRENT (A)`,{positiveCurrent:true});
      }return;
    }
    let specs=[];
    if(graphMode==='voltages')specs=[
      [[{key:'vs',label:'v_s',color:color.blue,dash:[8,3]},
        {key:'vo',label:'v_o',color:color.red}],-vLimit,vLimit,'SOURCE / OUTPUT VOLTAGE (V)',{negativeVoltage:true}],
      [resistiveOnly?
        [{key:'vr',label:'v_R',color:color.red}]:
        [{key:'vr',label:'v_R',color:color.red},
         {key:'vl',label:'v_L',color:color.teal,dash:[2,3]}],
        -vLimit,vLimit,resistiveOnly?'RESISTOR VOLTAGE (V)':'LOAD COMPONENT VOLTAGES (V)',{}]
    ];
    else if(graphMode==='vak')specs=[
      [[{key:'vak',label:'v_AK',color:color.blue}],-vLimit,vLimit,'SCR ANODE–CATHODE VOLTAGE (V)',{}],
      [[{key:'i',label:'i_T',color:color.red}],-.12*imax,imax,'SCR CURRENT (A)',{positiveCurrent:true}]
    ];
    else if(graphMode==='energy')specs=[
      [[{key:'i',label:'i_T',color:color.red}],-.12*imax,imax,'SCR CURRENT (A)',{positiveCurrent:true}],
      [[{key:'w',label:'W_L',color:color.teal}],0,Math.max(.2,rl.sampled.reduce((p,q)=>Math.max(p,q.w),0)*1.14),'STORED MAGNETIC ENERGY (J)',{}]
    ];
    else specs=[
      [[{key:'vs',label:'v_s',color:color.blue,dash:[8,3],opacity:.76},
        {key:'vo',label:'v_o',color:color.red}],-vLimit,vLimit,'AC SOURCE / LOAD VOLTAGE (V)',{negativeVoltage:true}],
      [[{key:'i',label:'i_T',color:color.red}],-.12*imax,imax,'SCR CURRENT (A)',{positiveCurrent:true}],
      [resistiveOnly?
        [{key:'vak',label:'v_AK',color:color.blue,dash:[8,3],opacity:.82}]:
        [{key:'vak',label:'v_AK',color:color.blue,dash:[8,3],opacity:.82},
         {key:'vl',label:'v_L',color:color.teal,dash:[2,3],opacity:.82}],
        -vLimit,vLimit,resistiveOnly?'SCR VOLTAGE (V)':'SCR / INDUCTOR VOLTAGE (V)',{}]
    ];
    // Expose only the rendered signals for accessibility and automated checks.
    canvas.dataset.activeLoad=m.config.load;
    canvas.dataset.signals=JSON.stringify(specs.flatMap(([lines])=>lines.map(t=>t.key)));
    canvas.dataset.panelTitles=JSON.stringify(specs.map(([, , ,title])=>title));
    const gap=3,height=(h-gap*(specs.length-1))/specs.length;
    specs.forEach(([lines,min,max,title,opts],j)=>graphPanel(g,{x:0,y:j*(height+gap),w,h:height},m,theta,lines,min,max,title,opts));
  }
  return {config,model,get,render};
})();
