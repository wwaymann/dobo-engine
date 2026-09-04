from __future__ import annotations

"""Visual-only 2.5D plant layer for DOBO Design Lab.

This module intentionally does not modify the CAD/manufacturing pipeline. It
imports the current Design Lab, injects a selectable plant/substrate preview
layer into the Three.js scene, and then starts the existing server.

Run:
    python tools/dobo_design_lab_plants.py

Manufacturing invariant:
    plant + substrate are presentation/order metadata only. They are never
    added to STL/3MF generation and never enter the motor payload.
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
<div class="plantSizes" id="plantSizes">
  <button class="plantSize" data-size="small">Pequeña</button>
  <button class="plantSize active" data-size="medium">Mediana</button>
  <button class="plantSize" data-size="large">Grande</button>
</div>
<h3>9 · Superficie</h3>
<div class="substrateRow" id="substrates">
  <button class="substrateChoice active" data-substrate="soil">Tierra</button>
  <button class="substrateChoice" data-substrate="white_stone">Piedra blanca</button>
  <button class="substrateChoice" data-substrate="volcanic">Volcánica</button>
</div>
<span class="visualOnlyTag">visual_only · no exportable</span>
</div>
'''


PLANT_JS = r'''

// -------------------------------------------------------------------------
// DOBO visual-only plant layer. None of this state is sent to /api/design.
// -------------------------------------------------------------------------
const plantState={plant:'ficus',size:'medium',substrate:'soil'};
let visualPlantGroup=null;
let substrateGroup=null;
let lastPotBox=null;

const PLANT_SCALE={small:.72,medium:1.0,large:1.34};
const PLANT_COLORS={leaf:0x356b3f,leaf2:0x4b8050,leaf3:0x254c32,stem:0x76563a};

function disposeVisualObject(object){
 if(!object)return;
 object.traverse?.(n=>{
  n.geometry?.dispose?.();
  if(n.material){
   const materials=Array.isArray(n.material)?n.material:[n.material];
   materials.forEach(m=>m.dispose?.());
  }
 });
 scene.remove(object);
}

function leafShape(width,height,notch=0){
 const shape=new THREE.Shape();
 shape.moveTo(0,-height*.5);
 shape.bezierCurveTo(width*.62,-height*.34,width*.62,height*.22,0,height*.5);
 if(notch>0){
  shape.bezierCurveTo(-width*.10,height*.36,-width*.13,height*.18,-width*.18,height*.08);
  shape.bezierCurveTo(-width*.43,height*.26,-width*.62,-height*.08,0,-height*.5);
 }else{
  shape.bezierCurveTo(-width*.62,height*.22,-width*.62,-height*.34,0,-height*.5);
 }
 return shape;
}

function leafPlane(width,height,color=PLANT_COLORS.leaf,notch=0){
 const mesh=new THREE.Mesh(
  new THREE.ShapeGeometry(leafShape(width,height,notch),24),
  new THREE.MeshStandardMaterial({color,roughness:.86,metalness:0,side:THREE.DoubleSide})
 );
 mesh.userData.visual_only=true;
 return mesh;
}

function stem(length,radius=.7){
 const mesh=new THREE.Mesh(
  new THREE.CylinderGeometry(radius,radius*1.15,length,10),
  new THREE.MeshStandardMaterial({color:PLANT_COLORS.stem,roughness:.95})
 );
 mesh.rotation.x=Math.PI/2;
 mesh.userData.visual_only=true;
 return mesh;
}

// 2.5D plants use flat leaf silhouettes distributed in depth. This keeps them
// light, readable from the OrbitControls camera and replaceable by PNG cards later.
function makeFicus(unit){
 const g=new THREE.Group();
 const trunk=stem(unit*1.05,unit*.018);trunk.position.z=unit*.52;g.add(trunk);
 const leaves=[
  [-.22,-.025,.62,-.40,.34,.46],[.21,.025,.72,.36,.37,.50],[-.18,.04,.86,-.50,.33,.44],
  [.18,-.04,.98,.43,.35,.48],[-.08,.03,1.10,-.16,.37,.50],[.09,-.02,1.22,.24,.35,.47]
 ];
 leaves.forEach(([x,y,z,rot,w,h],i)=>{const l=leafPlane(unit*w,unit*h,i%3===0?PLANT_COLORS.leaf3:(i%2?PLANT_COLORS.leaf2:PLANT_COLORS.leaf));l.position.set(unit*x,unit*y,z*unit);l.rotation.z=rot;l.rotation.x=Math.PI/2;l.rotation.y=(i%2?1:-1)*.10;g.add(l)});
 return g;
}

function makeMonstera(unit){
 const g=new THREE.Group();
 const trunk=stem(unit*.82,unit*.016);trunk.position.z=unit*.40;g.add(trunk);
 const leaves=[[-.30,-.04,.55,-.58],[.29,.04,.62,.54],[-.21,.03,.78,-.34],[.23,-.03,.87,.30],[0,.02,1.03,.04]];
 leaves.forEach(([x,y,z,rot],i)=>{const l=leafPlane(unit*.50,unit*.54,i%2?PLANT_COLORS.leaf2:PLANT_COLORS.leaf,1);l.position.set(unit*x,unit*y,z*unit);l.rotation.z=rot;l.rotation.x=Math.PI/2;l.rotation.y=(i-2)*.06;g.add(l)});
 return g;
}

function makeSansevieria(unit){
 const g=new THREE.Group();
 const xs=[-.23,-.14,-.05,.05,.14,.23];
 xs.forEach((x,i)=>{
  const h=unit*(.72+(i%3)*.18);
  const shape=new THREE.Shape();shape.moveTo(-unit*.055,0);shape.lineTo(unit*.055,0);shape.lineTo(unit*.018,h*.92);shape.lineTo(0,h);shape.lineTo(-unit*.018,h*.92);shape.closePath();
  const l=new THREE.Mesh(new THREE.ShapeGeometry(shape),new THREE.MeshStandardMaterial({color:i%2?0x46794a:0x315f38,roughness:.78,side:THREE.DoubleSide}));
  l.position.set(x*unit,(i%2?1:-1)*unit*.025,0);l.rotation.x=Math.PI/2;l.rotation.z=(i-2.5)*.045;l.rotation.y=(i%2?1:-1)*.08;l.userData.visual_only=true;g.add(l);
 });
 return g;
}

function makePothos(unit){
 const g=new THREE.Group();
 const stems=[-.25,-.08,.10,.25];
 stems.forEach((x,i)=>{
  const s=stem(unit*(.56+i*.07),unit*.010);s.position.set(unit*x,(i%2?1:-1)*unit*.02,unit*.20);s.rotation.y=(i-1.5)*.15;g.add(s);
  for(let j=0;j<3;j++){
   const l=leafPlane(unit*.25,unit*.29,(i+j)%2?PLANT_COLORS.leaf2:PLANT_COLORS.leaf);
   l.position.set(unit*(x+(j%2?-.10:.10)),(j-1)*unit*.018,unit*(.24+j*.19));l.rotation.x=Math.PI/2;l.rotation.z=(j%2?-.55:.55);g.add(l);
  }
 });
 return g;
}

function substrateColor(){
 return plantState.substrate==='white_stone'?0xe9e5dd:plantState.substrate==='volcanic'?0x433b38:0x4b3527;
}

function makeSubstrate(center,size,top){
 const g=new THREE.Group();
 // The pot program uses opening_width/opening_depth = 0.58 of the body width.
 // Keep the visual fill slightly inset and slightly below the rim to prevent
 // the old floating/oversized circle effect.
 const openingDiameter=Math.min(size.x,size.y)*.58;
 const radius=Math.max(2,openingDiameter*.485);
 const z=top-Math.max(.7,Math.min(size.z*.012,2.0));
 const disc=new THREE.Mesh(
  new THREE.CircleGeometry(radius,64),
  new THREE.MeshStandardMaterial({color:substrateColor(),roughness:1,metalness:0,side:THREE.DoubleSide})
 );
 disc.position.set(center.x,center.y,z);
 disc.userData={visual_only:true,exportable:false,role:'substrate'};
 g.add(disc);

 if(plantState.substrate!=='soil'){
  const stoneColor=plantState.substrate==='white_stone'?0xf2efe9:0x272321;
  const count=24;
  for(let i=0;i<count;i++){
   const a=(i/count)*Math.PI*2*3.7;
   const rr=radius*(.18+.70*((i*37)%101)/100);
   const sx=center.x+Math.cos(a)*rr, sy=center.y+Math.sin(a)*rr;
   const chip=new THREE.Mesh(
    new THREE.CircleGeometry(radius*(.035+((i*13)%7)*.004),8),
    new THREE.MeshStandardMaterial({color:stoneColor,roughness:1,side:THREE.DoubleSide})
   );
   chip.position.set(sx,sy,z+.08+(i%3)*.025);chip.userData.visual_only=true;g.add(chip);
  }
 }
 g.name='DOBO_VISUAL_ONLY_SUBSTRATE';
 g.userData={visual_only:true,exportable:false,substrate:plantState.substrate,opening_diameter_mm:openingDiameter};
 return g;
}

function updatePlantVisual(){
 if(!model)return;
 lastPotBox=new THREE.Box3().setFromObject(model);
 const size=lastPotBox.getSize(new THREE.Vector3()),center=lastPotBox.getCenter(new THREE.Vector3());
 const top=lastPotBox.max.z;
 const unit=Math.max(size.x,size.y)*.58*PLANT_SCALE[plantState.size];

 disposeVisualObject(visualPlantGroup);visualPlantGroup=null;
 disposeVisualObject(substrateGroup);substrateGroup=null;

 substrateGroup=makeSubstrate(center,size,top);
 scene.add(substrateGroup);

 const makers={ficus:makeFicus,monstera:makeMonstera,sansevieria:makeSansevieria,pothos:makePothos};
 visualPlantGroup=makers[plantState.plant](unit);
 visualPlantGroup.name='DOBO_VISUAL_ONLY_PLANT_2_5D';
 visualPlantGroup.position.set(center.x,center.y,top-.15);
 visualPlantGroup.userData={visual_only:true,exportable:false,render_mode:'2.5D',plant:plantState.plant,size:plantState.size};
 scene.add(visualPlantGroup);
}

function bindPlantUI(){
 document.querySelectorAll('#plantChoices [data-plant]').forEach(el=>el.onclick=()=>{
  document.querySelectorAll('#plantChoices [data-plant]').forEach(x=>x.classList.remove('active'));el.classList.add('active');plantState.plant=el.dataset.plant;updatePlantVisual();
 });
 document.querySelectorAll('#plantSizes [data-size]').forEach(el=>el.onclick=()=>{
  document.querySelectorAll('#plantSizes [data-size]').forEach(x=>x.classList.remove('active'));el.classList.add('active');plantState.size=el.dataset.size;updatePlantVisual();
 });
 document.querySelectorAll('#substrates [data-substrate]').forEach(el=>el.onclick=()=>{
  document.querySelectorAll('#substrates [data-substrate]').forEach(x=>x.classList.remove('active'));el.classList.add('active');plantState.substrate=el.dataset.substrate;updatePlantVisual();
 });
}

bindPlantUI();

// Hook the existing preview loader without altering the manufacturing request.
const doboOriginalLoadPreview=loadPreview;
loadPreview=async function(d){
 await doboOriginalLoadPreview(d);
 updatePlantVisual();
};
'''


def _inject(html: str) -> str:
    html = html.replace("</style></head>", PLANT_CSS + "\n</style></head>")
    html = html.replace(
        '<button class="generate" id="generate">Generar diseño real</button>',
        '<button class="generate" id="generate">Generar diseño real</button>\n' + PLANT_CONTROLS,
    )
    html = html.replace("</script></body></html>", PLANT_JS + "\n</script></body></html>")
    return html


base.HTML = _inject(base.HTML)
base.DESIGN_LAB_VERSION = base.DESIGN_LAB_VERSION + "+visual-plants-2.5d-v2"


if __name__ == "__main__":
    base.main()
