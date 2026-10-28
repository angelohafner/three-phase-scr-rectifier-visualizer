/* Dependency-free technical math labels for Canvas and inline HTML. */
'use strict';
const TechnicalMath = (() => {
  const greek={alpha:'α',gamma:'γ',mu:'μ',theta:'θ',omega:'ω',Delta:'Δ'};
  function tokens(source) {
    const a=String(source).match(/^([A-Za-zα-ωΔ]+)(?:_\{([^}]*)\})?$/);
    if(!a)return [{text:String(source),style:'roman'}];
    return [{text:greek[a[1]]||a[1],style:'variable'},...(a[2]?[{text:a[2],style:'subscript'}]:[])];
  }
  function draw(ctx,x,y,source,{size=11,align='left',color='#2d5364'}={}) {
    const t=tokens(source),fonts=t.map(k=>k.style==='variable'?`italic ${size}px "STIX Math",Georgia,serif`:k.style==='subscript'?`${size*.72}px "STIX Math",Georgia,serif`:`${size}px "Segoe UI",Arial,sans-serif`);
    ctx.save();ctx.fillStyle=color;let total=0;
    for(let j=0;j<t.length;j++){ctx.font=fonts[j];total+=ctx.measureText(t[j].text).width;}
    let cx=x-(align==='right'?total:align==='center'?total/2:0);
    for(let j=0;j<t.length;j++){
      const k=t[j];ctx.font=fonts[j];ctx.fillText(k.text,cx,y+(k.style==='subscript'?size*.26:0));cx+=ctx.measureText(k.text).width;
    }
    ctx.restore();return total;
  }
  function html(source){
    const esc=s=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    return '<span class="math-expression">'+tokens(source).map(k=>k.style==='variable'?`<i>${esc(k.text)}</i>`:k.style==='subscript'?`<sub>${esc(k.text)}</sub>`:`<span>${esc(k.text)}</span>`).join('')+'</span>';
  }
  return {draw,html,tokens};
})();
