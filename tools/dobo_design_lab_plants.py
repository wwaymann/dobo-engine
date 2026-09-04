from __future__ import annotations

"""Visual-only plant layer for DOBO Design Lab.

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
<h3>8 · Planta · vista previa</h3>
<div class="hint">Esta capa es solo visual. No se incorpora al STL ni al 3MF.</div>
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
let substrateMesh=null;
let lastPotBox=null;

const PLANT_SCALE={small:.72,medium:1.0,large:1.34};
const PLANT_COLORS={leaf:0x356b3f,leaf2:0x4b8050,stem:0x76563a};

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

function ellipseLeaf(width,height,color=PLANT_COLORS.leaf){
 const shape=new THREE.Shape();
 shape.moveTo(0,-height*.5);
 shape.bezierCurveTo(width*.62,-height*.38,width*.62,height*.28,0,height*.5);
 shape.bezierCurveTo(-width*.62,height*.28,-width*.62,-height*.38,0,-height*.5);
 const mesh=new THREE.Mesh(
  new THREE.ShapeGeometry(shape,20),
  new THREE.MeshStandardMaterial({color,roughness:.8,metalness:0,side:THREE.DoubleSide})
 );
 return mesh;
}

function stem(length,radius=.7){
 const mesh=new THREE.Mesh(
  new THREE.CylinderGeometry(radius,radius*1.15,length,10),
  new THREE.MeshStandardMaterial({color:PLANT_COLORS.stem,roughness:.95})
 );
 mesh.rotation.x=Math.PI/2;
 return mesh;
}

function makeFicus(unit){
 const g=new THREE.Group();
 const trunk=stem(unit*1.05,unit*.018);trunk.position.z=unit*.52;g.add(trunk);
 const leaves=[
  [-.20,.62,-.35,.34,.46],[.19,.73,.34,.36,.50],[-.16,.86,-.45,.32,.44],
  [.16,.98,.42,.34,.47],[-.08,1.10,-.15,.36,.50],[.08,1.22,.22,.34,.46]
 ];
 leaves.forEach(([x,z,rot,w,h],i)=>{const l=ellipseLeaf(unit*w,unit*h,i%2?PLANT_COLORS.leaf2:PLANT_COLORS.leaf);l.position.set(unit*x,0,z*unit);l.rotation.z=rot;l.rotation.x=Math.PI/2;g.add(l)});
 return g;
}

function makeMonstera(unit){
 const g=new THREE.Group();
 const trunk=stem(unit*.82,unit*.016);trunk.position.z=unit*.4;g.add(trunk);
 const leaves=[[-.28,.56,-.55],[.28,.62,.52],[-.20,.78,-.32],[.22,.86,.28],[0,1.02,0]];
 leaves.forEach(([x,z,rot],i)=>{const l=ellipseLeaf(unit*.48,unit*.52,i%2?PLANT_COLORS.leaf2:PLANT_COLORS.leaf);l.position.set(unit*x,0,z*unit);l.rotation.z=rot;l.rotation.x=Math.PI/2;g.add(l)});
 return g;
}

function makeSansevieria(unit){
 const g=new THREE.Group();
 const xs=[-.22,-.12,-.04,.05,.13,.22];
 xs.forEach((x,i)=>{
  const h=unit*(.70+(i%3)*.18);
  const shape=new THREE.Shape();shape.moveTo(-unit*.055,0);shape.lineTo(unit*.055,0);shape.lineTo(unit*.018,h*.92);shape.lineTo(0,h);shape.lineTo(-unit*.018,h*.92);shape.closePath();
  const l=new THREE.Mesh(new THREE.ShapeGeometry(shape),new THREE.MeshStandardMaterial({color:i%2?0x46794a:0x315f38,roughness:.75,side:THREE.DoubleSide}));
  l.position.x=x*unit;l.rotation.x=Math.PI/2;l.rotation.z=(i-2.5)*.045;g.add(l);
 });
 return g;
}

function makePothos(unit){
 const g=new THREE.Group();
 const stems=[-.24,-.08,.10,.24];
 stems.forEach((x,i)=>{
  const s=stem(unit*(.58+i*.08),unit*.010);s.position.set(unit*x,0,unit*.20);s.rotation.y=(i-1.5)*.15;g.add(s);
  for(let j=0;j<3;j++){
   const l=ellipseLeaf(unit*.24,unit*.28,(i+j)%2?PLANT_COLORS.leaf2:PLANT_COLORS.leaf);
   l.position.set(unit*(x+(j%2?-.10:.10)),0,unit*(.25+j*.20));l.rotation.x=Math.PI/2;l.rotation.z=(j%2?-.55:.55);g.add(l);
  }
 });
 return g;
}

function substrateColor(){
 return plantState.substrate==='white_stone'?0xe7e2d8:plantState.substrate==='volcanic'?0x4b403b:0x4a3327;
}

function updatePlantVisual(){
 if(!model)return;
 lastPotBox=new THREE.Box3().setFromObject(model);
 const size=lastPotBox.getSize(new THREE.Vector3()),center=lastPotBox.getCenter(new THREE.Vector3());
 const top=lastPotBox.max.z;
 const unit=Math.max(size.x,size.y)*.58*PLANT_SCALE[plantState.size];
 const openingRadius=Math.max(6,Math.min(size.x,size.y)*.23);

 disposeVisualObject(visualPlantGroup);visualPlantGroup=null;
 if(substrateMesh){disposeVisualObject(substrateMesh);substrateMesh=null}

 substrateMesh=new THREE.Mesh(
  new THREE.CircleGeometry(openingRadius,48),
  new THREE.MeshStandardMaterial({color:substrateColor(),roughness:1,metalness:0,side:THREE.DoubleSide})
 );
 substrateMesh.position.set(center.x,center.y,top+.35);
 substrateMesh.rotation.x=0;
 substrateMesh.renderOrder=2;
 scene.add(substrateMesh);

 const makers={ficus:makeFicus,monstera:makeMonstera,sansevieria:makeSansevieria,pothos:makePothos};
 visualPlantGroup=makers[plantState.plant](unit);
 visualPlantGroup.name='DOBO_VISUAL_ONLY_PLANT';
 visualPlantGroup.position.set(center.x,center.y,top+.5);
 visualPlantGroup.userData={visual_only:true,exportable:false,plant:plantState.plant,size:plantState.size};
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
base.DESIGN_LAB_VERSION = base.DESIGN_LAB_VERSION + "+visual-plants-1"


if __name__ == "__main__":
    base.main()
