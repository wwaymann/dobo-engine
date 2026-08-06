from __future__ import annotations
from features.builders.extrude_operation_builder import ExtrudeOperationBuilder
from features.builders.modeling_operation_builder import ModelingOperationBuilder
from features.contracts import BooleanMode, FeatureContext
from features.definitions.extrude_feature_definition import ExtrudeFeatureDefinition
from features.definitions.modeling_feature_definition import ModelingFeatureDefinition
from kernel.contracts.model_state import ModelState
from kernel.contracts.operations.modeling_operation import ModelingTool
from kernel.core.kernel_model import KernelModel
from testing import build_kernel_engine, build_rectangle_region_set

CASES={
 ModelingTool.MOVE:{'vector':(5.0,0.0,0.0)},
 ModelingTool.ROTATE:{'axis_origin':(0.0,0.0,0.0),'axis_direction':(0.0,0.0,1.0),'angle':30.0},
 ModelingTool.SCALE:{'factor':1.1},
 ModelingTool.MIRROR:{'plane':'YZ','base_point':(0.0,0.0,0.0)},
 ModelingTool.FILLET:{'radius':1.0,'edge_indices':(0,)},
 ModelingTool.CHAMFER:{'length':1.0,'edge_indices':(0,)},
 ModelingTool.LINEAR_PATTERN:{'direction':(1.0,0.0,0.0),'spacing':20.0,'count':3},
 ModelingTool.CIRCULAR_PATTERN:{'axis_origin':(0.0,0.0,0.0),'axis_direction':(0.0,0.0,1.0),'total_angle':360.0,'count':4},
}

def run(tool,parameters):
    regions=build_rectangle_region_set(region_set_id=f'{tool.value}_regions',width=10.0,height=10.0)
    context=FeatureContext(model=ModelState()); context.register_regions(f'{tool.value}_regions',regions)
    base=ExtrudeFeatureDefinition(id=f'{tool.value}_base',name='Base',region_set_id=f'{tool.value}_regions',region_id=regions.regions[0].id,output_id='source_body',distance=10.0,mode=BooleanMode.NEW_BODY)
    feature=ModelingFeatureDefinition(id=f'{tool.value}_feature',name=tool.value,source_body_id='source_body',output_id=f'{tool.value}_body',tool=tool,parameters=parameters)
    base_plan=ExtrudeOperationBuilder().build(base,context); tool_plan=ModelingOperationBuilder().build(feature,context)
    model=KernelModel(name=f'{tool.value} test')
    for op in (*base_plan.operations,*tool_plan.operations): model.add_operation(op)
    result=build_kernel_engine(include_boolean=False,include_export=False).execute(model)
    result.validate()
    if not result.succeeded:
        errors=[r.error_message for r in result.operations if r.failed]
        raise RuntimeError(f'{tool.value} failed: {errors}')
    print(tool.value, result.solids[f'{tool.value}_body'].volume, 'OK')

def main():
    for tool,params in CASES.items(): run(tool,params)
    print('DOBO Modeling Tools Pack: Valid OK')

if __name__=='__main__': main()
