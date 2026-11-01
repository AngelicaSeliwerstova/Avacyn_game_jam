"""Authored pumpkin decorations shared by both versions of the hospital."""

from pathlib import Path

from engine.scene.box import Box
from engine.scene.entity import Entity
from engine.scene.model import ModelComponent
from engine.scene.object import ObjectState, SceneObject
from engine.scene.transform import Transform


MODEL_PATH = Path(__file__).resolve().parents[2] / "resources/models/props/pumpkin.glb"

# Name, X, Z, diameter in metres, facing. Keep doorways and the stair clear.
GROUND_PUMPKINS = (
    ("waiting_west", -19.0, 12.65, 0.60, 30),
    ("waiting_west_small", -19.55, 11.95, 0.38, -15),
    ("waiting_east", 19.8, 12.7, 0.55, -25),
    ("office_corridor_west", -12.5, -2.65, 0.55, 160),
    ("office_corridor_east", 19.7, -5.2, 0.60, 25),
    ("reception", 18.8, 6.0, 0.50, -70),
    ("security", -1.05, 7.1, 0.42, 45),
)
SURGERY_PUMPKINS = (
    ("corridor_west", -28.9, -8.8, 0.65, 145),
    ("preop_corner", -20.7, -9.2, 0.48, 20),
    ("operating_corridor", -5.3, -9.2, 0.58, -20),
    ("pharmacy_corridor", 18.4, -9.2, 0.52, 25),
    ("corridor_east", 28.8, -8.8, 0.62, -35),
    ("nurses", -4.2, -1.2, 0.45, 55),
    ("waiting", -28.9, 15.5, 0.58, 100),
    ("staff_room", 12.7, 22.7, 0.55, -40),
    ("electrical_room", 28.7, 22.7, 0.48, -80),
)


def build_hospital_pumpkins(floor_heights):
    objects = []
    for floor, placements in enumerate((GROUND_PUMPKINS, SURGERY_PUMPKINS)):
        if floor >= len(floor_heights):
            break
        y = floor_heights[floor]
        for name, x, z, diameter, yaw in placements:
            object_id = f"f{floor + 1}_pumpkin_{name}"
            transform = Transform(position=(x, y, z), rotation=(0, yaw, 0),
                                  scale=(diameter,) * 3)
            entity = Entity(object_id, transform, ModelComponent(MODEL_PATH))
            bounds = Box((x, y + diameter * 0.4, z), (diameter, diameter * 0.8, diameter))
            objects.append(SceneObject(object_id, {"default": ObjectState((bounds,))},
                                       entity=entity, static_shadows=False))
    return tuple(objects)
