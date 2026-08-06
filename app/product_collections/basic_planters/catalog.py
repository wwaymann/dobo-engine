from __future__ import annotations
from .specification import BasicPlanterSpecification
BASIC_PLANTER_CATALOG=(
BasicPlanterSpecification(id="square_planter",name="Square Planter",profile="rectangle",width=120,depth=120,height=140),
BasicPlanterSpecification(id="round_planter",name="Round Planter",profile="circle",width=130,depth=130,height=140),
BasicPlanterSpecification(id="oval_planter",name="Oval Planter",profile="ellipse",width=160,depth=110,height=120),
BasicPlanterSpecification(id="hex_planter",name="Hexagonal Planter",profile="hexagon",width=140,depth=125,height=135),
BasicPlanterSpecification(id="conic_planter",name="Conic Planter",profile="circle",width=115,depth=115,height=150,top_scale=1.22),
BasicPlanterSpecification(id="rounded_square_planter",name="Rounded Square Planter",profile="rounded_rectangle",width=125,depth=125,height=135,corner_radius=18),
BasicPlanterSpecification(id="rounded_rectangle_planter",name="Rounded Rectangle Planter",profile="rounded_rectangle",width=165,depth=105,height=120,corner_radius=16),
BasicPlanterSpecification(id="saucer",name="Round Saucer",profile="circle",width=145,depth=145,height=16,wall_thickness=3),
BasicPlanterSpecification(id="drain_tray",name="Drain Tray",profile="rounded_rectangle",width=155,depth=120,height=18,wall_thickness=3,corner_radius=12),
)
for _s in BASIC_PLANTER_CATALOG: _s.validate()
