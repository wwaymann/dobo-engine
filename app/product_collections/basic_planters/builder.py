from __future__ import annotations
import os
from kernel.contracts.config import ExportConfiguration, ExportFormat
from kernel.contracts.geometry_definition import GeometryDefinition
from kernel.contracts.geometry_definition_set import GeometryDefinitionSet
from kernel.contracts.geometry_operation_type import GeometryOperationType
from kernel.contracts.geometry_request import GeometryRequest
from kernel.contracts.operations import ExportOperation, GeometryOperation, ShellOperation
from .profiles import build_contour
from .specification import BasicPlanterSpecification

class BasicPlanterCollectionBuilder:
    OUTPUT_DIRECTORY = 'outputs/product_collections/basic_planters'

    @staticmethod
    def source_body_id(specification): return f'{specification.id}:source'
    @staticmethod
    def final_body_id(specification): return f'{specification.id}:body'

    def build_geometry_operation(self, specification: BasicPlanterSpecification) -> GeometryOperation:
        specification.validate()
        output_id=self.source_body_id(specification)
        return self._build_extrude(specification, output_id=output_id) if abs(float(specification.top_scale)-1.0)<1e-12 else self._build_loft(specification, output_id=output_id)

    def build_shell_operation(self, specification: BasicPlanterSpecification, *, top_face_index: int) -> ShellOperation:
        specification.validate()
        if isinstance(top_face_index,bool) or not isinstance(top_face_index,int) or top_face_index<0:
            raise ValueError('top_face_index must be a non-negative integer.')
        op=ShellOperation(id=f'{specification.id}:shell', name=f'{specification.name} Shell', source_id=self.source_body_id(specification), output_id=self.final_body_id(specification), thickness=-float(specification.wall_thickness), tolerance=0.01, remove_face_indices=(top_face_index,), metadata={'collection':'basic_planters','product_id':specification.id,'resolved_top_face_index':top_face_index})
        op.validate(); return op

    def build_export_operation(self, specification: BasicPlanterSpecification) -> ExportOperation:
        destination=os.path.join(self.OUTPUT_DIRECTORY,specification.resolved_export_filename)
        op=ExportOperation(id=f'{specification.id}:export', name=f'Export {specification.name}', source_id=self.final_body_id(specification), configuration=ExportConfiguration(enabled=True,format=ExportFormat.STEP,destination=destination,tolerance=0.01,angular_tolerance=0.1,units='mm',metadata={'collection':'basic_planters','product_id':specification.id}), overwrite=True, metadata={'collection':'basic_planters','product_id':specification.id})
        op.validate(); return op

    def _build_extrude(self,specification,*,output_id):
        contour=build_contour(specification.profile,specification.width,specification.depth,corner_radius=specification.corner_radius,scale=1.0,contour_id=f'{specification.id}:outer')
        definition=GeometryDefinition(id=f'{specification.id}:definition',outer_contour=contour,source='basic_planters'); definition.validate()
        geometry=GeometryDefinitionSet(id=f'{specification.id}:geometry',definitions=(definition,),source='basic_planters'); geometry.validate()
        request=GeometryRequest(id=f'{specification.id}:request',geometry=geometry,operation=GeometryOperationType.EXTRUDE,parameters={'distance':float(specification.height),'direction':(0.0,0.0,1.0),'symmetric':False,'draft_angle':0.0},output_id=output_id,metadata={'collection':'basic_planters','product_id':specification.id}); request.validate()
        op=GeometryOperation(id=f'{specification.id}:geometry-operation',name=f'{specification.name} Geometry',request=request,output_id=output_id,tags=('collection','basic_planters',specification.id)); op.validate(); return op

    def _build_loft(self,specification,*,output_id):
        bottom=GeometryDefinition(id=f'{specification.id}:bottom-definition',outer_contour=build_contour(specification.profile,specification.width,specification.depth,corner_radius=specification.corner_radius,scale=1.0,contour_id=f'{specification.id}:bottom'),source='basic_planters')
        top=GeometryDefinition(id=f'{specification.id}:top-definition',outer_contour=build_contour(specification.profile,specification.width,specification.depth,corner_radius=specification.corner_radius,scale=specification.top_scale,contour_id=f'{specification.id}:top'),source='basic_planters')
        bottom.validate(); top.validate()
        geometry=GeometryDefinitionSet(id=f'{specification.id}:geometry',definitions=(bottom,top),source='basic_planters'); geometry.validate()
        xo=-(specification.width*(specification.top_scale-1.0)/2.0); yo=-(specification.depth*(specification.top_scale-1.0)/2.0)
        request=GeometryRequest(id=f'{specification.id}:request',geometry=geometry,operation=GeometryOperationType.LOFT,parameters={'solid':True,'ruled':False,'section_offsets':((0.0,0.0,0.0),(float(xo),float(yo),float(specification.height)))},output_id=output_id,metadata={'collection':'basic_planters','product_id':specification.id}); request.validate()
        op=GeometryOperation(id=f'{specification.id}:geometry-operation',name=f'{specification.name} Loft',request=request,output_id=output_id,tags=('collection','basic_planters',specification.id)); op.validate(); return op
