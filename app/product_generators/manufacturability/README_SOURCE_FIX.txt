DOBO Phase 7.5 source.py fix

Replace:
app/product_generators/manufacturability/source.py

Then run:

python -m py_compile app\product_generators\manufacturability\source.py
python -m py_compile app\product_generators\manufacturability\stability.py
python -m product_generators.manufacturability.test_phase_7_5_cavity_drainage
