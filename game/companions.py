import math

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.debug.geometry import DebugPath
from engine.scene.box import Box
from engine.scene.object import ObjectState, SceneObject
from game.entities.companion import Companion


class CompanionSystem:
    def __init__(self, level, player):
        self.player = player
        self._authored_level = level
        self._removed_groups = frozenset(level.removed_object_groups)
        self.companions = tuple(obj.entity for obj in level.objects if isinstance(obj.entity, Companion))
        self._creator_boxes = level.creator_objects
        self._creator_obstacle = SceneObject("companion_creator_collision", {
            "default": ObjectState(self._creator_boxes)})
        self._player_obstacle = SceneObject("companion_player_collision", {
            "default": ObjectState((self._player_box(),))})
        for ally in self.companions:
            world = CollisionWorld3D((b.collider for b in level.collision_boxes),
                                     level.floor_bounds, level.base_height,
                                     objects=tuple(o for o in level.objects if o is not ally.scene_object)
                                     + (self._player_obstacle,))
            world.set_creator_colliders(self._creator_boxes)
            ally.bind(world, level, (self._creator_obstacle,))
        for obj in level.objects:
            if obj.rotation_pivot is not None:
                previous = obj.motion_guard
                obj.motion_guard = lambda state, guard=previous: (
                    (guard is None or guard(state)) and self._clear_of_companions(state))

    def _player_box(self):
        body = self.player.body
        x, y, z = body.position
        return Box((x, y + body.height / 2, z), (body.radius * 2, body.height, body.radius * 2))

    def _clear_of_companions(self, state):
        return not state.collidable or all(
            not (b.collider.bottom < ally.body.position.y + ally.body.height - 1e-5
                 and b.collider.top > ally.body.position.y + 1e-5
                 and b.footprint.intersects_circle(ally.body.position.x, ally.body.position.z, ally.body.radius))
            for ally in self.companions for b in state.boxes)

    def update(self, delta_time):
        removed = frozenset(self._authored_level.removed_object_groups)
        if removed != self._removed_groups:
            self._removed_groups = removed
            colliders = tuple(b.collider for b in self._authored_level.collision_boxes)
            for ally in self.companions:
                ally.body.world.set_static_colliders(colliders)
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Companion delta time must be finite and nonnegative")
        self._player_obstacle.set_geometry((self._player_box(),))
        boxes = getattr(self.player, "creator_object_boxes", ())
        if boxes != self._creator_boxes:
            self._creator_boxes = boxes
            self._creator_obstacle.set_geometry(boxes)
            for ally in self.companions:
                ally.body.world.set_creator_colliders(self._creator_boxes)
        target = self.player.body.position
        if not self.player.body.grounded:
            target.y = self.player.body.world.support_height(target, self.player.body.radius, target.y)
        for ally in self.companions:
            ally.update(min(delta_time, settings.MAX_DELTA_TIME), target,
                        target_speed=self.player.body.horizontal_speed)

    def debug_paths(self):
        return tuple(DebugPath((tuple(ally.body.position), *ally.remaining_path))
                     for ally in self.companions if ally.remaining_path)
