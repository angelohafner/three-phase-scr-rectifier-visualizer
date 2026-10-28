/* Offline mathematical labeling with upright digits, descriptors and units. */
'use strict';
const MathUI=(()=>{
 const esc=x=>String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
 const v=(letter,sub='')=>`<span class="math-var">${esc(letter)}${sub?`<sub class="math-sub">${esc(sub)}</sub>`:''}</span>`;
 const unit=x=>`<span class="math-unit">${esc(x)}</span>`;
 const num=x=>`<span class="math-number">${esc(x)}</span>`;
 const angle=(symbol,value,sub='')=>`${v(symbol,sub)} = ${num(Number(value).toFixed(1))}${unit('°')}`;
 const formula=mode=>({
  R:`${v('i','dc')} = ${v('v','dc')} / ${v('R')}`,
  RL:`${v('L')} d${v('i','dc')}/d${v('t')} + ${v('R')}${v('i','dc')} = ${v('v','dc')}`,
  LE:`${v('L')} d${v('i','dc')}/d${v('t')} = ${v('v','dc')} − ${v('E')}`,
  RLE:`${v('L')} d${v('i','dc')}/d${v('t')} + ${v('R')}${v('i','dc')} = ${v('v','dc')} − ${v('E')}`
 }[mode]||'');
 function paint(ctx,label,x,y,{size=10,color='#35536c'}={}){
   const saveAlign=ctx.textAlign;
   const value=String(label);
   let symbol=null,sub='';
   const a=value.match(/^([vi])_(.+)$/);
   if(a){symbol=a[1];sub=a[2];}
   else if(/^([vi])(?:[ₐᵦ𝒸]|[ₐᵦ𝒸][ₐᵦ𝒸])+$/.test(value)){symbol=value[0];sub=value.slice(1);}
   else if(/^([αμγθRLE])$/.test(value)){symbol=value;}
   if(symbol){
     ctx.font=`italic ${size}px "Cambria Math","STIX Two Math",Georgia,serif`;
     ctx.fillStyle=color;ctx.fillText(symbol,x,y);
     if(sub){const w=ctx.measureText(symbol).width;ctx.font=`normal ${size*.76}px "Segoe UI",Arial,sans-serif`;ctx.fillText(sub,x+w+.3,y+3.2);}
   } else {
     ctx.font=`normal ${size}px "Segoe UI",Arial,sans-serif`;ctx.fillStyle=color;ctx.fillText(value,x,y);
   }
   ctx.textAlign=saveAlign;
 }
 return {v,unit,num,angle,formula,paint};
})();
