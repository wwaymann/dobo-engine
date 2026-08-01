import math
from dataclasses import dataclass

import cadquery as cq

Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class SurfacePlacement:
    """
    Describe una posición y orientación local
    sobre la superficie exterior del modelo.
    """

    point: Vector3
    normal: Vector3
    tangent: Vector3
    vertical: Vector3


def normalize_vector(vector: Vector3) -> Vector3:
    """
    Devuelve un vector de longitud 1.
    """

    length = math.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)

    if length <= 0:
        raise ValueError("Cannot normalize a zero-length vector.")

    return (
        vector[0] / length,
        vector[1] / length,
        vector[2] / length,
    )


def get_radius_at_z(
    config: dict,
    position_z: float,
) -> float:
    """
    Calcula el radio exterior de un cilindro
    o tronco de cono en una altura determinada.
    """

    height = float(config["height"])

    if height <= 0:
        raise ValueError("Model height must be greater than 0.")

    bottom_radius = float(config["bottom_diameter"]) / 2

    top_radius = float(config["top_diameter"]) / 2

    return bottom_radius + (top_radius - bottom_radius) * (position_z / height)


def get_radius_slope(
    config: dict,
) -> float:
    """
    Calcula la variación del radio respecto
    de la altura.

    Cilindro:
        pendiente = 0

    Cuerpo que se ensancha hacia arriba:
        pendiente > 0
    """

    height = float(config["height"])

    if height <= 0:
        raise ValueError("Model height must be greater than 0.")

    bottom_radius = float(config["bottom_diameter"]) / 2

    top_radius = float(config["top_diameter"]) / 2

    return (top_radius - bottom_radius) / height


def arc_length_to_angle_radians(
    arc_length: float,
    radius: float,
) -> float:
    """
    Convierte una longitud sobre una circunferencia
    en un ángulo expresado en radianes.
    """

    if radius <= 0:
        raise ValueError("Radius must be greater than 0.")

    return arc_length / radius


def arc_length_to_angle_degrees(
    arc_length: float,
    radius: float,
) -> float:
    """
    Convierte una longitud sobre una circunferencia
    en un ángulo expresado en grados.
    """

    angle_radians = arc_length_to_angle_radians(
        arc_length=arc_length,
        radius=radius,
    )

    return math.degrees(angle_radians)


def get_radial_direction(
    angle_degrees: float,
) -> Vector3:
    """
    Devuelve el vector radial horizontal
    correspondiente a un ángulo.

    Convención DOBO:

    0 grados   = frente
    90 grados  = lado derecho
    180 grados = parte trasera
    -90 grados = lado izquierdo
    """

    angle_radians = math.radians(angle_degrees)

    return (
        math.sin(angle_radians),
        math.cos(angle_radians),
        0.0,
    )


def get_surface_tangent(
    radial: Vector3,
) -> Vector3:
    """
    Devuelve la dirección horizontal tangente
    a la superficie.
    """

    return normalize_vector(
        (
            -radial[1],
            radial[0],
            0.0,
        )
    )


def get_surface_orientation(
    config: dict,
    radial: Vector3,
) -> tuple[
    Vector3,
    Vector3,
    Vector3,
]:
    """
    Calcula la orientación local de una superficie
    cilíndrica o cónica.

    Devuelve:

    - normal exterior;
    - tangente horizontal;
    - dirección vertical inclinada.
    """

    slope = get_radius_slope(
        config=config,
    )

    radial_normalized = normalize_vector(radial)

    normal = normalize_vector(
        (
            radial_normalized[0],
            radial_normalized[1],
            -slope,
        )
    )

    tangent = get_surface_tangent(
        radial=radial_normalized,
    )

    vertical = normalize_vector(
        (
            radial_normalized[0] * slope,
            radial_normalized[1] * slope,
            1.0,
        )
    )

    return (
        normal,
        tangent,
        vertical,
    )


def get_surface_point(
    config: dict,
    position_z: float,
    angle_degrees: float,
) -> Vector3:
    """
    Calcula un punto sobre la superficie exterior.
    """

    radius = get_radius_at_z(
        config=config,
        position_z=position_z,
    )

    if radius <= 0:
        raise ValueError("Surface radius must be greater than 0.")

    radial = get_radial_direction(
        angle_degrees=angle_degrees,
    )

    return (
        radius * radial[0],
        radius * radial[1],
        position_z,
    )


def get_surface_placement(
    config: dict,
    position_z: float,
    angle_degrees: float,
) -> SurfacePlacement:
    """
    Obtiene la posición y orientación completas
    sobre una superficie cilíndrica o cónica.
    """

    point = get_surface_point(
        config=config,
        position_z=position_z,
        angle_degrees=angle_degrees,
    )

    radial = get_radial_direction(
        angle_degrees=angle_degrees,
    )

    (
        normal,
        tangent,
        vertical,
    ) = get_surface_orientation(
        config=config,
        radial=radial,
    )

    return SurfacePlacement(
        point=point,
        normal=normal,
        tangent=tangent,
        vertical=vertical,
    )


def offset_point(
    point: Vector3,
    direction: Vector3,
    distance: float,
) -> Vector3:
    """
    Desplaza un punto en una dirección determinada.
    """

    return (
        point[0] + direction[0] * distance,
        point[1] + direction[1] * distance,
        point[2] + direction[2] * distance,
    )


def rotate_axis_on_surface(
    tangent: Vector3,
    vertical: Vector3,
    rotation_degrees: float,
) -> Vector3:
    """
    Rota el eje horizontal dentro del plano
    tangente de la superficie.

    Se utiliza para texto o decoraciones diagonales.
    """

    angle_radians = math.radians(rotation_degrees)

    cosine = math.cos(angle_radians)

    sine = math.sin(angle_radians)

    rotated_axis = (
        tangent[0] * cosine + vertical[0] * sine,
        tangent[1] * cosine + vertical[1] * sine,
        tangent[2] * cosine + vertical[2] * sine,
    )

    return normalize_vector(rotated_axis)


def create_surface_plane(
    config: dict,
    position_z: float,
    angle_degrees: float,
    overlap: float = 0.0,
    outward: bool = False,
    rotation_degrees: float = 0.0,
) -> cq.Plane:
    """
    Crea un plano local adaptado a la superficie.

    Parámetros:

    overlap:
        distancia de penetración o separación.

    outward=False:
        desplaza el plano hacia dentro del modelo.

    outward=True:
        desplaza el plano hacia fuera.

    rotation_degrees:
        inclinación dentro del plano tangente.
    """

    placement = get_surface_placement(
        config=config,
        position_z=position_z,
        angle_degrees=angle_degrees,
    )

    direction_multiplier = 1.0 if outward else -1.0

    origin = offset_point(
        point=placement.point,
        direction=placement.normal,
        distance=(overlap * direction_multiplier),
    )

    x_axis = rotate_axis_on_surface(
        tangent=placement.tangent,
        vertical=placement.vertical,
        rotation_degrees=rotation_degrees,
    )

    return cq.Plane(
        origin=origin,
        xDir=x_axis,
        normal=placement.normal,
    )
