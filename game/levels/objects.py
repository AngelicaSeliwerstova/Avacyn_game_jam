from dataclasses import replace
import math

from engine.scene.box import Box
from engine.scene.interaction import Interaction
from engine.scene.object import ObjectState, SceneObject


def build_objects(definitions, layout) -> tuple[SceneObject, ...]:
    """Игровые заготовки двери и ключа из данных карты, без привязки к координатам."""
    objects = []
    for data in definitions:
        node = tuple(data["node"])
        if not layout.is_open(node):
            raise ValueError(f"Object must be in an open maze cell: {node}")
        offset = data.get("offset", (0, 0, 0))
        if len(offset) != 3 or any(not math.isfinite(v) for v in offset):
            raise ValueError("Object offset needs three finite coordinates")
        position = tuple(p + o for p, o in zip(layout.position(node), offset))
        if data["type"] == "key":
            objects.extend(_key(data, position))
        elif data["type"] == "door":
            objects.extend(_door(data, position, layout))
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
    frame = tuple(box(sign * (width + side) / 2, layout.wall_height / 2, 0,
                      side, layout.wall_height, thickness + 0.1, "concrete") for sign in (-1, 1))
    frame += (box(0, (height + layout.wall_height) / 2, 0,
                  width, layout.wall_height - height, thickness + 0.1, "concrete"),)
    panel = (box(0, height / 2, 0, width - 0.04, height - 0.04, thickness),)
    # Ручки с обеих сторон видны независимо от стороны подхода.
    panel += tuple(box(width * 0.3, 1.05, sign * (thickness / 2 + 0.04),
                       0.22, 0.055, 0.08, "wood") for sign in (-1, 1))
    shift = layout.cell_size
    opened = tuple(replace(b, position=(b.position[0] + (shift if axis == "x" else 0),
                                       b.position[1], b.position[2] + (shift if axis == "z" else 0)))
                   for b in panel)
    action = Interaction(data.get("name", "Locked door"), "Unlocked. The door slides aside.",
                         "Open", "unlock_door", key_id)
    return (
        SceneObject(data["id"] + "_frame", {"default": ObjectState(frame)}),
        SceneObject(data["id"], {"default": ObjectState(panel, interaction=action),
                                 "open": ObjectState(opened, collidable=False)}),
    )
