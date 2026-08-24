from __future__ import annotations

from .phase_5_design_matrix import _feature, _program
from .phase_d_visual_matrix import DVisualCase


def _human_face_features() -> list[dict]:
    f=[]
    f += [_feature("left_eye","eye","slit","recessed",region="front",horizontal=-.23,vertical=.62,width=.14,height=.055,depth=1.8,roll=-3),_feature("right_eye","eye","slit","recessed",region="front",horizontal=.23,vertical=.62,width=.14,height=.055,depth=1.8,roll=3)]
    f += [_feature("nose","nose","point","raised",region="front",horizontal=0,vertical=.48,width=.13,height=.23,depth=3.0),_feature("mouth","mouth","slit","recessed",region="front",horizontal=0,vertical=.31,width=.27,height=.055,depth=1.5)]
    for i,x in enumerate((-.48,-.34,-.18,.18,.34,.48)):
        f.append(_feature(f"hair_{i}","hair_lock","leaf","raised",region="upper",horizontal=x,vertical=.78-.05*abs(i-2.5),width=.18,height=.36,depth=3.0,roll=18*x))
    return f


def _relief_features(prefix:str, recessed:bool=False) -> list[dict]:
    f=[]
    for row,v in enumerate((.25,.43,.61,.78)):
        for col,h in enumerate((-.72,-.42,-.12,.18,.48,.72)):
            effect="recessed" if recessed and (row+col)%2 else "raised"
            hint="leaf" if (row+col)%3 else "point"
            f.append(_feature(f"{prefix}_{row}_{col}","ornamental_leaf",hint,effect,region="front",horizontal=h,vertical=v,width=.15,height=.14,depth=2.7,roll=(row*17+col*23)%70-35))
    return f


def _perforation_features() -> list[dict]:
    f=[]
    for row,v in enumerate((.24,.42,.60,.76)):
        for col,h in enumerate((-.68,-.38,-.08,.22,.52)):
            f.append(_feature(f"void_{row}_{col}","organic_void","oval","recessed",region="front",horizontal=h,vertical=v,width=.16+(col%2)*.04,height=.13+(row%2)*.04,depth=3.0,roll=(row*29+col*31)%80-40))
    return f


def _case(case_id,label,profile,goal,*,height,width,depth,opening_shape,tags,features):
    p=_program(f"d2_{case_id}",goal,family="hexagonal" if "origami" in tags else "organic",height=height,width=width,depth=depth,opening_shape=opening_shape,opening_width=.58,opening_depth=.55,style_tags=tags,features=features,relations=[])
    return DVisualCase(case_id,label,profile,goal,p)


def d2_visual_matrix() -> tuple[DVisualCase,...]:
    probe=lambda cid:[_feature(f"{cid}_probe","ridge","slit","recessed",region="front",horizontal=0,vertical=.44,width=.12,height=.035,depth=.8)]
    return (
      _case("organic_asymmetric","Organic asymmetric","undulating_shell","Silueta orgánica asimétrica, ondulada y no cilíndrica.",height=112,width=132,depth=118,opening_shape="elliptical",tags=["organic_asymmetric","undulating"],features=probe("organic")),
      _case("figurative_sculptural","Figurative / sculptural","sculptural_cluster","Rostro escultórico integrado al volumen, con ojos, nariz, boca y masas de cabello físicamente modeladas.",height=126,width=116,depth=108,opening_shape="elliptical",tags=["sculptural_cluster","compound_sculpture"],features=_human_face_features()),
      _case("geometric_faceted","Geometric / faceted","origami_crown","Volumen facetado de planos tensos y corona arquitectónica.",height=108,width=128,depth=128,opening_shape="polygonal",tags=["geometric","origami","architectural_folded"],features=probe("facet")),
      _case("complex_relief_body","Complex relief","undulating_shell","Relieve ornamental profundo y jerárquico distribuido sobre una envolvente orgánica.",height=110,width=130,depth=122,opening_shape="elliptical",tags=["biomorphic_shell","wavy_shell"],features=_relief_features("relief",True)),
      _case("integrated_text_body","Integrated text","sculptural_cluster","Plano frontal dominante preparado para texto físico conformado, con marco escultórico claramente diferenciado.",height=112,width=138,depth=108,opening_shape="elliptical",tags=["sculptural_cluster","multi_volume_sculptural"],features=[_feature("text_panel","plaque","oval","raised",region="front",horizontal=0,vertical=.48,width=.62,height=.30,depth=2.2)]+_relief_features("frame")[:8]),
      _case("perforated_biomorphic_body","Perforated / biomorphic","undulating_shell","Patrón orgánico de vacíos profundos distribuido irregularmente sobre la envolvente.",height=116,width=130,depth=126,opening_shape="elliptical",tags=["organic_asymmetric","biomorphic_shell"],features=_perforation_features()),
      _case("spiral_dynamic","Spiral / dynamic","spiral_ribbed","Ascenso helicoidal fuerte con costillas en torsión continua.",height=120,width=122,depth=122,opening_shape="circular",tags=["spiral_ribbed","dynamic_spiral","helical_ribs"],features=probe("spiral")),
      _case("origami_architectural","Origami / architectural","origami_crown","Pliegues arquitectónicos agudos, ritmo poligonal y corona fuertemente marcada.",height=122,width=132,depth=132,opening_shape="polygonal",tags=["origami","folded_crown","pleated"],features=probe("origami")),
    )
