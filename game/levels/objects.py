from dataclasses import replace
import math

from config import settings

from engine.scene.box import Box
from engine.scene.interaction import Interaction
from engine.scene.object import ObjectState, SceneObject
from game.entities.enemy import Enemy, EnemySettings


def build_objects(definitions, layout) -> tuple[SceneObject, ...]:
    """Объекты и сущности из карты."""
    objects = []
    for data in definitions:
        if data["type"] == "enemy" and not settings.ENEMIES_ENABLED:
            continue
        if "node" in data:
            node = tuple(data["node"])
            if not layout.is_open(node):
                raise ValueError(f"Object must be in an open maze cell: {node}")
            base_position = layout.position(node)
        else:
            base_position = tuple(data["position"])
            if len(base_position) != 3 or not all(math.isfinite(v) for v in base_position):
                raise ValueError("Object position needs three finite coordinates")
        offset = data.get("offset", (0, 0, 0))
        if len(offset) != 3 or any(not math.isfinite(v) for v in offset):
            raise ValueError("Object offset needs three finite coordinates")
        position = tuple(p + o for p, o in zip(base_position, offset))
        if data["type"] == "key":
            objects.extend(_key(data, position))
        elif data["type"] == "door":
            objects.extend(_door(data, position, layout))
        elif data["type"] == "enemy":
            enemy = Enemy(data["id"], position,
                          tuning=EnemySettings(**data.get("settings", {})))
            objects.append(enemy.scene_object)
        else:
            raise ValueError(f"Unknown map object type: {data['type']}")
    return tuple(objects)


def _key(data, position):
    x, y, z = position
    name = data.get("name", "Key")
    key_id = data["key_id"]
    if not isinstance(key_id, str) or not key_id.strip():
        raise ValueError("Key ID must not be empty")
    pedestal = Box((x, y + 0.4, z), (0.65, 0.8, 0.65), material="wood")
    # Кольцо, стержень и два зубца - временная модель без внешнего файла.
    parts = (
        ((-0.16, 1.02, 0), (0.16, 0.04, 0.05)),
        ((-0.16, 0.88, 0), (0.16, 0.04, 0.05)),
        ((-0.24, 0.95, 0), (0.04, 0.14, 0.05)),
        ((-0.08, 0.95, 0), (0.04, 0.14, 0.05)),
        ((0.09, 0.95, 0), (0.34, 0.045, 0.05)),
        ((0.16, 0.9, 0), (0.04, 0.1, 0.05)),
        ((0.25, 0.9, 0), (0.04, 0.1, 0.05)),
    )
    boxes = tuple(Box((x + dx, y + dy, z + dz), size, material="rust", emission=(0.6, 0.36, 0.04))
                  for (dx, dy, dz), size in parts)
    # Единственный объём выбора вместо необходимости попасть в маленький зубец ключа.
    # Геометрия остаётся настоящей: доступ перекрывают стол и стены.
    action = Interaction(name, f"Picked up: {name}.", "Take", "pickup_key", key_id)
    return (
        SceneObject(data["id"] + "_pedestal", {"default": ObjectState((pedestal,))}),
        SceneObject(data["id"], {
            "default": ObjectState(boxes, collidable=False, interaction=action,
                                   selection_box=Box((x, y + 0.95, z), (0.56, 0.22, 0.16))),
            "collected": ObjectState(),
        }),
    )


def _door(data, position, layout):
    width = data.get("width", 1.8)
    height = data.get("height", 2.35)
    thickness = data.get("thickness", 0.18)
    if (any(not math.isfinite(v) or v <= 0 for v in (width, height, thickness))
            or width >= layout.cell_size or height >= layout.wall_height):
        raise ValueError("Door must fit inside its maze cell")
    axis = data.get("axis", "x")  # Ось ширины; другая горизонтальная ось - толщина.
    if axis not in ("x", "z"):
        raise ValueError("Door width axis must be x or z")
    key_id = data["key_id"]
    if not isinstance(key_id, str) or not key_id.strip():
        raise ValueError("Door key ID must not be empty")
    x, y, z = position

    def box(u, v, n, w, h, d, material="rust"):
        point = (x + u, y + v, z + n) if axis == "x" else (x + n, y + v, z + u)
        size = (w, h, d) if axis == "x" else (d, h, w)
        return Box(point, size, material=material)

    side = (layout.cell_size - width) / 2
    overlap = 0.02  # Торцы рамы уходят в стену, без совпадающих видимых плоскостей.
    frame = tuple(box(sign * (width + side + overlap) / 2, layout.wall_height / 2, 0,
                      side + overlap, layout.wall_height + 2 * overlap, thickness + 0.1, "concrete")
                  for sign in (-1, 1))
    frame += (box(0, (height + layout.wall_height + overlap) / 2, 0,
                  width, layout.wall_height - height + overlap, thickness + 0.1, "concrete"),)
    panel = (box(0, height / 2, 0, width - 0.04, height - 0.04, thickness),)
    # Ручки с обеих сторон видны независимо от стороны подхода.
    panel += tuple(box(width * 0.3, 1.05, sign * (thickness / 2 + 0.04),
                       0.22, 0.055, 0.08, "wood") for sign in (-1, 1))
    panel = tuple(replace(b, local_texture=True) for b in panel)
    hinge_side = data.get("hinge_side", "left")
    if hinge_side not in ("left", "right"):
        raise ValueError("Door hinge_side must be left or right")
    sign = -1 if hinge_side == "left" else 1
    default_angle = (90 if axis == "x" else -90) * -sign
    angle = data.get("open_angle", default_angle)
    if not math.isfinite(angle) or not 10 <= abs(angle) <= 110:
        raise ValueError("Door open_angle must be between 10 and 110 degrees in magnitude")
    # Ось петли вынесена за лицевую плоскость рамы: полотно не врезается в косяк.
    normal_offset = -(thickness + 0.1) / 2 - 0.02
    if angle * default_angle < 0:
        normal_offset = -normal_offset
    u = sign * width / 2
    pivot = (x + u, y, z + normal_offset) if axis == "x" else (x + normal_offset, y, z + u)
    opened = tuple(b.rotated_around(pivot, angle) for b in panel)
    action = Interaction(data.get("name", "Locked door"), "Unlocked. The door opens.",
                         "Open", "unlock_door", key_id)
    return (
        SceneObject(data["id"] + "_frame", {"default": ObjectState(frame)}),
        SceneObject(data["id"], {"default": ObjectState(panel, interaction=action),
                                 "open": ObjectState(opened)},
                    transition_seconds={"open": data.get("open_seconds", 0.9)}, rotation_pivot=pivot),
    )
