"""Whole-object Creator presets built from the game's furniture builders."""

from dataclasses import dataclass, replace
from functools import lru_cache
import uuid

import glm

from engine.scene.box import Box
from game.levels.hospital_props import HospitalProps
from game.levels.hospital_finishes import hospital_palette, MATERIAL_ROLES
from game.levels import furniture
from game.levels.vegetation import dead_tree


@dataclass(frozen=True)
class CreatorPreset:
    name: str
    boxes: tuple[Box, ...]


@lru_cache(maxsize=2)
def creator_presets(peaceful=False):
    palette = hospital_palette(peaceful)
    result = [CreatorPreset("Блок", (Box((0, 0.3, 0), (0.6, 0.6, 0.6), material="concrete"),))]

    def add(name, method, **options):
        props = HospitalProps()
        getattr(props, method)(0, 0, **options)
        result.append(CreatorPreset(name, tuple(props.boxes + props.decorations)))

    for name, method, options in (
        ("Диван", "sofa", {}), ("Диван широкий", "sofa", {"width": 3.6}),
        ("Стул", "chair", {}), ("Стол", "table", {}),
        ("Стол рабочий", "table", {"width": 2.2, "height": 0.98}),
        ("Столик прикроватный", "table", {"width": 0.45, "depth": 0.45, "height": 0.72}),
        ("Шкаф медицинский", "cabinet", {}),
        ("Шкаф деревянный", "cabinet", {"medical": False}),
        ("Тумбочка", "cabinet", {"width": 0.45, "height": 0.65}),
        ("Тележка", "cart", {}), ("Стеллаж с бельём", "linen_shelf", {}),
        ("Раковина", "sink", {}), ("Радиатор", "radiator", {}),
        ("Ширма", "privacy_screen", {}), ("Ширма широкая", "privacy_screen", {"width": 2.2}),
        ("Капельница", "iv_stand", {}), ("Монитор медицинский", "monitor", {}),
        ("Растение", "plant", {}), ("Растение маленькое", "plant", {"small": True}),
        ("Предметы на столе", "desk_details", {}),
        ("Табличка", "sign", {"text": "Палата"}),
    ):
        add(name, method, **options)
    for name, builder in (("Кровать", furniture.bed), ("Операционный стол с лампой", furniture.operating_table)):
        props, boxes = HospitalProps(), []
        builder(boxes, props, 0, 0)
        result.append(CreatorPreset(name, tuple(boxes + props.boxes + props.decorations)))

    # Include the distinctive assemblies authored directly in the level scripts.
    result.extend((
        CreatorPreset("Кровать первого этажа", (
            Box((0, 0.45, 0), (1.2, 0.22, 2.2), material="medical_enamel"),
            Box((0, 0.66, 0), (1.14, 0.2, 2.05), material="bed_linen"),
            Box((0, 0.82, -0.7), (0.85, 0.12, 0.48), material="bed_linen"),
            *(Box((side * 0.5, 0.25, 0), (0.07, 0.5, 1.85), material="rust") for side in (-1, 1)),
            Box((0, 0.72, -1.05), (1.2, 0.85, 0.06), material="medical_enamel"),
        )),
        CreatorPreset("Лампа смотровая", (
            Box((-1.5, 0.06, -0.3), (0.65, 0.08, 0.5), material="rust"),
            Box((-1.5, 1.2, -0.3), (0.06, 2.3, 0.06), material="rust"),
            Box((-0.8, 2.3, -0.3), (1.4, 0.055, 0.055), material="rust"),
            Box((-0.1, 2.25, -0.3), (0.6, 0.1, 0.55), material="rust"),
        )),
        CreatorPreset("Письменный стол", (
            Box((0, 0.91, 0), (2.4, 0.14, 0.9), material="wood"),
            *(Box((side * 0.93, 0.43, 0), (0.4, 0.86, 0.765), material="plaster") for side in (-1, 1)),
        )),
        CreatorPreset("Пост медсестры — стойка", (
            Box((-2.0, 0.75, 0), (0.45, 1.5, 5.2), material="wood"),
            Box((0.2, 0.75, 2.35), (4.85, 1.5, 0.45), material="wood"),
            Box((-1.85, 1.55, 0), (0.6, 0.12, 5.35), material="wood"),
            Box((0.2, 1.55, 2.05), (4.95, 0.12, 0.6), material="wood"),
        )),
        CreatorPreset("Электрический шкаф", (
            Box((0, 1.45, 0), (1.25, 2.45, 0.28), material="rust", color=(0.34, 0.37, 0.32)),
            Box((0, 1.55, -0.18), (0.82, 1.58, 0.06), material="rust", color=(0.48, 0.49, 0.39)),
            Box((0, 1.65, -0.23), (0.12, 0.12, 0.035), material="rust", emission=(0.42, 0.29, 0.12)),
        )),
        CreatorPreset("Ящик", (Box((0, 0.36, 0), (0.75, 0.72, 0.75), material="wood", color=(0.37, 0.31, 0.2)),)),
        CreatorPreset("Потолочный светильник", (
            Box((0, 0.08, 0), (1.5, 0.08, 0.36), material="rust"),
            Box((0, 0.03, 0), (1.24, 0.025, 0.2), emission=(0.35, 0.54, 0.43)),
        )),
    ))
    props = HospitalProps()
    props.bed_details(0, 0, mattress_top=0.76)
    index = next(i for i, p in enumerate(result) if p.name == "Кровать первого этажа")
    result[index] = CreatorPreset(result[index].name, result[index].boxes + tuple(props.boxes + props.decorations))
    reception = []
    for position, size, yaw in (
        ((0, 0.7375, 0), (9.6, 1.475, 0.6), 0),
        ((-5.5, 0.7375, -0.85), (0.6, 1.475, 2.4), 35),
        ((-6.1, 0.7375, -2.8), (0.6, 1.475, 2.2), 0),
        ((5.5, 0.7375, -0.85), (0.6, 1.475, 2.4), -35),
        ((6.2, 0.7375, -2.3), (0.6, 1.475, 0.9), 0),
    ):
        reception.append(Box(position, size, material="wood", yaw_degrees=yaw))
        reception.append(Box((position[0], 1.5, position[2]),
                             (size[0] + 0.12, 0.12, size[2] + 0.12), material="wood", yaw_degrees=yaw))
    props = HospitalProps()
    for x in (-2.4, 2):
        props.desk_details(x, 0, height=1.56)
    result.append(CreatorPreset("Стойка регистрации", tuple(reception + props.boxes + props.decorations)))
    result.extend((CreatorPreset("Иссохшее дерево", dead_tree()),
                   CreatorPreset("Иссохшее деревце", dead_tree(2.6)),
                   CreatorPreset("Сломанный сухой ствол", dead_tree(1.6, broken=True))))
    return tuple(CreatorPreset(p.name, tuple(replace(
        b, material=palette.get(b.material, b.material),
        color=None if b.material in MATERIAL_ROLES else b.color,
    ) for b in p.boxes)) for p in result)


def place_preset(preset, position, normal=(0, 1, 0)):
    """Place the entire assembly outside the aimed surface, not through it."""
    normal = glm.normalize(glm.vec3(normal))
    center = glm.vec3(position)
    support = min(glm.dot(glm.vec3(b.position), normal) - sum(
        abs(normal[i]) * b.bounds_half_size[i] for i in range(3)) for b in preset.boxes)
    offset = center - normal * support + normal * (0.0 if abs(normal.y) > 0.99 else 0.01)
    group = uuid.uuid4().hex
    # The common center stays fixed when any component is selected for rotation.
    low = [min(b.position[i] - b.bounds_half_size[i] for b in preset.boxes) for i in range(3)]
    high = [max(b.position[i] + b.bounds_half_size[i] for b in preset.boxes) for i in range(3)]
    pivot = tuple(offset[i] + (low[i] + high[i]) / 2 for i in range(3))
    return tuple(replace(b, position=tuple(glm.vec3(b.position) + offset),
                         authored_group=None, creator_group=group, creator_pivot=pivot) for b in preset.boxes)


def rotate_group(objects, index, axis, degrees):
    selected = objects[index]
    pivot = glm.vec3(selected.creator_pivot or selected.position)
    rotation = glm.angleAxis(glm.radians(degrees), glm.vec3(axis))
    if tuple(axis) == (0, 1, 0) and all(
        b.orientation == (1.0, 0.0, 0.0, 0.0) for b in objects
        if b is selected or (selected.creator_group and b.creator_group == selected.creator_group)
    ):
        return tuple(b.rotated_around(tuple(pivot), degrees)
                     if i == index or (selected.creator_group and b.creator_group == selected.creator_group)
                     else b for i, b in enumerate(objects))
    return tuple(replace(b, position=tuple(pivot + rotation * (glm.vec3(b.position) - pivot)),
                         orientation=tuple(glm.normalize(rotation * glm.quat(*b.orientation))))
                 if i == index or (selected.creator_group and b.creator_group == selected.creator_group)
                 else b for i, b in enumerate(objects))


def remove_group(objects, index):
    group = objects[index].creator_group
    return tuple(b for i, b in enumerate(objects) if i != index and not (group and b.creator_group == group))
