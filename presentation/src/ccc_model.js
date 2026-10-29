/* Six-pulse stiff-DC-current capacitor-commutated bridge with periodic shooting. */
'use strict';
const CCCModel=(()=>{
 const PI=Math.PI, PAIRS=[[0,2],[1,2],[1,0],[2,0],[2,1],[0,1]], SCR=['T1','T3','T5','T2','T4','T6'];
 const PHASES=['a','b','c'], RAD=PI/180;
 const defaults={alpha:15,idc:.8,vPeak:1,LmH:.24,CmF:26,R:.012,f:60,qShunt:.4};
 const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
 const volt=(t,p)=>[0,1,2].map(k=>p.vPeak*Math.cos(t+p.alpha*RAD-k*2*PI/3));
 function prepare(user){const p={...defaults,...user};const omega=2*PI*p.f;
   p.XL=omega*p.LmH/1000;p.XC=p.CmF>0?1/(omega*p.CmF/1000):0;
   if(!(p.f>0&&p.idc>0&&p.vPeak>0&&p.LmH>0&&p.R>=0&&p.CmF>=0&&p.alpha>=0&&p.alpha<=90))throw Error('Invalid physical parameter');
   return p;
 }
 function commInfo(sector){let prev=PAIRS[(sector+5)%6],next=PAIRS[sector];
   const up=prev[0]!==next[0],out=up?prev[0]:prev[1],incoming=up?next[0]:next[1],stationary=up?prev[1]:prev[0];
   return {up,out,incoming,stationary,sign:up?1:-1,sector};
 }
 function currentArray(info,s,p,sect=5){let arr=[0,0,0];if(!info){let pair=PAIRS[sect];arr[pair[0]]=p.idc;arr[pair[1]]=-p.idc;return arr;}
   let nxt=PAIRS[info.sector],outgoing=info.sign*p.idc-s;
   arr[info.incoming]=s;arr[info.out]=outgoing;arr[info.stationary]=-info.sign*p.idc;
   return arr;
 }
 function rhs(theta,vC,s,info,p,sect){const a=volt(theta,p),i=currentArray(info,s,p,sect);
   const derivatives=i.map(i=>p.XC*i);
   if(!info)return {dVC:derivatives,dI:0,currents:i};
   const {incoming,out,sign}=info;
   const di=(a[incoming]-a[out]-(vC[incoming]-vC[out])-p.R*(i[incoming]-i[out]))/(2*p.XL);
   return {dVC:derivatives,dI:di,currents:i};
 }
 function integrate(t,vC,s,info,p,h,sect){
   let k1=rhs(t,vC,s,info,p,sect),k2=rhs(t+h/2,vC.map((v,k)=>v+h*k1.dVC[k]/2),s+h*k1.dI/2,info,p,sect);
   let k3=rhs(t+h/2,vC.map((v,k)=>v+h*k2.dVC[k]/2),s+h*k2.dI/2,info,p,sect);
   let k4=rhs(t+h,vC.map((v,k)=>v+h*k3.dVC[k]),s+h*k3.dI,info,p,sect);
   const vNext=vC.map((v,k)=>v+h*(k1.dVC[k]+2*k2.dVC[k]+2*k3.dVC[k]+k4.dVC[k])/6);
   const sNext=s+h*(k1.dI+2*k2.dI+2*k3.dI+k4.dI)/6;
   return [vNext,sNext];
 }
 function cycle(p,initial,store=false){const N=p.samplesPerCycle||1800;let vc=initial.slice(),sect=-1,info=null,s=0,mu=Array(6).fill(NaN),traces=[],fail='',finished=0;
   for(let k=0;k<N;k++){
     let angle=k*2*PI/N, nextSector=Math.floor(k/(N/6));
     if(nextSector!==sect){
       if(info){fail='Commutation did not complete before the next 60° firing event.';break;}
       sect=nextSector;info=commInfo(sect);s=0;
       const k0=rhs(angle,vc,s,info,p,sect);
       if(k0.dI*info.sign < 1e-8){fail='Insufficient forward commutating voltage at the firing instant.';break;}
     }
     let current=currentArray(info,s,p,sect);
     let waves=volt(angle,p);
     const csource=waves.map((v,j)=>v-vc[j]);
     let dv=info?rhs(angle,vc,s,info,p,sect).dI:0;
     let plus,minus;
     if(info){const u=info.up, phases=[info.out,info.incoming];
       const vgroup=(csource[phases[0]]-p.R*current[phases[0]]-p.XL*(-dv)+
                     csource[phases[1]]-p.R*current[phases[1]]-p.XL*dv)/2;
       if(u){plus=vgroup;let lower=info.stationary;minus=csource[lower]+p.R*p.idc;}
       else {minus=vgroup;let upper=info.stationary;plus=csource[upper]-p.R*p.idc;}
     }else{let pair=PAIRS[sect];plus=csource[pair[0]]-p.R*p.idc;minus=csource[pair[1]]+p.R*p.idc;}
     if(store)traces.push({angle:k*360/N,source:waves,capacitors:vc.slice(),current:current.slice(),valve:csource,dc:plus-minus,
       overlap:!!info,sector:sect,transfer:info?Math.abs(s)/p.idc:1,voltageDifference:info?(csource[info.incoming]-csource[info.out]):0,
       outgoing:info?.out??-1,incoming:info?.incoming??-1});
     const [newvc,news]=integrate(angle,vc,s,info,p,2*PI/N,sect);vc=newvc;
     if(info){s=news;const target=info.sign*p.idc;
       if(s*info.sign< -1e-5){fail='Attempted thyristor reverse-current conduction.';break;}
       if(s*info.sign>=p.idc){mu[sect]=(k+1)*360/N-sect*60;info=null;finished++;}
     }
   }
   if(!fail&&info)fail='Unfinished commutation at the cycle boundary.';
   if(!fail&&finished!==6)fail='The bridge completed fewer than six valid commutations.';
   return {valid:!fail,error:fail,end:vc,initial,mu,traces};
 }
 function estimate(p){if(!p.XC)return [0,0,0];let N=p.samplesPerCycle||1800,p0={...p,XC:0},x=cycle(p0,[0,0,0],true);
   if(!x.valid)return [0,0,0];let integral=[0,0,0],means=[0,0,0];
   for(let k=0;k<x.traces.length;k++){
     let i=x.traces[k].current;
     for(let j=0;j<3;j++){integral[j]+=i[j]*p.XC*2*PI/N;means[j]+=integral[j];}
   }
   let init=means.map(z=>-z/N),average=init.reduce((a,b)=>a+b,0)/3;
   return init.map(v=>v-average);
 }
 function shooting(p){if(!p.XC){let x=cycle(p,[0,0,0],true);return {...x,converged:x.valid,iterations:0,residual:0};}
   let x=estimate(p);const eps=2e-4;
   for(let n=0;n<18;n++){
     let a=cycle(p,x);
     if(!a.valid)return {...a,converged:false,iterations:n,residual:NaN};
     const f=[a.end[0]-x[0],a.end[1]-x[1]],norm=Math.max(...f.map(Math.abs));
     if(norm<eps){let full=cycle(p,x,true);return {...full,converged:true,residual:norm,iterations:n};}
     let delta=1e-3,col=[];
     for(let j=0;j<2;j++){
       let y=x.slice();y[j]+=delta;y[2]-=delta;let b=cycle(p,y);
       if(!b.valid)return {...a,converged:false,error:'Periodic shooting perturbation encountered an invalid commutation.',iterations:n,residual:norm};
       col.push([(b.end[0]-y[0]-f[0])/delta,(b.end[1]-y[1]-f[1])/delta]);
     }
     const det=col[0][0]*col[1][1]-col[1][0]*col[0][1];
     if(Math.abs(det)<1e-8)return {...a,converged:false,error:'Periodic shooting Jacobian is singular.',iterations:n,residual:norm};
     const step0=(f[0]*col[1][1]-f[1]*col[1][0])/det,step1=(col[0][0]*f[1]-col[0][1]*f[0])/det;
     let accepted=false;
     for(let mult of [1,.5,.25,.125,.0625]){
       let y=[x[0]-mult*step0,x[1]-mult*step1];y.push(-y[0]-y[1]);
       let b=cycle(p,y);
       if(b.valid&&Math.max(Math.abs(b.end[0]-y[0]),Math.abs(b.end[1]-y[1]))<norm){x=y;accepted=true;break;}
     }
     if(!accepted)return {...a,converged:false,error:'Periodic shooting could not reduce the capacitor-voltage mismatch.',iterations:n,residual:norm};
   }
   return {valid:false,converged:false,error:'No periodic capacitor-voltage solution was found.',iterations:18};
 }
 function powers(traces,p){if(!traces?.length)return {};
   const d=2*PI/traces.length,coeff=(j,field)=>{
     let re=0,im=0;for(const q of traces){const sig=q[field][j];re+=sig*Math.cos(q.angle*RAD);im-=sig*Math.sin(q.angle*RAD);}
     return [2*re/traces.length,2*im/traces.length];
   };
   let P=0,Q=0,pr=0;
   for(let j=0;j<3;j++){
     const [vr,vi]=coeff(j,'source'),[ir,ii]=coeff(j,'current');
     P+=(vr*ir+vi*ii)/2; Q+=(vi*ir-vr*ii)/2;
   }
   for(const q of traces)pr+=q.dc*p.idc/traces.length;
   const losses=traces.reduce((sum,x)=>sum+p.R*x.current.reduce((k,i)=>k+i*i,0),0)/traces.length;
   const base=1.5;
   const [vr,vi]=coeff(0,'source'),[ir,ii]=coeff(0,'current');
   const phi=(Math.atan2(vi,vr)-Math.atan2(ii,ir))*180/PI;
   return {phasor:{v:[vr,vi],i:[ir,ii],angle:phi},P:P/base,Q:Q/base,S:Math.hypot(P,Q)/base,pf:P/Math.max(1e-8,Math.hypot(P,Q)),
     bridge:pr/base,loss:losses/base,imbalance:(P-pr-losses)/base,
     Qshunt:p.qShunt*p.vPeak*p.vPeak,Qgrid:Q/base-p.qShunt*p.vPeak*p.vPeak};
 }
 function solve(input){let p;try{p=prepare(input);}catch(e){return {valid:false,error:e.message};}
   const result=shooting(p);if(!result.valid||!result.converged)return {valid:false,error:result.error||'No periodic solution',params:p,iterations:result.iterations,residual:result.residual};
   return {...result,params:p,powers:powers(result.traces,p),avgMu:result.mu.reduce((a,b)=>a+b,0)/6};
 }
 return {solve,cycle,prepare,estimate,powers,defaults,PAIRS,SCR};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=CCCModel;