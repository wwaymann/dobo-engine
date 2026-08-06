from __future__ import annotations
import os
from dataclasses import dataclass
from kernel.core.execution_context import KernelExecutionContext
from testing import build_dispatcher
from .builder import BasicPlanterCollectionBuilder
from .geometry_inspector import BasicPlanterGeometryInspector
from .specification import BasicPlanterSpecification

@dataclass(slots=True)
class BasicPlanterRunResult:
    specification: BasicPlanterSpecification
    context: KernelExecutionContext
    top_face_index: int
    export_path: str
    @property
    def final_body_id(self) -> str: return f'{self.specification.id}:body'

class BasicPlanterCollectionRunner:
    def __init__(self,builder=None,inspector=None):
        self._builder=builder or BasicPlanterCollectionBuilder(); self._inspector=inspector or BasicPlanterGeometryInspector()
    def run(self,specification: BasicPlanterSpecification) -> BasicPlanterRunResult:
        specification.validate()
        dispatcher=build_dispatcher(include_geometry=True,include_boolean=False,include_shell=True,include_modeling=False,include_export=True)
        context=KernelExecutionContext(metadata={'collection':'basic_planters','product_id':specification.id})
        geometry_operation=self._builder.build_geometry_operation(specification); dispatcher.dispatch(geometry_operation,context)
        source_id=self._builder.source_body_id(specification)
        if not context.solids.contains(source_id): raise RuntimeError(f'{specification.id}: source solid missing')
        source=context.solids.get(source_id)
        top_face_index=self._inspector.top_face_index(source)
        shell_operation=self._builder.build_shell_operation(specification,top_face_index=top_face_index); dispatcher.dispatch(shell_operation,context)
        final_id=self._builder.final_body_id(specification)
        if not context.solids.contains(final_id): raise RuntimeError(f'{specification.id}: final solid missing')
        payload=dispatcher.dispatch(self._builder.build_export_operation(specification),context)
        if payload.export_path is None or not os.path.isfile(payload.export_path): raise RuntimeError(f'{specification.id}: STEP export failed')
        context.validate()
        return BasicPlanterRunResult(specification,context,top_face_index,payload.export_path)
