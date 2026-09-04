from __future__ import annotations

"""Visual-only 2.5D plant layer for DOBO Design Lab.

This module does not modify CAD/manufacturing geometry. It normalizes the
viewer to Y-up, adds selectable visual plants and a substrate surface, and
keeps all of that out of STL/3MF generation.

Run:
    python tools/dobo_design_lab_plants.py
"""

import dobo_design_lab as base

PLANT_CSS = r'''
.plantBlock{margin-top:22px;padding-top:18px;border-top:1px solid var(--line)}
.plantGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:7px}.plantChoice{border:1px solid var(--line);background:#faf8f3;border-radius:10px;padding:9px;cursor:pointer;text-align:left;font-size:11px}.plantChoice.active{background:#222;color:#fff;border-color:#222}.plantChoice b{display:block;font-size:12px}.plantChoice span{opacity:.72}
.plantSizes{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:7px}.plantSize{border:1px solid var(--line);background:#faf8f3;border-radius:9px;padding:8px 4px;cursor:pointer;text-align:center;font-size:10px}.plantSize.active{background:#222;color:#fff;border-color:#222}
.substrateRow{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:7px}.substrateChoice{border:1px solid var(--line);background:#faf8f3;border-radius:9px;padding:8px 4px;cursor:pointer;text-align:center;font-size:10px}.substrateChoice.active{background:#222;color:#fff;border-color:#222}
.visualOnlyTag{display:inline-block;margin-top:8px;padding:4px 7px;border-radius:999px;background:#eee9df;color:#666;font-size:9px;font-weight:700;letter-spacing:.05em;text-transform:uppercase}
'''

PLANT_CONTROLS = r'''
<div class="plantBlock">
<h3>8 · Planta · vista previa 2.5D</h3>
<div class="hint">Capa visual independiente. No se incorpora al STL ni al 3MF.</div>
<div class="plantGrid" id="plantChoices">
<button class="plantChoice active" data-plant="ficus"><b>Ficus lyrata</b><span>hoja ancha</span></button>
<button class="plantChoice" data-plant="monstera"><b>Monstera</b><span>hoja abierta</span></button>
<button class="plantChoice" data-plant="sansevieria"><b>Sansevieria</b><span>vertical</span></button>
<button class="plantChoice" data-plant="pothos"><b>Pothos</b><span>colgante</span></button>
</div>
<div class="plantSizes" id="plantSizes"><button class="plantSize" data-size="small">Pequeña</button><button class="plantSize active" data-size="medium">Mediana</button><button class="plantSize" data-size="large">Grande</button></div>
<h3>9 · Superficie</h3>
<div class="substrateRow" id="substrates"><button class="substrateChoice active" data-substrate="soil">Tierra</button><button class="substrateChoice" data-substrate="white_stone">Piedra blanca</button><button class="substrateChoice" data-substrate="volcanic">Volcánica</button></div>
<span class="visualOnlyTag">visual_only · no exportable</span>
</div>
'''

PLANT_JS = r'''
// DOBO visual presentation layer. CAD arrives Z-up; the Lab scene is Y-up.
const plantState={plant:'ficus',size:'medium',substrate:'soil'};
let visualPlantGroup=null,substrateGroup=null,saucerModel=null;
let saucerSupportTop=0;
const PLANT_SCALE={small:.72,medium:1.0,large:1.34};
const C={leaf:0x356b3f,leaf2:0x4b8050,leaf3:0x254c32,stem:0x76563a};

const COMMONS_FILE=name=>'https://commons.wikimedia.org/wiki/Special:Redirect/file/'+encodeURIComponent(name)+'?width=1400';
const PHOTO_ASSETS={
 ficus:{
  file:'Ficus lyrata indoor house second floor Transparent - July 2026.png',
  source:'Wikimedia Commons',mode:'transparent',height:1.62,layers:3
 },
 monstera:{
  file:'Feuille Plante.png',
  source:'Wikimedia Commons',mode:'leaf_cluster',height:1.22,layers:7
 },
 sansevieria:{
  file:'Dracaena trifasciata.jpg',
  source:'Wikimedia Commons',mode:'green_key',height:1.18,layers:3
 },
 pothos:{
  file:"Epipremnum Aureum (Devil's Ivy) cutting.png",
  source:'Wikimedia Commons',mode:'transparent',height:1.02,layers:3
 }
};
const photoTextureCache=new Map();
let plantLoadToken=0;

function disposeMaterial(m){if(!m)return;['map','bumpMap','roughnessMap','alphaMap','normalMap'].forEach(k=>{const t=m[k];if(t&&!t.userData?.sharedPhoto)t.dispose?.()});m.dispose?.()}
function disposeVisual(o){if(!o)return;o.traverse?.(n=>{n.geometry?.dispose?.();if(n.material){(Array.isArray(n.material)?n.material:[n.material]).forEach(disposeMaterial)}});scene.remove(o)}

function seededRandom(seed){let s=seed>>>0;return()=>{s=(1664525*s+1013904223)>>>0;return s/4294967296}}
function textureCanvas(kind,size=1024){
 const canvas=document.createElement('canvas');canvas.width=canvas.height=size;const ctx=canvas.getContext('2d');
 const bump=document.createElement('canvas');bump.width=bump.height=size;const bctx=bump.getContext('2d');
 const seed=kind==='soil'?9137:kind==='white_stone'?22471:44893,rand=seededRandom(seed);
 const bg=kind==='soil'?'#3b2619':kind==='white_stone'?'#c9c6bd':'#2b2928';ctx.fillStyle=bg;ctx.fillRect(0,0,size,size);bctx.fillStyle='#777';bctx.fillRect(0,0,size,size);
 if(kind==='soil'){
  for(let i=0;i<9000;i++){const x=rand()*size,y=rand()*size,r=.35+rand()*2.6,v=28+Math.floor(rand()*55);ctx.fillStyle='rgb('+(52+v*.35)+','+(34+v*.20)+','+(20+v*.12)+')';ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();const g=85+Math.floor(rand()*95);bctx.fillStyle='rgb('+g+','+g+','+g+')';bctx.beginPath();bctx.arc(x,y,r,0,Math.PI*2);bctx.fill()}
  ctx.globalAlpha=.35;ctx.strokeStyle='#b18b5d';ctx.lineWidth=.7;for(let i=0;i<260;i++){const x=rand()*size,y=rand()*size,l=3+rand()*15,a=rand()*Math.PI*2;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+Math.cos(a)*l,y+Math.sin(a)*l);ctx.stroke()}ctx.globalAlpha=1;
 }else{
  const pale=kind==='white_stone';ctx.fillStyle=pale?'#595650':'#151414';ctx.fillRect(0,0,size,size);
  for(let i=0;i<560;i++){const x=rand()*size,y=rand()*size,rx=5+rand()*18,ry=4+rand()*13,rot=rand()*Math.PI;ctx.save();ctx.translate(x,y);ctx.rotate(rot);const grad=ctx.createRadialGradient(-rx*.25,-ry*.35,1,0,0,Math.max(rx,ry));if(pale){grad.addColorStop(0,'#fbfaf6');grad.addColorStop(.55,'#ddd9cf');grad.addColorStop(1,'#a7a399')}else{grad.addColorStop(0,'#5c5652');grad.addColorStop(.55,'#312e2c');grad.addColorStop(1,'#141313')}ctx.fillStyle=grad;ctx.beginPath();ctx.ellipse(0,0,rx,ry,0,0,Math.PI*2);ctx.fill();ctx.restore();const gv=pale?180+Math.floor(rand()*70):55+Math.floor(rand()*80);bctx.fillStyle='rgb('+gv+','+gv+','+gv+')';bctx.save();bctx.translate(x,y);bctx.rotate(rot);bctx.beginPath();bctx.ellipse(0,0,rx,ry,0,0,Math.PI*2);bctx.fill();bctx.restore()}
 }
 const map=new THREE.CanvasTexture(canvas),bumpMap=new THREE.CanvasTexture(bump);map.colorSpace=THREE.SRGBColorSpace;map.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());bumpMap.anisotropy=map.anisotropy;map.needsUpdate=bumpMap.needsUpdate=true;return{map,bumpMap}
}

function loadRemoteImage(url){
 return new Promise((ok,bad)=>{
  const img=new Image();img.crossOrigin='anonymous';img.decoding='async';
  img.onload=()=>ok(img);img.onerror=bad;img.src=url;
 });
}

function textureFromImage(img){
 const t=new THREE.Texture(img);t.needsUpdate=true;t.colorSpace=THREE.SRGBColorSpace;
 t.anisotropy=Math.min(12,renderer.capabilities.getMaxAnisotropy());
 t.generateMipmaps=true;t.minFilter=THREE.LinearMipmapLinearFilter;t.magFilter=THREE.LinearFilter;
 return t;
}

function greenKeyPhoto(img){
 const maxSide=1400,scale=Math.min(1,maxSide/Math.max(img.width,img.height));
 const w=Math.max(2,Math.round(img.width*scale)),h=Math.max(2,Math.round(img.height*scale));
 const canvas=document.createElement('canvas');canvas.width=w;canvas.height=h;
 const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(img,0,0,w,h);
 const data=ctx.getImageData(0,0,w,h),p=data.data;
 for(let i=0;i<p.length;i+=4){
  const r=p[i]/255,g=p[i+1]/255,b=p[i+2]/255,max=Math.max(r,g,b),min=Math.min(r,g,b),sat=max>0?(max-min)/max:0;
  const greenness=g-.55*r-.45*b;
  const leaf=Math.max(0,Math.min(1,(greenness+.02)*4.4))*Math.max(0,Math.min(1,(sat-.06)*4.5));
  const darkLeaf=(g>r*.88&&g>b*.82&&g>.12)?Math.min(1,(g+.10)*1.15):0;
  const alpha=Math.max(leaf,darkLeaf);
  p[i+3]=Math.round(255*Math.pow(alpha,.70));
 }
 ctx.putImageData(data,0,0);
 const t=new THREE.CanvasTexture(canvas);t.needsUpdate=true;t.colorSpace=THREE.SRGBColorSpace;
 t.anisotropy=Math.min(12,renderer.capabilities.getMaxAnisotropy());
 return t;
}

async function photoTexture(asset){
 const key=asset.file+'|'+asset.mode;
 if(photoTextureCache.has(key))return photoTextureCache.get(key);
 const promise=loadRemoteImage(COMMONS_FILE(asset.file)).then(img=>{
  const texture=asset.mode==='green_key'?greenKeyPhoto(img):textureFromImage(img);
  texture.userData={source:asset.source,file:asset.file,sharedPhoto:true};
  return texture;
 });
 photoTextureCache.set(key,promise);
 return promise;
}

function barkTexture(){
 const size=512,canvas=document.createElement('canvas');canvas.width=canvas.height=size;
 const ctx=canvas.getContext('2d'),rand=seededRandom(44219);
 const grad=ctx.createLinearGradient(0,0,size,0);grad.addColorStop(0,'#3e2b1d');grad.addColorStop(.48,'#75513a');grad.addColorStop(1,'#342419');
 ctx.fillStyle=grad;ctx.fillRect(0,0,size,size);
 for(let x=0;x<size;x+=5+Math.floor(rand()*9)){
  ctx.strokeStyle='rgba('+(55+Math.floor(rand()*55))+','+(34+Math.floor(rand()*35))+','+(22+Math.floor(rand()*25))+','+(.22+rand()*.32)+')';
  ctx.lineWidth=.6+rand()*2;ctx.beginPath();ctx.moveTo(x+rand()*8,0);
  for(let y=0;y<=size;y+=24)ctx.lineTo(x+Math.sin(y*.035+rand())*5+rand()*4,y);
  ctx.stroke();
 }
 for(let i=0;i<650;i++){const x=rand()*size,y=rand()*size,r=.4+rand()*1.7;ctx.fillStyle='rgba(20,12,7,'+(.08+rand()*.18)+')';ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill()}
 const t=new THREE.CanvasTexture(canvas);t.colorSpace=THREE.SRGBColorSpace;t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(2.5,1.0);t.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());return t
}

function texturedStem(h,r){
 const map=barkTexture(),m=new THREE.Mesh(new THREE.CylinderGeometry(r,r*1.12,h,14),new THREE.MeshStandardMaterial({map,roughness:.92,metalness:0}));
 m.userData.visual_only=true;m.castShadow=true;return m
}

function photoCard(texture,height,opts={}){
 const img=texture.image||{},aspect=(img.width&&img.height)?img.width/img.height:(opts.aspect||.78);
 const width=height*aspect*(opts.widthScale||1);
 const mat=new THREE.MeshStandardMaterial({
  map:texture,color:0xffffff,transparent:true,alphaTest:opts.alphaTest??.035,
  roughness:opts.roughness??.72,metalness:0,side:THREE.DoubleSide,depthWrite:true,opacity:opts.opacity??1
 });
 const mesh=new THREE.Mesh(new THREE.PlaneGeometry(width,height),mat);
 mesh.position.set(opts.x||0,opts.y??height*.5,opts.z||0);
 mesh.rotation.z=opts.roll||0;
 mesh.castShadow=true;mesh.receiveShadow=false;
 mesh.userData.visual_only=true;
 mesh.userData.billboard2_5d={baseYaw:opts.baseYaw||0,follow:opts.follow??1};
 return mesh
}

function shortestAngle(a){return Math.atan2(Math.sin(a),Math.cos(a))}
function updatePlantBillboards(){
 if(!visualPlantGroup)return;
 const wp=new THREE.Vector3();
 visualPlantGroup.traverse(node=>{
  const bb=node.userData?.billboard2_5d;if(!bb)return;
  node.getWorldPosition(wp);
  const target=Math.atan2(camera.position.x-wp.x,camera.position.z-wp.z);
  const desired=bb.baseYaw+shortestAngle(target-bb.baseYaw)*(bb.follow??1);
  node.rotation.y+=shortestAngle(desired-node.rotation.y)*.16;
 });
}
function billboardLoop(){requestAnimationFrame(billboardLoop);updatePlantBillboards()}
billboardLoop();

function normalizePotForViewer(supportTop=0){
 if(!model)return;
 model.rotation.set(-Math.PI/2,0,0);
 model.position.set(0,Math.max(0,Number(supportTop)||0),0);
 model.updateMatrixWorld(true);
 floor.position.set(0,saucerModel?-.35:-2,0);
 floor.updateMatrixWorld(true);
 key.position.set(-180,260,220);key.castShadow=true;floor.receiveShadow=true;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
}

function loadSaucerForViewer(d){
 disposeVisual(saucerModel);saucerModel=null;saucerSupportTop=0;
 const info=d?.preview?.saucer;
 if(!info?.url)return Promise.resolve(false);
 return new Promise((ok,bad)=>new STLLoader().load(info.url,g=>{
  g.computeVertexNormals();
  const material=new THREE.MeshStandardMaterial({color:new THREE.Color(d.selection.body_color),roughness:.68,metalness:.01,side:THREE.DoubleSide});
  saucerModel=new THREE.Mesh(g,material);
  saucerModel.rotation.set(-Math.PI/2,0,0);
  saucerModel.position.set(0,0,0);
  saucerModel.castShadow=true;saucerModel.receiveShadow=true;
  saucerModel.name='DOBO_CAD_SAUCER';
  saucerModel.userData={visual_only:false,exportable:true,role:'saucer',source:'CAD_STL'};
  saucerSupportTop=Math.max(0,Number(info.support_top_mm)||0);
  scene.add(saucerModel);saucerModel.updateMatrixWorld(true);ok(true);
 },undefined,bad));
}

function buildPhotoLayers(group,texture,u,id){
 const asset=PHOTO_ASSETS[id],H=u*asset.height;
 if(asset.mode==='leaf_cluster'){
  const trunk=texturedStem(H*.62,u*.018);trunk.position.y=H*.31;group.add(trunk);
  const leaves=[
   [-.30,.43,-.08,.62,-.52, .62], [.29,.48,.07,.68,.48,.72], [-.24,.61,.03,.66,-.31,.82],
   [.25,.70,-.03,.72,.30,.90], [-.08,.82,.07,.69,-.12,.96], [.12,.93,-.06,.64,.20,.86], [0,1.02,.01,.72,0,1.0]
  ];
  leaves.forEach(([x,y,z,scale,roll,follow],i)=>{
   const card=photoCard(texture,H*.42*scale,{x:x*u,y:y*H,z:z*u,roll,baseYaw:(i-3)*.055,follow,alphaTest:.045,roughness:.68});
   group.add(card);
  });
  return;
 }
 if(id==='pothos'){
  const trunk=texturedStem(H*.46,u*.012);trunk.position.y=H*.23;trunk.rotation.z=-.08;group.add(trunk);
 }
 const layers=[
  {scale:1.00,x:0,z:0,baseYaw:0,follow:1.00,opacity:1},
  {scale:.92,x:-.055*u,z:.060*u,baseYaw:-.24,follow:.72,opacity:.88},
  {scale:.88,x:.060*u,z:-.055*u,baseYaw:.25,follow:.58,opacity:.82},
 ];
 layers.slice(0,asset.layers||3).forEach((L,i)=>{
  const card=photoCard(texture,H*L.scale,{x:L.x,y:H*L.scale*.5,z:L.z,baseYaw:L.baseYaw,follow:L.follow,opacity:L.opacity,alphaTest:asset.mode==='green_key' ? 0.08 : 0.035,roughness:.70});
  card.renderOrder=10+i;group.add(card);
 });
}

function makePhotoPlant(id,u){
 const g=new THREE.Group(),token=++plantLoadToken;g.userData.photo_loading=true;
 const asset=PHOTO_ASSETS[id];
 photoTexture(asset).then(texture=>{
  if(!g.parent||token!==plantLoadToken)return;
  buildPhotoLayers(g,texture,u,id);
  g.userData.photo_loading=false;g.userData.photo_source=asset.source;g.userData.photo_file=asset.file;
  updatePlantBillboards();
 }).catch(error=>{
  console.warn('DOBO 2.5D photo texture fallback',id,error);
  g.userData.photo_error=String(error);
  const fallback=texturedStem(u*.9,u*.018);fallback.position.y=u*.45;g.add(fallback);
 });
 return g;
}

function substrateColor(){return 0xffffff}
function substrateSurfaceY(size,rimY){return rimY-Math.max(6.0,Math.min(size.y*.055,9.0))}
function makeSubstrate(center,size,rimY){
 const g=new THREE.Group();
 // Derive the visible mouth from the selected profile instead of the generic 0.58 body contract.
 // This fixes the undersized floating brown circle seen on low/wide profiles.
 const shapeItem=byId(state.shape);
 const profile=shapeItem?.profile||[];
 const topRadiusRatio=profile.length?Number(profile[profile.length-1][1])||.80:.80;
 const openingDiameter=Math.min(size.x,size.z)*topRadiusRatio;
 const wallInset=Math.max(2.0,openingDiameter*.025);
 const radius=Math.max(2,openingDiameter*.5-wallInset);
 const y=substrateSurfaceY(size,rimY);
 const tex=textureCanvas(plantState.substrate,2048);
 const mat=new THREE.MeshStandardMaterial({color:substrateColor(),map:tex.map,bumpMap:tex.bumpMap,bumpScale:plantState.substrate==='soil'?1.15:1.8,roughness:plantState.substrate==='white_stone' ? 0.82 : 0.98,metalness:0,side:THREE.DoubleSide});
 const disc=new THREE.Mesh(new THREE.CircleGeometry(radius,96),mat);disc.rotation.x=-Math.PI/2;disc.position.set(center.x,y,center.z);disc.receiveShadow=true;disc.userData={visual_only:true,exportable:false,role:'substrate',surface_y:y};g.add(disc);
 g.name='DOBO_VISUAL_ONLY_SUBSTRATE';g.userData={visual_only:true,exportable:false,substrate:plantState.substrate};return g
}

function updatePlantVisual(){
 if(!model)return;
 const box=new THREE.Box3().setFromObject(model),size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3()),rimY=box.max.y;
 const unit=Math.max(size.x,size.z)*.58*PLANT_SCALE[plantState.size];
 disposeVisual(visualPlantGroup);disposeVisual(substrateGroup);visualPlantGroup=null;substrateGroup=null;
 substrateGroup=makeSubstrate(center,size,rimY);scene.add(substrateGroup);
 visualPlantGroup=makePhotoPlant(plantState.plant,unit);visualPlantGroup.position.set(center.x,substrateSurfaceY(size,rimY),center.z);visualPlantGroup.name='DOBO_VISUAL_ONLY_PLANT_2_5D_PHOTO';visualPlantGroup.userData={visual_only:true,exportable:false,render_mode:'2.5D_billboard_photo',plant:plantState.plant,size:plantState.size};scene.add(visualPlantGroup);
 // Fit from the complete sellable composition: pot + plant + actual CAD saucer.
 const viewBox=new THREE.Box3().setFromObject(model).union(new THREE.Box3().setFromObject(visualPlantGroup));
 if(saucerModel)viewBox.union(new THREE.Box3().setFromObject(saucerModel));
 const vs=viewBox.getSize(new THREE.Vector3()),vc=viewBox.getCenter(new THREE.Vector3()),m=Math.max(vs.x,vs.y,vs.z);controls.target.copy(vc);camera.position.set(vc.x+1.45*m,vc.y+.72*m,vc.z+1.65*m);controls.update();
}

function bindPlantUI(){document.querySelectorAll('#plantChoices [data-plant]').forEach(el=>el.onclick=()=>{document.querySelectorAll('#plantChoices [data-plant]').forEach(x=>x.classList.remove('active'));el.classList.add('active');plantState.plant=el.dataset.plant;updatePlantVisual()});document.querySelectorAll('#plantSizes [data-size]').forEach(el=>el.onclick=()=>{document.querySelectorAll('#plantSizes [data-size]').forEach(x=>x.classList.remove('active'));el.classList.add('active');plantState.size=el.dataset.size;updatePlantVisual()});document.querySelectorAll('#substrates [data-substrate]').forEach(el=>el.onclick=()=>{document.querySelectorAll('#substrates [data-substrate]').forEach(x=>x.classList.remove('active'));el.classList.add('active');plantState.substrate=el.dataset.substrate;updatePlantVisual()})}
bindPlantUI();

const doboOriginalLoadPreview=loadPreview;
loadPreview=async function(d){
 await doboOriginalLoadPreview(d);
 try{
  await loadSaucerForViewer(d);
 }catch(e){console.warn('saucer preview fallback',e);disposeVisual(saucerModel);saucerModel=null;saucerSupportTop=0}
 normalizePotForViewer(saucerSupportTop);
 updatePlantVisual();
 if(saucerModel)$('#previewMode').textContent+=' · plato CAD';
};
'''

def _inject(html: str) -> str:
    html = html.replace("</style></head>", PLANT_CSS + "\n</style></head>")
    html = html.replace('<button class="generate" id="generate">Generar diseño real</button>','<button class="generate" id="generate">Generar diseño real</button>\n' + PLANT_CONTROLS)
    html = html.replace("</script></body></html>", PLANT_JS + "\n</script></body></html>")
    return html

base.HTML = _inject(base.HTML)
base.DESIGN_LAB_VERSION = base.DESIGN_LAB_VERSION + "+visual-plants-photo-billboard-v6"

if __name__ == "__main__":
    base.main()
