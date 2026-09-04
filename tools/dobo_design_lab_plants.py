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
let visualPlantGroup=null,substrateGroup=null;
const PLANT_SCALE={small:.72,medium:1.0,large:1.34};
const C={leaf:0x356b3f,leaf2:0x4b8050,leaf3:0x254c32,stem:0x76563a};

function disposeVisual(o){if(!o)return;o.traverse?.(n=>{n.geometry?.dispose?.();if(n.material){(Array.isArray(n.material)?n.material:[n.material]).forEach(m=>m.dispose?.())}});scene.remove(o)}

function normalizePotForViewer(){
 if(!model)return;
 // Manufacturing geometry is untouched: this transform exists only in Three.js.
 model.rotation.set(-Math.PI/2,0,0);
 model.updateMatrixWorld(true);
 // Base Lab floor is XZ, therefore Y is the visual vertical axis.
 floor.position.set(0,-2,0);
 floor.updateMatrixWorld(true);
 fit();
}

function leafShape(w,h,notch=0){const s=new THREE.Shape();s.moveTo(0,-h*.5);s.bezierCurveTo(w*.62,-h*.34,w*.62,h*.22,0,h*.5);if(notch){s.bezierCurveTo(-w*.10,h*.36,-w*.13,h*.18,-w*.18,h*.08);s.bezierCurveTo(-w*.43,h*.26,-w*.62,-h*.08,0,-h*.5)}else{s.bezierCurveTo(-w*.62,h*.22,-w*.62,-h*.34,0,-h*.5)}return s}
function leaf(w,h,color=C.leaf,notch=0){const m=new THREE.Mesh(new THREE.ShapeGeometry(leafShape(w,h,notch),24),new THREE.MeshStandardMaterial({color,roughness:.84,side:THREE.DoubleSide}));m.userData.visual_only=true;return m}
function stem(h,r){const m=new THREE.Mesh(new THREE.CylinderGeometry(r,r*1.12,h,10),new THREE.MeshStandardMaterial({color:C.stem,roughness:.95}));m.userData.visual_only=true;return m}

// Plants are authored directly Y-up. Leaves are 2.5D cards with small depth offsets.
function makeFicus(u){const g=new THREE.Group();const t=stem(u*1.03,u*.018);t.position.y=u*.515;g.add(t);[[-.22,.62,-.025,-.40,.34,.46],[.21,.72,.025,.36,.37,.50],[-.18,.86,.04,-.50,.33,.44],[.18,.98,-.04,.43,.35,.48],[-.08,1.10,.03,-.16,.37,.50],[.09,1.22,-.02,.24,.35,.47]].forEach(([x,y,z,r,w,h],i)=>{const l=leaf(u*w,u*h,i%3===0?C.leaf3:(i%2?C.leaf2:C.leaf));l.position.set(u*x,u*y,u*z);l.rotation.z=r;l.rotation.y=(i%2?1:-1)*.12;g.add(l)});return g}
function makeMonstera(u){const g=new THREE.Group();const t=stem(u*.82,u*.016);t.position.y=u*.41;g.add(t);[[-.30,.55,-.04,-.58],[.29,.62,.04,.54],[-.21,.78,.03,-.34],[.23,.87,-.03,.30],[0,1.03,.02,.04]].forEach(([x,y,z,r],i)=>{const l=leaf(u*.50,u*.54,i%2?C.leaf2:C.leaf,1);l.position.set(u*x,u*y,u*z);l.rotation.z=r;l.rotation.y=(i-2)*.08;g.add(l)});return g}
function makeSansevieria(u){const g=new THREE.Group();[-.23,-.14,-.05,.05,.14,.23].forEach((x,i)=>{const h=u*(.72+(i%3)*.18),s=new THREE.Shape();s.moveTo(-u*.055,0);s.lineTo(u*.055,0);s.lineTo(u*.018,h*.92);s.lineTo(0,h);s.lineTo(-u*.018,h*.92);s.closePath();const l=new THREE.Mesh(new THREE.ShapeGeometry(s),new THREE.MeshStandardMaterial({color:i%2?0x46794a:0x315f38,roughness:.78,side:THREE.DoubleSide}));l.position.set(x*u,0,(i%2?1:-1)*u*.025);l.rotation.z=(i-2.5)*.045;l.rotation.y=(i%2?1:-1)*.08;l.userData.visual_only=true;g.add(l)});return g}
function makePothos(u){const g=new THREE.Group();[-.25,-.08,.10,.25].forEach((x,i)=>{const h=u*(.56+i*.07),s=stem(h,u*.010);s.position.set(u*x,h*.5,(i%2?1:-1)*u*.02);s.rotation.z=(i-1.5)*.10;g.add(s);for(let j=0;j<3;j++){const l=leaf(u*.25,u*.29,(i+j)%2?C.leaf2:C.leaf);l.position.set(u*(x+(j%2?-.10:.10)),u*(.24+j*.19),(j-1)*u*.025);l.rotation.z=j%2?-.55:.55;l.rotation.y=(j-1)*.12;g.add(l)}});return g}

function substrateColor(){return plantState.substrate==='white_stone'?0xe9e5dd:plantState.substrate==='volcanic'?0x433b38:0x4b3527}
function makeSubstrate(center,size,rimY){
 const g=new THREE.Group();
 // Profiled pots use a 0.58 opening ratio. Inset further so the fill never covers the rim.
 const openingDiameter=Math.min(size.x,size.z)*.58;
 const radius=Math.max(2,openingDiameter*.46);
 const y=rimY-Math.max(.8,Math.min(size.y*.018,2.2));
 const mat=new THREE.MeshStandardMaterial({color:substrateColor(),roughness:1,side:THREE.DoubleSide});
 const disc=new THREE.Mesh(new THREE.CircleGeometry(radius,64),mat);disc.rotation.x=-Math.PI/2;disc.position.set(center.x,y,center.z);disc.userData={visual_only:true,exportable:false,role:'substrate'};g.add(disc);
 if(plantState.substrate!=='soil'){
  const stoneColor=plantState.substrate==='white_stone'?0xf2efe9:0x272321;
  for(let i=0;i<26;i++){const a=i*2.3999632297,rr=radius*(.16+.72*((i*37)%101)/100),chip=new THREE.Mesh(new THREE.CircleGeometry(radius*(.032+((i*13)%7)*.004),8),new THREE.MeshStandardMaterial({color:stoneColor,roughness:1,side:THREE.DoubleSide}));chip.rotation.x=-Math.PI/2;chip.position.set(center.x+Math.cos(a)*rr,y+.06+(i%3)*.025,center.z+Math.sin(a)*rr);chip.userData.visual_only=true;g.add(chip)}
 }
 g.name='DOBO_VISUAL_ONLY_SUBSTRATE';g.userData={visual_only:true,exportable:false,substrate:plantState.substrate};return g
}

function updatePlantVisual(){
 if(!model)return;
 const box=new THREE.Box3().setFromObject(model),size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3()),rimY=box.max.y;
 const unit=Math.max(size.x,size.z)*.58*PLANT_SCALE[plantState.size];
 disposeVisual(visualPlantGroup);disposeVisual(substrateGroup);visualPlantGroup=null;substrateGroup=null;
 substrateGroup=makeSubstrate(center,size,rimY);scene.add(substrateGroup);
 const makers={ficus:makeFicus,monstera:makeMonstera,sansevieria:makeSansevieria,pothos:makePothos};visualPlantGroup=makers[plantState.plant](unit);visualPlantGroup.position.set(center.x,rimY-Math.max(.25,size.y*.006),center.z);visualPlantGroup.name='DOBO_VISUAL_ONLY_PLANT_2_5D';visualPlantGroup.userData={visual_only:true,exportable:false,render_mode:'2.5D',plant:plantState.plant,size:plantState.size};scene.add(visualPlantGroup);
 // Fit after all presentation objects exist, but frame from the pot + plant rather than the huge floor.
 const viewBox=new THREE.Box3().setFromObject(model).union(new THREE.Box3().setFromObject(visualPlantGroup));const vs=viewBox.getSize(new THREE.Vector3()),vc=viewBox.getCenter(new THREE.Vector3()),m=Math.max(vs.x,vs.y,vs.z);controls.target.copy(vc);camera.position.set(vc.x+1.45*m,vc.y+.72*m,vc.z+1.65*m);controls.update();
}

function bindPlantUI(){document.querySelectorAll('#plantChoices [data-plant]').forEach(el=>el.onclick=()=>{document.querySelectorAll('#plantChoices [data-plant]').forEach(x=>x.classList.remove('active'));el.classList.add('active');plantState.plant=el.dataset.plant;updatePlantVisual()});document.querySelectorAll('#plantSizes [data-size]').forEach(el=>el.onclick=()=>{document.querySelectorAll('#plantSizes [data-size]').forEach(x=>x.classList.remove('active'));el.classList.add('active');plantState.size=el.dataset.size;updatePlantVisual()});document.querySelectorAll('#substrates [data-substrate]').forEach(el=>el.onclick=()=>{document.querySelectorAll('#substrates [data-substrate]').forEach(x=>x.classList.remove('active'));el.classList.add('active');plantState.substrate=el.dataset.substrate;updatePlantVisual()})}
bindPlantUI();

const doboOriginalLoadPreview=loadPreview;
loadPreview=async function(d){await doboOriginalLoadPreview(d);normalizePotForViewer();updatePlantVisual()};
'''

def _inject(html: str) -> str:
    html = html.replace("</style></head>", PLANT_CSS + "\n</style></head>")
    html = html.replace('<button class="generate" id="generate">Generar diseño real</button>','<button class="generate" id="generate">Generar diseño real</button>\n' + PLANT_CONTROLS)
    html = html.replace("</script></body></html>", PLANT_JS + "\n</script></body></html>")
    return html

base.HTML = _inject(base.HTML)
base.DESIGN_LAB_VERSION = base.DESIGN_LAB_VERSION + "+visual-plants-2.5d-yup-v3"

if __name__ == "__main__":
    base.main()
