DOBO Phase 7.8 Static Type Fixes

Replace these files:

app\product_generators\manufacturability\stability.py
app\product_generators\manufacturability\source.py

Fixes:

source.py
- removes generic Workplane.val() results from fixture solids
- uses findSolid()
- removes unnecessary cq.Shape.cast()
- adds explicit cq.Solid / cq.Shape annotations

stability.py
- explicitly narrows Workplane.edges().vals() objects to cq.Edge
- avoids Pylance CQObject/Vector/Location false positives
- keeps validated section-footprint stability algorithm
- keeps cq.Shape.centerOfMass(shape) compatibility

Run:

python -m py_compile app\product_generators\manufacturability\source.py
python -m py_compile app\product_generators\manufacturability\stability.py

python -m product_generators.manufacturability.test_phase_7_5_cavity_drainage
python -m product_generators.manufacturability.test_phase_7_8_color_final_production
