from __future__ import annotations

import math
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

APP = Path(__file__).resolve().parents[2]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

from product_generators.design_interpreter.phase_5_design_matrix import _feature, _program
from product_generators.design_interpreter.structural_pipeline import DoboStructuralPipeline


PROMPT = (
    'Crea una maceta cilíndrica hueca, con abertura superior, drenaje inferior '
    'y el texto "WALTER" en bajorrelieve sobre la superficie exterior frontal.'
)


def _fixture():
    return _program(
        "native_cylindrical_deboss_regression",
        PROMPT,
        family="cylindrical",
        height=115.0,
        width=110.0,
        depth=110.0,
        opening_shape="circular",
        opening_width=0.58,
        opening_depth=0.58,
        style_tags=["cylindrical"],
        features=[
            _feature(
                "front_text",
                "walter",
                "text",
                "recessed",
                region="front",
                horizontal=0.0,
                vertical=0.50,
                width=0.62,
                height=0.12,
                depth=1.20,
            )
        ],
        relations=[],
    )


def _angular_error_from_front(theta: np.ndarray) -> np.ndarray:
    return np.angle(np.exp(1j * (theta + 0.5 * math.pi)))


def test_native_cylindrical_deboss_regression() -> None:
    with TemporaryDirectory(prefix="dobo-native-deboss-") as temporary:
        result = DoboStructuralPipeline().generate_from_semantic(
            _fixture(), output_root=Path(temporary)
        )

        mesh = result.mesh_result.mesh
        checks = result.mesh_result.semantic_checks

        assert result.trace.mesh_quality_profile == "analytic_cad_native_text"
        assert result.mesh_result.component_count == 1
        assert result.mesh_result.watertight
        assert result.mesh_result.winding_consistent
        assert checks["cavity_is_empty"]
        assert checks["opening_is_clear"]
        assert checks["drain_is_clear"]

        vertices = np.asarray(mesh.vertices, dtype=np.float64)
        radial = np.hypot(vertices[:, 0], vertices[:, 1])
        theta = np.arctan2(vertices[:, 1], vertices[:, 0])
        front_error = np.abs(_angular_error_from_front(theta))

        # Exterior cylinder radius is 55 mm. A real deboss must create surface
        # vertices measurably inside that radius, but still far outside the
        # cavity wall. Restrict to the canonical frontal text band so inner-wall
        # vertices cannot satisfy the test accidentally.
        recessed = vertices[
            (radial > 53.0)
            & (radial < 54.90)
            & (front_error < math.radians(70.0))
            & (vertices[:, 2] > 35.0)
            & (vertices[:, 2] < 80.0)
        ]
        assert len(recessed) > 20, "Expected measurable frontal native CAD deboss vertices."

        recessed_theta = np.arctan2(recessed[:, 1], recessed[:, 0])
        recessed_error = _angular_error_from_front(recessed_theta)
        assert np.percentile(np.abs(recessed_error), 95) < math.radians(70.0)


if __name__ == "__main__":
    test_native_cylindrical_deboss_regression()
    print("Native cylindrical deboss regression: PASS")
