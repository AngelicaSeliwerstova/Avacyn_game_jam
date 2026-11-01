"""The lost-property cabinet, pendant and final meeting at the foot of the stair."""
from pathlib import Path
from dataclasses import replace

from engine.scene.box import Box
from engine.scene.entity import Entity
from engine.scene.model import ModelComponent
from engine.scene.object import ObjectState, SceneObject
from engine.scene.transform import Transform
from game.levels.story_props import build_story_prop

BODY_POSITION = (-12.1, 0.02, 9.65)
HELP_PLAYER = (-11.0, 0.0, 10.6)
HELP_DOCTOR = (-11.0, 0.0, 9.1)


def pendant_boxes(position):
    x, y, z = position
    gold = (0.83, 0.65, 0.24)
    return tuple(Box((x + dx, y, z + dz), size, color=gold, emission=(0.10, 0.07, 0.01))
                 for dx, dz, size in ((0, 0, (0.10, 0.025, 0.13)),
                                      (-0.07, -0.09, (0.025, 0.018, 0.16)),
                                      (0.07, -0.09, (0.025, 0.018, 0.16)),
                                      (0, -0.18, (0.14, 0.018, 0.025))))


def build_final_props():
    cabinet = build_story_prop({"id": "security_lost_items", "name": "Шкаф потерянных вещей",
        "action": "Осмотреть найденные вещи", "size": (0.9, 1.65, 0.42),
        "color": (0.32, 0.36, 0.31)}, (-4.6, 0.85, 6.8))
    # The body is a baked, unanimated copy of the user's friend.glb.
    source = Path(__file__).resolve().parents[2] / "resources/models/props/friend_rest.glb"
    body = SceneObject("friend_body", {"default": ObjectState((
        Box((-12.1, 0.20, 9.65), (1.7, 0.38, 0.65)),), collidable=False),
        "hidden": ObjectState()}, initial="hidden",
        entity=Entity("friend_body", Transform(position=BODY_POSITION), ModelComponent(source)), static_shadows=False)
    pendant = SceneObject("fallen_pendant", {"default": ObjectState(
        pendant_boxes((-11.58, 0.035, 10.02)), collidable=False), "hidden": ObjectState()}, initial="hidden")
    hand = build_story_prop({"id": "doctor_help", "name": "Протянутая рука доктора",
        "action": "Принять помощь", "size": (0.08, 0.07, 0.12),
        "selection_size": (0.7, 0.7, 0.65), "color": (0.78, 0.66, 0.57), "initial": "hidden"},
        (-11.1, 1.15, 9.75))
    hand = SceneObject("doctor_help", {"default": replace(hand.states["default"], boxes=()),
                                       "hidden": ObjectState()}, entity=hand.entity, initial="hidden")
    return cabinet, body, pendant, hand
