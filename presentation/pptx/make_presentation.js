/** Build the offline PowerPoint lecture from the validated 54-slide HTML snapshots.
 * All comments and documentation strings are written in English.
 * The 61 HTML snapshots preserve the visual layout at 16:9.
 * Native hyperlink hotspots make state, chapter and angle navigation clickable.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const pptxgen = require('pptxgenjs');

const ROOT=__dirname;
const OUT=path.resolve(__dirname,'../../dist/LCC_HVDC_R_RL_Presentation.pptx');
const META=JSON.parse(fs.readFileSync(path.join(ROOT,'slide_metadata.json'),'utf8'));
const CLICK_MAP=JSON.parse(fs.readFileSync(path.join(ROOT,'angle_click_map.json'),'utf8'));
const PAGE_WIDTH=1600, PAGE_HEIGHT=900, WIDTH=13.333333333333334, HEIGHT=7.5;
const X=(p)=>p*WIDTH/PAGE_WIDTH;
const Y=(p)=>p*HEIGHT/PAGE_HEIGHT;
const P={deep:'071927',deep2:'0B2E46',cyan:'2BB8C4',teal:'0AA0AB',white:'FFFFFF',muted:'9ABACC',ink:'14283F',line:'39536A',red:'DC354B',blue:'19465D',sky:'E8F0F6'};
const pptx=new pptxgen();
pptx.defineLayout({name:'LCC_SCREEN',width:WIDTH,height:HEIGHT});
pptx.layout='LCC_SCREEN';
pptx.author='Electrical engineering educational resources';
pptx.company='HVDC Conduction Lab';
pptx.subject='6-pulse SCR rectifier, inverter and complete HVDC link conduction';
pptx.title='HVDC LCC — Current paths and commutation (PowerPoint lecture edition)';
pptx.lang='en-US';
pptx.theme={headFontFace:'Aptos Display',bodyFontFace:'Aptos',lang:'en-US'};
pptx.defineSlideMaster({title:'PLAIN',background:{color:P.deep},objects:[]});

const slides=[];
const IDX=62, HELP=63;
const chTitle={rectifier:3,inverter:23,hvdc:36};
const startState={rectifier:10,inverter:23,hvdc:36};
const counts={rectifier:12,inverter:12,hvdc:24};
const pathUrl='https://github.com/angelohafner/three-phase-scr-rectifier-visualizer/blob/main/';

function shapeButton(slide,rect,destination,tooltip=''){
 if(!rect||!destination)return;
 if(!Number.isFinite(rect.x)||!Number.isFinite(rect.y))return;
 const xy={x:X(rect.x),y:Y(rect.y),w:X(rect.w),h:Y(rect.h)};
 if(xy.w<0.005||xy.h<0.005)return;
 const hyperlink=typeof destination==='number'?{slide:destination,tooltip}:{url:destination,tooltip};
 slide.addShape(pptx.ShapeType.rect,{...xy,rectRadius:0,line:{color:'FFFFFF',transparency:100, width:0.1},fill:{color:'FFFFFF',transparency:100},hyperlink});
}
function stateSlide(side,id){return startState[side]+id;}
function stepState(side,id,dir){return stateSlide(side,((id-1+dir+counts[side])%counts[side])+1);}
function coords(d,id){return d.controls?.[id]??null;}
function addSliderLinks(slide,d){
 const side=d.side;
 const angles=CLICK_MAP[side];
 if(!angles)return;
 const region=coords(d,'angle-range');
 if(region){
   const xStart=region.x+7, width=region.w-14, N=angles.length;
   for(let j=0;j<N;j++)shapeButton(slide,{x:xStart+width*j/N,y:region.y-9,w:width/N,h:Math.max(21,region.h+18)},stateSlide(side,angles[j]),`Electrical angle approximately ${5*j+2.5}°, state ${angles[j]}`);
 }
 // Graph clicks also jump to a discrete conduction state, like the HTML chart click.
 const chart=coords(d,'plot-canvas');
 if(chart){
   const xStart=chart.x+38, width=chart.w-53, N=angles.length;
   for(let j=0;j<N;j++)shapeButton(slide,{x:xStart+width*j/N,y:chart.y+28,w:width/N,h:chart.h-44},stateSlide(side,angles[j]),`Go to ${side} conduction state ${angles[j]}`);
 }
}
function externalCircuit(side,id){
 const n=String(id).padStart(2,'0');
 return side==='hvdc'?`${pathUrl}output_hvdc/hvdc_joint_state_${n}.svg`:`${pathUrl}output_lcc/${side}/estado_${n}.svg`;
}
function externalWaveform(side,id){
 const n=String(id).padStart(2,'0');
 return side==='hvdc'?`${pathUrl}output_hvdc/waveforms/hvdc_joint_state_${n}.svg`:`${pathUrl}output_lcc/${side}/waveforms/estado_${n}.svg`;
}
function notes(d){
 const t=[];
 t.push(`Updated HTML lecture, slide ${d.index+1}/61.`);
 t.push(`Chapter: ${d.side}. Slide type: ${d.type}${d.state?' / state '+d.state:''}.`);
 t.push(`Title: ${d.title.replace(/\s+/g,' ').trim()}`);
 if(d.subtitle)t.push(`On-screen subtitle: ${d.subtitle}`);
 if(d.description)t.push(`Concept: ${d.description}`);
 if(d.facts)t.push(`Conduction facts: ${d.facts.replace(/\s+/g,' ').trim()}`);
 if(d.status)t.push(`Angular snapshot: ${d.status}`);
 t.push('Reference settings: alpha_rectifier=15°, mu_rectifier=12°, alpha_inverter=145°, mu_inverter=15°, gamma_inverter=20°, DC current=1 p.u., phase voltage peak=1 p.u.');
 t.push('All current-transfer curves are illustrative, analytically simplified and not EMT results.');
 t.push('PowerPoint: use chapter buttons, slide arrows, state arrows, overview or the angle track to navigate. Clicking an angle jumps to a nearby discrete state. Continuous animation and changing electrical parameters require the companion self-contained HTML file.');
 return t.join('\n');
}
function nativeHeader(slide,label,sub){
 slide.addShape(pptx.ShapeType.roundRect,{x:0.25,y:0.22,w:0.36,h:0.34,rectRadius:0.1,fill:{color:P.cyan},line:{color:P.cyan}});
 slide.addText('LCC',{x:0.255,y:0.31,w:0.35,h:0.14,fontSize:10,color:P.deep,bold:true,align:'center',margin:0});
 slide.addText('HVDC CONDUCTION LAB',{x:0.70,y:0.19,w:3.9,h:0.22,fontFace:'Aptos',fontSize:14,bold:true,color:P.white,margin:0});
 slide.addText(sub||'POWERPOINT LECTURE EDITION',{x:0.70,y:0.42,w:4.4,h:0.17,fontSize:8.5,color:P.muted,charSpacing:2,margin:0});
 slide.addText(label,{x:0.45,y:0.96,w:9,h:0.47,fontSize:28,bold:true,color:P.white,margin:0});
}
function nativeTile(slide,caption,x,y,w,h,destination,active=false,sub=''){
 slide.addShape(pptx.ShapeType.roundRect,{x,y,w,h,rectRadius:0.08,fill:{color:active?'16586C':'102D47'},line:{color:active?'45CBD2':'46657D',width:active?1.2:.75},hyperlink:{slide:destination}});
 slide.addText(caption,{x:x+0.03,y:y+0.095,w:w-0.06,h:0.205,fontSize:11.4,color:'FFFFFF',bold:true,align:'center',margin:0,hyperlink:{slide:destination}});
 if(sub)slide.addText(sub,{x:x+0.03,y:y+h-0.27,w:w-0.06,h:0.18,fontSize:8,color:active?'9DE9E9':'9ABACC',align:'center',margin:0});
}
function addNavPill(slide,caption,x,y,w,target){
 slide.addShape(pptx.ShapeType.roundRect,{x,y,w,h:.36,rectRadius:.07,fill:{color:'19455B'},line:{color:'3D7A8D',width:.75},hyperlink:{slide:target}});
 slide.addText(caption,{x,y:y+.07,w,h:.23,align:'center',fontSize:10.2,bold:true,color:'FFFFFF',margin:0,hyperlink:{slide:target}});
}

for(const d of META){
 const slide=pptx.addSlide('PLAIN');
 slide.background={color:P.deep};
 slide.addImage({path:d.image,x:0,y:0,w:WIDTH,h:HEIGHT});
 slide.addNotes(notes(d));
 // Native chapter tabs and footer navigation replicate the HTML deck interface.
 for(const [id,side] of [['nav-rect','rectifier'],['nav-inv','inverter'],['nav-hvdc','hvdc']]) shapeButton(slide,coords(d,id),chTitle[side],`Jump to ${side} chapter`);
 shapeButton(slide,coords(d,'overview-open'),IDX,'Open the clickable state overview');
 shapeButton(slide,coords(d,'settings-open'),HELP,'PowerPoint and HTML lecture modes');
 shapeButton(slide,coords(d,'help-open'),HELP,'PowerPoint lecture help');
 // The Full Screen button remains decorative: Slide Show is already full-screen.
 if(d.index>0)shapeButton(slide,coords(d,'footer-prev'),d.index,`Previous slide (${d.index}/61)`);
 if(d.index<60)shapeButton(slide,coords(d,'footer-next'),d.index+2,`Next slide (${d.index+2}/61)`);
 if(d.type==='load'){
   shapeButton(slide,coords(d,'load-settings'),HELP,'Open the companion HTML to change electrical parameters');
   shapeButton(slide,coords(d,'load-choice'),9,'R and RL comparison');
   shapeButton(slide,coords(d,'load-chart-mode'),HELP,'Change plotted signals in the companion HTML');
   shapeButton(slide,coords(d,'play-btn'),HELP,'Live current animation requires the HTML');
   shapeButton(slide,coords(d,'angle-range'),d.index+1,'Load-model angular cursor is interactive in HTML');
 }
 if(d.type==='state'){
   const {side,state}=d;
   shapeButton(slide,coords(d,'step-prev'),stepState(side,state,-1),`Previous ${side} state`);
   shapeButton(slide,coords(d,'step-next'),stepState(side,state,+1),`Next ${side} state`);
   shapeButton(slide,coords(d,'play-btn'),HELP,'Live animation is available in the companion HTML');
   shapeButton(slide,coords(d,'chart-mode'),HELP,'Change waveforms in the HTML app');
   shapeButton(slide,coords(d,'zoom-btn'),externalCircuit(side,state),'Open editable circuit SVG on GitHub (internet required)');
   shapeButton(slide,coords(d,'ref-btn'),externalWaveform(side,state),'Open reference waveform SVG on GitHub (internet required)');
   addSliderLinks(slide,d);
 }
 slides.push(slide);
}
// Extra clickable PowerPoint overview (does not alter the original 61-slide narrative).
{
 const slide=pptx.addSlide('PLAIN');
 nativeHeader(slide,'STATE OVERVIEW','CLICK A STATE TO NAVIGATE DIRECTLY');
 const groups=[
   {side:'rectifier',title:'01  RECTIFIER',desc:'AC  →  DC',x:.38,w:4.0,cols:4,rows:3,cardw:.82},
   {side:'inverter',title:'02  INVERTER',desc:'DC  →  AC',x:4.57,w:4.0,cols:4,rows:3,cardw:.82},
   {side:'hvdc',title:'03  HVDC LINK',desc:'TWO STATIONS',x:8.77,w:4.18,cols:6,rows:4,cardw:.58}
 ];
 // Additional introductory R/RL slide shortcuts.
 [['R · 0°',5],['R · 30°',6],['R · 75°',7],['R · 90°',8],['R / RL',9],['RL',10]].forEach(([txt,dst],j)=>{
  slide.addText(txt,{x:.65+j*1.55,y:1.36,w:1.42,h:.17,fontSize:9,color:P.muted,hyperlink:{slide:dst},margin:0});
 });
 for(const g of groups){
   slide.addShape(pptx.ShapeType.roundRect,{x:g.x,y:1.55,w:g.w,h:4.74,rectRadius:.13,fill:{color:'0C2940'},line:{color:'24556A',width:1.0}});
   slide.addText(g.title,{x:g.x+.18,y:1.79,w:g.w-.36,h:.29,fontSize:18.0,color:P.white,bold:true,margin:0});
   slide.addText(g.desc,{x:g.x+.18,y:2.11,w:g.w-.36,h:.22,fontSize:10.0,color:P.muted,charSpacing:1.8,margin:0});
   const n=counts[g.side], gapX=g.side==='hvdc'?.10:.13, gapY=.17;
   const usable=g.w-.36, tileW=(usable-gapX*(g.cols-1))/g.cols;
   const tileH=g.side==='hvdc'?.68:.83;
   for(let k=0;k<n;k++){
     const row=Math.floor(k/g.cols),col=k%g.cols;
     const x=g.x+.18+col*(tileW+gapX), y=2.58+row*(tileH+gapY);
     const overlap=g.side==='hvdc'?((CLICK_MAP.schedule[k].r%2===0)||(CLICK_MAP.schedule[k].i%2===0)):(k%2===1);
     const dest=stateSlide(g.side,k+1);
     slide.addShape(pptx.ShapeType.roundRect,{x,y,w:tileW,h:tileH,rectRadius:.08,fill:{color:overlap?'502838':'123D54'},line:{color:overlap?'BB6878':'287C91',width:.65},hyperlink:{slide:dest}});
     slide.addText(String(k+1).padStart(2,'0'),{x,y:y+(g.side==='hvdc'?.19:.19),w:tileW,h:.22,align:'center',fontSize:g.side==='hvdc'?12:15,bold:true,color:'FFFFFF',margin:0,hyperlink:{slide:dest}});
     if(g.side!=='hvdc')slide.addText(overlap?'OVERLAP':'NORMAL',{x,y:y+.51,w:tileW,h:.19,fontSize:7.0,color:overlap?'F7B2BD':'A2E6EB',align:'center',margin:0});
   }
 }
 slide.addText('Click any state or use the chapter buttons. Red cards indicate a commutation overlap.',{x:.42,y:6.46,w:9.7,h:.24,fontSize:10.0,color:P.muted,margin:0});
 addNavPill(slide,'TITLE',.45,6.94,1.35,1);
 addNavPill(slide,'RECTIFIER',2.05,6.94,1.55,3);
 addNavPill(slide,'INVERTER',3.85,6.94,1.45,23);
 addNavPill(slide,'HVDC LINK',5.55,6.94,1.55,36);
 addNavPill(slide,'HOW TO USE',10.85,6.94,1.90,HELP);
 slide.addNotes('Clickable PowerPoint state overview. Choose any of the 48 electrical conduction diagrams. The underlying current-transfer waveforms are conceptual, not EMT simulation.');
 slides.push(slide);
}
// PowerPoint-specific help slide, including explicit distinction from continuous HTML simulation.
{
 const slide=pptx.addSlide('PLAIN');
 nativeHeader(slide,'HOW TO USE THIS EDITION','CLICK NAVIGATION · VIEW STATIC REFERENCE STATES');
 const sections=[
   ['01','Navigate','Use the arrow keys, the footer buttons, or the clickable chapter tabs.'],
   ['02','Choose an electrical state','Click the angle track or a waveform to jump to a discrete state. Use STATE arrows for step-by-step conduction.'],
   ['03','Open source SVGs','The ENLARGE and SOURCE SVG links open their editable GitHub assets when you have internet access.'],
   ['04','Use the companion HTML for real-time controls','Continuous animation, live firing-angle sliders, changing the DC current and selecting plotted signals require the offline HTML application included in the ZIP.']
 ];
 sections.forEach(([n,title,body],i)=>{
   const y=1.64+i*1.11;
   slide.addShape(pptx.ShapeType.roundRect,{x:.46,y,w:12.35,h:.96,rectRadius:.09,fill:{color:'0B2A40'},line:{color:'285269',width:.75}});
   slide.addShape(pptx.ShapeType.roundRect,{x:.66,y:y+.20,w:.55,h:.52,rectRadius:.08,fill:{color:P.teal},line:{color:P.teal}});
   slide.addText(n,{x:.69,y:y+.34,w:.50,h:.21,align:'center',fontSize:13,bold:true,color:'FFFFFF',margin:0});
   slide.addText(title,{x:1.44,y:y+.12,w:10.70,h:.27,fontSize:17.0,color:'FFFFFF',bold:true,margin:0});
   slide.addText(body,{x:1.44,y:y+.47,w:10.83,h:.32,fontSize:12.0,color:'B7D4E3',margin:0,breakLine:false});
 });
 slide.addText('The PPTX and companion HTML both work offline. The PowerPoint version offers native clickable slide navigation, while the HTML edition also performs live calculations in JavaScript.',{x:.55,y:6.37,w:12.2,h:.46,fontSize:10.2,color:P.muted,margin:0});
 addNavPill(slide,'TITLE',.45,6.94,1.35,1);
 addNavPill(slide,'STATE OVERVIEW',2.05,6.94,2.10,IDX);
 addNavPill(slide,'RECTIFIER',4.40,6.94,1.55,3);
 addNavPill(slide,'INVERTER',6.20,6.94,1.45,23);
 addNavPill(slide,'HVDC LINK',7.90,6.94,1.55,36);
 slide.addNotes('The companion HTML is fully self-contained and offers continuous electrical-angle scrubbing, phase-current animation, editing electrical parameters and different signal modes. PowerPoint slides are illustrated snapshots; click navigation and angular jumps are discrete.');
 slides.push(slide);
}

pptx.writeFile({fileName:OUT,compression:true}).then(()=>{
 console.log(JSON.stringify({file:OUT,slideCount:slides.length,imageCount:META.length,pptxBytes:fs.statSync(OUT).size},null,2));
}).catch(e=>{console.error(e);process.exit(1)});
