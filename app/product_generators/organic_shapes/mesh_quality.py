from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import trimesh


@dataclass(frozen=True, slots=True)
class OrganicMeshQualityContract:
    subdivision_passes: int
    projection_iterations: int
    projection_epsilon_mm: float
    max_surface_error_mm: float
    iterations: int
    lambda_factor: float
    mu_factor: float
    rim_axial_band_mm: float
    rim_radial_band: float
    max_displacement_mm: float
    base_protection_mm: float
    drain_protection_mm: float
    max_volume_drift_percent: float
    minimum_roughness_improvement_percent: float

    def validate(self) -> None:
        if self.subdivision_passes < 1 or self.subdivision_passes > 2:
            raise ValueError(
                "mesh_quality.subdivision_passes must be between 1 and 2."
            )
        if self.projection_iterations < 1 or self.projection_iterations > 6:
            raise ValueError(
                "mesh_quality.projection_iterations must be between 1 and 6."
            )
        if self.iterations < 1 or self.iterations > 12:
            raise ValueError("mesh_quality.iterations must be between 1 and 12.")
        if not 0.0 < self.lambda_factor < 1.0:
            raise ValueError("mesh_quality.lambda_factor must be between 0 and 1.")
        if not -1.0 < self.mu_factor < 0.0:
            raise ValueError("mesh_quality.mu_factor must be between -1 and 0.")
        if abs(self.mu_factor) < self.lambda_factor:
            raise ValueError("Taubin mu magnitude must be at least lambda_factor.")
        positive = {
            "rim_axial_band_mm": self.rim_axial_band_mm,
            "rim_radial_band": self.rim_radial_band,
            "projection_epsilon_mm": self.projection_epsilon_mm,
            "max_surface_error_mm": self.max_surface_error_mm,
            "max_displacement_mm": self.max_displacement_mm,
            "base_protection_mm": self.base_protection_mm,
            "drain_protection_mm": self.drain_protection_mm,
            "max_volume_drift_percent": self.max_volume_drift_percent,
        }
        invalid = [name for name, value in positive.items() if value <= 0.0]
        if invalid:
            raise ValueError(f"Mesh-quality values must be positive: {invalid}")
        if self.minimum_roughness_improvement_percent < 0.0:
            raise ValueError(
                "mesh_quality.minimum_roughness_improvement_percent cannot be negative."
            )


@dataclass(frozen=True, slots=True)
class OrganicMeshQualityMetrics:
    input_face_count: int
    refined_face_count: int
    active_vertex_count: int
    protected_vertex_count: int
    iterations_applied: int
    roughness_before_mm: float
    roughness_after_mm: float
    roughness_improvement_percent: float
    volume_drift_percent: float
    total_volume_drift_percent: float
    maximum_displacement_mm: float
    protected_displacement_mm: float
    mean_surface_error_mm: float
    maximum_surface_error_mm: float
    maximum_base_plane_error_mm: float
    maximum_base_perimeter_error_mm: float
    maximum_base_transition_error_mm: float
    maximum_drain_radius_error_mm: float

    def validate(self, contract: OrganicMeshQualityContract) -> None:
        if self.refined_face_count <= self.input_face_count:
            raise RuntimeError("Localized mesh refinement did not increase rim density.")
        if self.active_vertex_count <= 0:
            raise RuntimeError("Localized mesh refinement selected no rim vertices.")
        if self.protected_vertex_count <= 0:
            raise RuntimeError("Localized mesh refinement protected no functional vertices.")
        if self.iterations_applied <= 0:
            raise RuntimeError("Localized mesh refinement applied no valid iteration.")
        if self.roughness_improvement_percent < (
            contract.minimum_roughness_improvement_percent
        ):
            raise RuntimeError(
                "Localized mesh refinement did not meet the roughness target."
            )
        if self.volume_drift_percent > contract.max_volume_drift_percent:
            raise RuntimeError("Localized mesh refinement exceeded the volume-drift limit.")
        if self.total_volume_drift_percent > contract.max_volume_drift_percent:
            raise RuntimeError(
                "Localized mesh refinement exceeded total volume drift from input."
            )
        if self.maximum_displacement_mm > contract.max_displacement_mm + 1e-9:
            raise RuntimeError("Localized mesh refinement exceeded its displacement limit.")
        if self.protected_displacement_mm > 1e-9:
            raise RuntimeError("Localized mesh refinement moved protected geometry.")
        if self.maximum_surface_error_mm > contract.max_surface_error_mm:
            raise RuntimeError(
                "Localized mesh refinement exceeded the SDF surface-error limit."
            )
        functional_error = max(
            self.maximum_base_plane_error_mm,
            self.maximum_base_perimeter_error_mm,
            self.maximum_base_transition_error_mm,
            self.maximum_drain_radius_error_mm,
        )
        if functional_error > contract.max_surface_error_mm:
            raise RuntimeError(
                "Localized mesh refinement exceeded a functional-geometry limit."
            )


class LocalizedTaubinRefiner:
    @classmethod
    def refine(
        cls,
        mesh: trimesh.Trimesh,
        contract: OrganicMeshQualityContract,
        *,
        opening_center: tuple[float, float],
        opening_radii: tuple[float, float],
        opening_start_z_mm: float,
        base_z_mm: float,
        cavity_floor_z_mm: float,
        drain_center: tuple[float, float],
        drain_radius_mm: float,
        field_sampler: Callable[[np.ndarray], np.ndarray],
        outer_field_sampler: Callable[[np.ndarray], np.ndarray],
    ) -> tuple[trimesh.Trimesh, OrganicMeshQualityMetrics]:
        contract.validate()
        input_face_count = int(len(mesh.faces))
        input_volume = abs(float(mesh.volume))
        vertices = np.asarray(mesh.vertices, dtype=np.float64).copy()
        faces = np.asarray(mesh.faces, dtype=np.int64).copy()
        for _ in range(contract.subdivision_passes):
            selection_weights, _ = cls._vertex_weights(
                vertices,
                contract,
                opening_center=opening_center,
                opening_radii=opening_radii,
                opening_start_z_mm=opening_start_z_mm,
                base_z_mm=base_z_mm,
                cavity_floor_z_mm=cavity_floor_z_mm,
                drain_center=drain_center,
                drain_radius_mm=drain_radius_mm,
            )
            functional_faces = cls._functional_face_mask(
                vertices,
                faces,
                outer_field_sampler=outer_field_sampler,
                base_z_mm=base_z_mm,
                cavity_floor_z_mm=cavity_floor_z_mm,
                drain_center=drain_center,
                drain_radius_mm=drain_radius_mm,
                protection_mm=contract.drain_protection_mm,
            )
            vertices, faces = cls._subdivide_selected(
                vertices,
                faces,
                (np.max(selection_weights[faces], axis=1) > 0.02)
                | functional_faces,
            )

        reference = vertices.copy()
        vertices, functional_masks = cls._project_functional_geometry(
            vertices,
            outer_field_sampler,
            base_z_mm=base_z_mm,
            cavity_floor_z_mm=cavity_floor_z_mm,
            drain_center=drain_center,
            drain_radius_mm=drain_radius_mm,
            tolerance_mm=contract.drain_protection_mm,
            epsilon_mm=contract.projection_epsilon_mm,
            projection_iterations=contract.projection_iterations,
        )
        reference = vertices.copy()
        adjacency_mesh = trimesh.Trimesh(
            vertices=reference,
            faces=faces,
            process=False,
            validate=False,
        )
        edges = np.asarray(adjacency_mesh.edges_unique, dtype=np.int64)
        if len(edges) == 0:
            raise RuntimeError("Localized mesh refinement requires mesh adjacency.")

        weights, protected = cls._vertex_weights(
            reference,
            contract,
            opening_center=opening_center,
            opening_radii=opening_radii,
            opening_start_z_mm=opening_start_z_mm,
            base_z_mm=base_z_mm,
            cavity_floor_z_mm=cavity_floor_z_mm,
            drain_center=drain_center,
            drain_radius_mm=drain_radius_mm,
        )
        active = weights > 1e-6
        vertices = cls._project_to_surface(
            reference,
            field_sampler,
            weights,
            protected,
            reference,
            contract,
        )
        original = vertices.copy()
        roughness_before = cls._roughness(original, edges, weights)
        original_volume = cls._volume(original, faces)
        if original_volume <= 0.0:
            raise RuntimeError("Localized mesh refinement requires positive mesh volume.")

        vertices = original.copy()
        best_vertices: np.ndarray | None = None
        best_roughness = roughness_before
        best_volume_drift = float("inf")
        best_iteration = 0

        for iteration in range(1, contract.iterations + 1):
            vertices = cls._step(
                vertices,
                edges,
                weights,
                contract.lambda_factor,
                original,
                protected,
                contract.max_displacement_mm,
            )
            vertices = cls._step(
                vertices,
                edges,
                weights,
                contract.mu_factor,
                original,
                protected,
                contract.max_displacement_mm,
            )
            vertices = cls._project_to_surface(
                vertices,
                field_sampler,
                weights,
                protected,
                reference,
                contract,
            )
            roughness = cls._roughness(vertices, edges, weights)
            volume_drift = 100.0 * abs(
                cls._volume(vertices, faces) - original_volume
            ) / original_volume
            if (
                roughness < best_roughness
                and volume_drift <= contract.max_volume_drift_percent
            ):
                best_vertices = vertices.copy()
                best_roughness = roughness
                best_volume_drift = volume_drift
                best_iteration = iteration

        if best_vertices is None:
            raise RuntimeError(
                "Localized mesh refinement found no iteration within quality limits."
            )

        best_vertices, functional_masks = cls._project_functional_geometry(
            best_vertices,
            outer_field_sampler,
            base_z_mm=base_z_mm,
            cavity_floor_z_mm=cavity_floor_z_mm,
            drain_center=drain_center,
            drain_radius_mm=drain_radius_mm,
            tolerance_mm=contract.drain_protection_mm,
            epsilon_mm=contract.projection_epsilon_mm,
            projection_iterations=contract.projection_iterations,
        )
        refined = trimesh.Trimesh(
            vertices=best_vertices,
            faces=faces.copy(),
            process=False,
            validate=False,
        )
        if not refined.is_winding_consistent or refined.volume < 0.0:
            refined.fix_normals(multibody=True)

        displacement = np.linalg.norm(best_vertices - reference, axis=1)
        surface_error = np.abs(field_sampler(best_vertices[active]))
        base_plane = functional_masks["base_plane"]
        base_perimeter = functional_masks["base_perimeter"]
        base_transition = functional_masks["base_transition"]
        drain = functional_masks["drain"]
        drain_distance = np.hypot(
            best_vertices[:, 0] - drain_center[0],
            best_vertices[:, 1] - drain_center[1],
        )
        improvement = 100.0 * (roughness_before - best_roughness) / roughness_before
        total_volume_drift = 100.0 * abs(
            cls._volume(best_vertices, faces) - input_volume
        ) / input_volume
        metrics = OrganicMeshQualityMetrics(
            input_face_count=input_face_count,
            refined_face_count=int(len(faces)),
            active_vertex_count=int(np.count_nonzero(active)),
            protected_vertex_count=int(np.count_nonzero(protected)),
            iterations_applied=best_iteration,
            roughness_before_mm=roughness_before,
            roughness_after_mm=best_roughness,
            roughness_improvement_percent=improvement,
            volume_drift_percent=best_volume_drift,
            total_volume_drift_percent=total_volume_drift,
            maximum_displacement_mm=float(displacement.max(initial=0.0)),
            protected_displacement_mm=float(
                np.abs(best_vertices[protected, 2] - reference[protected, 2]).max(
                    initial=0.0
                )
            ),
            mean_surface_error_mm=float(surface_error.mean()),
            maximum_surface_error_mm=float(surface_error.max(initial=0.0)),
            maximum_base_plane_error_mm=float(
                np.abs(best_vertices[base_plane, 2] - base_z_mm).max(initial=0.0)
            ),
            maximum_base_perimeter_error_mm=float(
                np.abs(outer_field_sampler(best_vertices[base_perimeter])).max(
                    initial=0.0
                )
            ),
            maximum_base_transition_error_mm=float(
                np.abs(outer_field_sampler(best_vertices[base_transition])).max(
                    initial=0.0
                )
            ),
            maximum_drain_radius_error_mm=float(
                np.abs(drain_distance[drain] - drain_radius_mm).max(initial=0.0)
            ),
        )
        metrics.validate(contract)
        return refined, metrics

    @staticmethod
    def _functional_face_mask(
        vertices: np.ndarray,
        faces: np.ndarray,
        *,
        outer_field_sampler: Callable[[np.ndarray], np.ndarray],
        base_z_mm: float,
        cavity_floor_z_mm: float,
        drain_center: tuple[float, float],
        drain_radius_mm: float,
        protection_mm: float,
    ) -> np.ndarray:
        face_z = vertices[faces, 2]
        crosses_base_edge = (
            (face_z.min(axis=1) <= base_z_mm + 1e-6)
            & (face_z.max(axis=1) > base_z_mm + 1e-6)
        )
        radial = np.hypot(
            vertices[:, 0] - drain_center[0],
            vertices[:, 1] - drain_center[1],
        )
        near_drain = (
            np.min(np.abs(radial[faces] - drain_radius_mm), axis=1)
            <= protection_mm
        ) & (face_z.min(axis=1) <= cavity_floor_z_mm + protection_mm)
        outer_error = np.abs(outer_field_sampler(vertices))
        outer_transition_vertex = (
            (vertices[:, 2] <= base_z_mm + 2.0 * protection_mm)
            & (outer_error <= 2.0 * protection_mm)
            & (radial > drain_radius_mm + protection_mm)
        )
        outer_transition = np.any(outer_transition_vertex[faces], axis=1)
        return crosses_base_edge | near_drain | outer_transition

    @classmethod
    def _project_functional_geometry(
        cls,
        vertices: np.ndarray,
        outer_field_sampler: Callable[[np.ndarray], np.ndarray],
        *,
        base_z_mm: float,
        cavity_floor_z_mm: float,
        drain_center: tuple[float, float],
        drain_radius_mm: float,
        tolerance_mm: float,
        epsilon_mm: float,
        projection_iterations: int,
    ) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        projected = vertices.copy()
        radial = np.hypot(
            projected[:, 0] - drain_center[0],
            projected[:, 1] - drain_center[1],
        )
        base_plane = np.abs(projected[:, 2] - base_z_mm) <= 1e-6
        drain = (
            (np.abs(radial - drain_radius_mm) <= tolerance_mm)
            & (projected[:, 2] <= cavity_floor_z_mm + tolerance_mm)
        )
        outer_error = np.abs(outer_field_sampler(projected))
        base_transition = (
            (projected[:, 2] <= base_z_mm + 2.0 * tolerance_mm)
            & ~drain
            & (outer_error <= tolerance_mm)
        )
        base_perimeter = base_plane & base_transition

        projected[base_plane, 2] = base_z_mm
        if np.any(drain):
            direction_x = projected[drain, 0] - drain_center[0]
            direction_y = projected[drain, 1] - drain_center[1]
            length = np.hypot(direction_x, direction_y)
            projected[drain, 0] = (
                drain_center[0] + drain_radius_mm * direction_x / length
            )
            projected[drain, 1] = (
                drain_center[1] + drain_radius_mm * direction_y / length
            )

        if np.any(base_transition):
            indices = np.flatnonzero(base_transition)
            for _ in range(projection_iterations):
                points = projected[indices]
                values = np.asarray(outer_field_sampler(points), dtype=np.float64)
                plus_x = points.copy()
                minus_x = points.copy()
                plus_y = points.copy()
                minus_y = points.copy()
                plus_x[:, 0] += epsilon_mm
                minus_x[:, 0] -= epsilon_mm
                plus_y[:, 1] += epsilon_mm
                minus_y[:, 1] -= epsilon_mm
                gradient = np.column_stack(
                    (
                        (
                            outer_field_sampler(plus_x)
                            - outer_field_sampler(minus_x)
                        )
                        / (2.0 * epsilon_mm),
                        (
                            outer_field_sampler(plus_y)
                            - outer_field_sampler(minus_y)
                        )
                        / (2.0 * epsilon_mm),
                    )
                )
                denominator = np.einsum("ij,ij->i", gradient, gradient)
                correction = np.divide(
                    values[:, None] * gradient,
                    denominator[:, None],
                    out=np.zeros_like(gradient),
                    where=denominator[:, None] > 1e-12,
                )
                projected[indices, :2] -= correction
                projected[indices, 2] = base_z_mm

        return projected, {
            "base_plane": base_plane,
            "base_perimeter": base_perimeter,
            "base_transition": base_transition,
            "drain": drain,
        }

    @staticmethod
    def _project_to_surface(
        vertices: np.ndarray,
        field_sampler: Callable[[np.ndarray], np.ndarray],
        weights: np.ndarray,
        protected: np.ndarray,
        reference: np.ndarray,
        contract: OrganicMeshQualityContract,
    ) -> np.ndarray:
        projected = vertices.copy()
        active = (weights > 1e-6) & ~protected
        epsilon = contract.projection_epsilon_mm
        basis = np.eye(3, dtype=np.float64) * epsilon
        for _ in range(contract.projection_iterations):
            points = projected[active]
            values = np.asarray(field_sampler(points), dtype=np.float64)
            gradient = np.column_stack(
                [
                    (
                        np.asarray(field_sampler(points + axis), dtype=np.float64)
                        - np.asarray(field_sampler(points - axis), dtype=np.float64)
                    )
                    / (2.0 * epsilon)
                    for axis in basis
                ]
            )
            denominator = np.einsum("ij,ij->i", gradient, gradient)
            correction = np.divide(
                values[:, None] * gradient,
                denominator[:, None],
                out=np.zeros_like(gradient),
                where=denominator[:, None] > 1e-12,
            )
            projected[active] -= correction
            displacement = projected - reference
            lengths = np.linalg.norm(displacement, axis=1)
            scale = np.minimum(
                1.0,
                contract.max_displacement_mm / np.maximum(lengths, 1e-12),
            )
            projected = reference + displacement * scale[:, None]
            projected[protected] = reference[protected]
        return projected

    @staticmethod
    def _subdivide_selected(
        vertices: np.ndarray,
        faces: np.ndarray,
        selected_faces: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        if not np.any(selected_faces):
            raise RuntimeError("Localized subdivision selected no rim faces.")

        face_edges = np.stack(
            (
                faces[:, (0, 1)],
                faces[:, (1, 2)],
                faces[:, (2, 0)],
            ),
            axis=1,
        )
        sorted_edges = np.sort(face_edges, axis=2)
        unique_edges, inverse = np.unique(
            sorted_edges.reshape((-1, 2)),
            axis=0,
            return_inverse=True,
        )
        inverse = inverse.reshape((-1, 3))
        marked = np.zeros(len(unique_edges), dtype=bool)
        marked[inverse[selected_faces].reshape(-1)] = True

        marked_ids = np.flatnonzero(marked)
        midpoint_index = np.full(len(unique_edges), -1, dtype=np.int64)
        midpoint_index[marked_ids] = np.arange(
            len(vertices),
            len(vertices) + len(marked_ids),
        )
        midpoints = vertices[unique_edges[marked_ids]].mean(axis=1)
        new_vertices = np.vstack((vertices, midpoints))

        edge_mask = marked[inverse]
        code = (
            edge_mask[:, 0].astype(np.uint8)
            + 2 * edge_mask[:, 1].astype(np.uint8)
            + 4 * edge_mask[:, 2].astype(np.uint8)
        )
        midpoint = midpoint_index[inverse]
        pieces: list[np.ndarray] = []

        unchanged = faces[code == 0]
        if len(unchanged):
            pieces.append(unchanged)

        def append_pattern(value: int, pattern: tuple[tuple[str, str, str], ...]) -> None:
            chosen = code == value
            if not np.any(chosen):
                return
            a, b, c = faces[chosen].T
            mab, mbc, mca = midpoint[chosen].T
            names = {"a": a, "b": b, "c": c, "ab": mab, "bc": mbc, "ca": mca}
            pieces.append(
                np.column_stack(
                    [names[name] for triangle in pattern for name in triangle]
                ).reshape((-1, 3))
            )

        append_pattern(1, (("a", "ab", "c"), ("ab", "b", "c")))
        append_pattern(2, (("b", "bc", "a"), ("bc", "c", "a")))
        append_pattern(4, (("c", "ca", "b"), ("ca", "a", "b")))
        append_pattern(
            3,
            (("b", "bc", "ab"), ("a", "ab", "bc"), ("a", "bc", "c")),
        )
        append_pattern(
            6,
            (("c", "ca", "bc"), ("b", "bc", "ca"), ("b", "ca", "a")),
        )
        append_pattern(
            5,
            (("a", "ab", "ca"), ("c", "ca", "ab"), ("c", "ab", "b")),
        )
        append_pattern(
            7,
            (
                ("a", "ab", "ca"),
                ("ab", "b", "bc"),
                ("ca", "bc", "c"),
                ("ab", "bc", "ca"),
            ),
        )
        return new_vertices, np.vstack(pieces)

    @staticmethod
    def _vertex_weights(
        vertices: np.ndarray,
        contract: OrganicMeshQualityContract,
        *,
        opening_center: tuple[float, float],
        opening_radii: tuple[float, float],
        opening_start_z_mm: float,
        base_z_mm: float,
        cavity_floor_z_mm: float,
        drain_center: tuple[float, float],
        drain_radius_mm: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        x = vertices[:, 0]
        y = vertices[:, 1]
        z = vertices[:, 2]
        rho = np.sqrt(
            ((x - opening_center[0]) / opening_radii[0]) ** 2
            + ((y - opening_center[1]) / opening_radii[1]) ** 2
        )
        axial = np.clip(
            (z - (opening_start_z_mm - contract.rim_axial_band_mm))
            / contract.rim_axial_band_mm,
            0.0,
            1.0,
        )
        radial = np.clip(
            1.0 - np.abs(rho - 1.0) / contract.rim_radial_band,
            0.0,
            1.0,
        )
        weights = axial * axial * (3.0 - 2.0 * axial)
        weights *= radial * radial * (3.0 - 2.0 * radial)

        drain_distance = np.hypot(
            x - drain_center[0],
            y - drain_center[1],
        )
        protected_base = z <= base_z_mm + contract.base_protection_mm
        protected_drain = (
            (drain_distance <= drain_radius_mm + contract.drain_protection_mm)
            & (z <= cavity_floor_z_mm + contract.drain_protection_mm)
        )
        protected = protected_base | protected_drain
        weights[protected] = 0.0
        return weights, protected

    @staticmethod
    def _neighbor_mean(vertices: np.ndarray, edges: np.ndarray) -> np.ndarray:
        totals = np.zeros_like(vertices)
        counts = np.zeros(len(vertices), dtype=np.int64)
        np.add.at(totals, edges[:, 0], vertices[edges[:, 1]])
        np.add.at(totals, edges[:, 1], vertices[edges[:, 0]])
        np.add.at(counts, edges[:, 0], 1)
        np.add.at(counts, edges[:, 1], 1)
        return np.divide(
            totals,
            counts[:, None],
            out=vertices.copy(),
            where=counts[:, None] > 0,
        )

    @classmethod
    def _step(
        cls,
        vertices: np.ndarray,
        edges: np.ndarray,
        weights: np.ndarray,
        factor: float,
        original: np.ndarray,
        protected: np.ndarray,
        max_displacement_mm: float,
    ) -> np.ndarray:
        neighbors = cls._neighbor_mean(vertices, edges)
        candidate = vertices + factor * weights[:, None] * (neighbors - vertices)
        displacement = candidate - original
        lengths = np.linalg.norm(displacement, axis=1)
        scale = np.minimum(1.0, max_displacement_mm / np.maximum(lengths, 1e-12))
        candidate = original + displacement * scale[:, None]
        candidate[protected] = original[protected]
        return candidate

    @classmethod
    def _roughness(
        cls,
        vertices: np.ndarray,
        edges: np.ndarray,
        weights: np.ndarray,
    ) -> float:
        active = weights > 1e-6
        residual = np.linalg.norm(
            vertices - cls._neighbor_mean(vertices, edges),
            axis=1,
        )
        weighted_sum = float(np.sum(residual[active] * weights[active]))
        weight_sum = float(np.sum(weights[active]))
        if weight_sum <= 0.0:
            raise RuntimeError("Localized roughness measurement has no active weight.")
        return weighted_sum / weight_sum

    @staticmethod
    def _volume(vertices: np.ndarray, faces: np.ndarray) -> float:
        triangles = vertices[faces]
        signed = np.einsum(
            "ij,ij->i",
            np.cross(triangles[:, 0], triangles[:, 1]),
            triangles[:, 2],
        )
        return abs(float(np.sum(signed) / 6.0))
