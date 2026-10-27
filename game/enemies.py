import math
import glm

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.scene.box import Box
from engine.scene.object import ObjectState, SceneObject
from engine.raycasting.aabb import cast_ray
from game.entities.enemy import Enemy, EnemyState


class EnemySystem:
    """Связывает врагов, игрока и двери; движок знает только метод update."""

    def __init__(self, level, player, on_caught=None):
        self.player = player
        self._level = level
        self._static_colliders = tuple(box.collider for box in level.boxes)
        self._on_caught = on_caught
        self._caught = False
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
        if self._caught:
            return
        dt = min(delta_time, settings.MAX_DELTA_TIME)
        self._player_obstacle.set_geometry((self._player_box(),))
        position = self.player.body.position
        target = position
        if not self.player.body.grounded:
            target = glm.vec3(position)
            target.y = self.player.body.world.support_height(position, self.player.body.radius, position.y)
        for enemy in self.enemies:
            if self._try_catch(enemy):
                return
            enemy.update(dt, target)
            if self._try_catch(enemy):
                return
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
            self.player.enemy_debug_lines = (f"ENEMY: {enemy.state.value} | {distance:.1f} m | PATH: {enemy.path_length}",)
            if distance < 2:
                self.player.enemy_status = "Something is close."
            elif enemy.state is EnemyState.CHASE and distance < 5:
                self.player.enemy_status = "Something is following you."

    def _try_catch(self, enemy):
        if self._on_caught is None:
            return False
        body = enemy.body
        position = body.position
        player = self._player_box().collider
        bottom = max(position.y, player.bottom)
        top = min(position.y + body.height, player.top)
        if (top - bottom <= 1e-5 or not player.footprint.intersects_circle(
                position.x, position.z, body.radius + settings.ENEMY_CATCH_MARGIN)):
            return False
        # Даже тонкая закрытая дверь или стена прерывает контакт.
        target = self.player.body.position
        origin = (position.x, (bottom + top) / 2, position.z)
        direction = (target.x - position.x, 0, target.z - position.z)
        distance = math.hypot(direction[0], direction[2])
        obstacles = self._static_colliders + tuple(
            box.collider for obj in self._level.objects
            if obj.current_state.collidable and not isinstance(obj.entity, Enemy)
            for box in obj.current_state.boxes
        )
        if cast_ray(origin, direction if distance else (0, 1, 0), obstacles, distance) is not None:
            return False
        self._caught = True
        self._on_caught()
        return True
