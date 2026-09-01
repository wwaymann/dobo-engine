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
    'y el texto "PLANTA\\nUNA\\nIDEA" en sobrerrelieve sobre la superficie exterior frontal.'
)


def _fixture():
    return _program(
        "native_cylindrical_multiline_regression",
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
                "PLANTA UNA IDEA",
                "text",
                "raised",
                region="front",
                horizontal=0.0,
                vertical=0.50,
                width=0.62,
                height=0.12,
                depth=1.50,
            )
        ],
        relations=[],
    )


def _angular_error_from_front(theta: np.ndarray) -> np.ndarray:
    # Canonical DOBO front is -Y, i.e. -pi/2 in atan2(y, x).
    return np.angle(np.exp(1j * (theta + 0.5 * math.pi)))


def test_native_cylindrical_multiline_text_regression() -> None:
    with TemporaryDirectory(prefix="dobo-native-text-") as temporary:
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

        # Isolate vertices that protrude beyond the analytic 55 mm cylinder.
        vertices = np.asarray(mesh.vertices, dtype=np.float64)
        radial = np.hypot(vertices[:, 0], vertices[:, 1])
        relief = vertices[radial > 55.20]
        assert len(relief) > 30, "Expected measurable native CAD relief vertices."

        theta = np.arctan2(relief[:, 1], relief[:, 0])
        error = _angular_error_from_front(theta)
        # The complete relief must remain in the frontal hemisphere and its
        # circular centre must stay close to the -Y meridian.
        assert np.percentile(np.abs(error), 95) < math.radians(75.0)
        mean_angle = math.atan2(float(np.mean(np.sin(theta))), float(np.mean(np.cos(theta))))
        centre_error = abs(float(_angular_error_from_front(np.asarray([mean_angle]))[0]))
        assert centre_error < math.radians(8.0)

        # Three explicit lines must occupy a real vertical block, not collapse
        # into a single baseline or shrink back to the old tiny-text regression.
        z_span = float(relief[:, 2].max() - relief[:, 2].min())
        assert z_span > 28.0


if __name__ == "__main__":
    test_native_cylindrical_multiline_text_regression()
    print("Native cylindrical multiline regression: PASS")
