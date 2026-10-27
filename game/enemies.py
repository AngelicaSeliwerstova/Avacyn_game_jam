import math

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.scene.box import Box
from engine.scene.object import ObjectState, SceneObject
from game.entities.enemy import Enemy, EnemyState


class EnemySystem:
    """Связывает врагов, игрока и двери; движок знает только метод update."""

    def __init__(self, level, player):
        self.player = player
        self.enemies = tuple(obj.entity for obj in level.objects if isinstance(obj.entity, Enemy))
        self._player_obstacle = SceneObject("player_collision", {"default": ObjectState((self._player_box(),))})
        self._hud_timer = 0.0
        for enemy in self.enemies:
            world = CollisionWorld3D(
                (box.collider for box in level.boxes), level.floor_bounds, level.base_height,
                objects=tuple(obj for obj in level.objects if obj is not enemy.scene_object) + (self._player_obstacle,),
            )
            enemy.bind(world, level)
        for obj in level.objects:
            if obj.rotation_pivot is not None:
                previous = obj.motion_guard
                obj.motion_guard = lambda state, guard=previous: (
                    (guard is None or guard(state)) and self._clear_of_enemies(state))

    def _player_box(self):
        body = self.player.body
        x, y, z = body.position
        return Box((x, y + body.height / 2, z), (body.radius * 2, body.height, body.radius * 2))

    def _clear_of_enemies(self, state):
        if not state.collidable:
            return True
        for enemy in self.enemies:
            body = enemy.body
            position = body.position
            for box in state.boxes:
                collider = box.collider
                if (collider.bottom < position.y + body.height - 1e-5 and collider.top > position.y + 1e-5
                        and collider.footprint.intersects_circle(position.x, position.z, body.radius)):
                    return False
        return True

    def update(self, delta_time):
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Enemy system delta time must be finite and nonnegative")
        dt = min(delta_time, settings.MAX_DELTA_TIME)
        self._player_obstacle.set_geometry((self._player_box(),))
        position = self.player.body.position
        for enemy in self.enemies:
            enemy.update(dt, position, self.player.camera.position)
        self._hud_timer -= dt
        if self._hud_timer > 0:
            return
        self._hud_timer = 0.2
        nearby = sorted(self.enemies, key=lambda enemy: math.dist(enemy.transform.position, tuple(position)))
        self.player.enemy_status = ""
        self.player.enemy_debug_lines = ()
        if nearby:
            enemy = nearby[0]
            distance = math.dist(enemy.transform.position, tuple(position))
            self.player.enemy_debug_lines = (f"ENEMY: {enemy.state.value} | {distance:.1f} m",)
            if enemy.state is EnemyState.CHASE and distance < 5:
                self.player.enemy_status = "Something is following you."
            elif distance < 2:
                self.player.enemy_status = "Something is close."
