"""Physical story documents use the same visibility and reach rules as doors."""

from dataclasses import dataclass

from engine.scene.box import Box
from engine.scene.entity import Entity
from engine.scene.interaction import Interaction
from engine.scene.object import ObjectState, SceneObject


@dataclass
class StoryProp(Entity):
    requested: bool = False
    animated_states: tuple[str, ...] = ()
    animation_seconds: float = 0.12


@dataclass
class StoryDocument(StoryProp):
    pass


def build_story_prop(data, position):
    action = Interaction(data["name"], data["name"], data.get("action", "Осмотреть"), "story", data["id"])
    states = {}
    for name, material in data.get("materials", {"default": data.get("material")}).items():
        box = Box(position, tuple(data["size"]), material=material,
                  color=tuple(data["color"]) if "color" in data else None,
                  local_texture=True, emission=tuple(data.get("emission", (0, 0, 0))),
                  yaw_degrees=data.get("yaw", 0))
        states[name] = ObjectState((box,), collidable=False, interaction=action, selection_box=box)
    return SceneObject(data["id"], states, static_shadows=not bool(data.get("animated_states")), entity=StoryProp(name=data["id"],
        animated_states=tuple(data.get("animated_states", ())), animation_seconds=data.get("animation_seconds", 0.12)))


class StoryPropSystem:
    def __init__(self, level):
        self._time = 0.0
        self._objects = tuple(obj for obj in level.objects if isinstance(obj.entity, StoryProp)
                              and obj.entity.animated_states)

    def update(self, delta_time):
        self._time += delta_time
        for obj in self._objects:
            if obj.state_name in obj.entity.animated_states:
                frames = obj.entity.animated_states
                state = frames[int(self._time / obj.entity.animation_seconds) % len(frames)]
                if state != obj.state_name:
                    obj.set_state(state)


def build_story_document(data, position):
    """Placement belongs to level data; contents and progression belong to the act."""
    size = tuple(data["size"])
    style = data.get("style", "paper")
    if style not in ("paper", "board"):
        raise ValueError(f"Unknown story document style: {style}")
    face = Box(position, size, material="wood", color=(0.84, 0.79, 0.66))
    boxes = (face,)
    if style == "board":
        x, y, z = position
        boxes += tuple(Box((x + dx * size[0], y + dy * size[1], z + size[2] / 2 + 0.007),
                           (width * size[0], height * size[1], 0.012), color=(0.2, 0.32, 0.29))
                       for dx, dy, width, height in ((0, 0, 0.84, 0.02), (-0.26, 0, 0.013, 0.78),
                           (0.26, 0, 0.013, 0.78), (0, 0.26, 0.84, 0.02), (0, -0.26, 0.84, 0.02)))
    title, name = data["name"], data["id"]
    selection = Box(position, tuple(data.get("selection_size", size)))
    return SceneObject(name, {"default": ObjectState(boxes, collidable=False,
        interaction=Interaction(title, title, "Изучить", "story", name), selection_box=selection),
        "unavailable": ObjectState(boxes, collidable=False)}, initial=data.get("initial", "default"),
        entity=StoryDocument(name=name))
