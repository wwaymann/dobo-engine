from __future__ import annotations
from .catalog import BASIC_PLANTER_CATALOG
from .runner import BasicPlanterCollectionRunner

def main() -> None:
    runner=BasicPlanterCollectionRunner()
    print(); print('DOBO Basic Planters - Phase 1'); print('-----------------------------')
    completed=0
    for spec in BASIC_PLANTER_CATALOG:
        result=runner.run(spec)
        solid=result.context.solids.get(result.final_body_id); solid.validate()
        print(spec.id, round(float(solid.volume),3), 'top-face', result.top_face_index, 'OK')
        completed+=1
    print('-----------------------------'); print('Products:',completed); print('Phase 1: Valid OK'); print()
if __name__=='__main__': main()
