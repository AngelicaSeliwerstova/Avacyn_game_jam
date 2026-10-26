import math

import glm

from engine.collision.world3d import CollisionWorld3D


class CharacterBody:
    """Тело игрока: положение ног, ступени, падение и сглаживание камеры."""

    def __init__(self, position: tuple[float, float, float], world: CollisionWorld3D,
                 radius: float, height: float, step_height: float, gravity: float,
                 collision_max_step: float, physics_step: float, camera_smoothing: float,
                 jump_height: float):
        if any(not math.isfinite(value) or value <= 0 for value in (
            radius, height, gravity, collision_max_step, physics_step, camera_smoothing,
        )) or not 0 <= step_height < height or not math.isfinite(jump_height) or jump_height < 0:
            raise ValueError("Character dimensions and physics parameters must be positive")
        self._position = glm.vec3(position)
        if world.is_blocked(self._position, radius, height):
            raise ValueError("Player spawn overlaps an obstacle or lies outside the floor")
        self.world = world
        self.radius = radius
        self.height = height
        self.step_height = step_height
        self.gravity = gravity
        self._jump_speed = math.sqrt(2 * gravity * jump_height)
        self._jump_pending = False
        self._collision_max_step = collision_max_step
        self._physics_step = physics_step
        self._camera_smoothing = camera_smoothing
        self._accumulator = 0.0
        self._camera_offset = 0.0
        self.vertical_speed = 0.0
        self.horizontal_speed = 0.0
        support = world.support_height(self._position, radius, self._position.y)
        self.grounded = abs(self._position.y - support) <= world.EPSILON

    @property
    def position(self) -> glm.vec3:
        return glm.vec3(self._position)

    def eye_position(self, eye_height: float) -> glm.vec3:
        if not 0 < eye_height < self.height:
            raise ValueError("Eye height must be inside the character body")
        # При спуске камера остаётся внутри физического тела, ниже потолка.
        offset = max(-min(self.step_height, eye_height / 2), min(
            self._camera_offset, self.height - eye_height - 0.01,
        ))
        return self._position + glm.vec3(0, eye_height + offset, 0)

    def update(self, delta_time: float, velocity: glm.vec3, jump: bool = False):
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Character delta time must be finite and nonnegative")
        self._accumulator += delta_time
        # Короткое нажатие сохраняется до следующего шага физики, но только с опоры.
        if jump and self.grounded:
            self._jump_pending = True
        # Фиксированный шаг даёт одинаковую физику при 30, 60 и 120 FPS.
        while self._accumulator + 1e-10 >= self._physics_step:
            self._step(self._physics_step, velocity)
            self._accumulator = max(0.0, self._accumulator - self._physics_step)

    def _step(self, delta_time: float, velocity: glm.vec3):
        if self._jump_pending:
            self._jump_pending = False
            if self.grounded and self._jump_speed > 0:
                self.vertical_speed = self._jump_speed
                self.grounded = False
        old_y = self._position.y
        old_x, old_z = self._position.x, self._position.z
        self._position = self.world.move_horizontal(
            self._position, velocity * delta_time, self.radius, self.height,
            self._collision_max_step, self.step_height, self.grounded,
        )
        self._camera_offset -= self._position.y - old_y
        self.horizontal_speed = math.hypot(self._position.x - old_x, self._position.z - old_z) / delta_time
        support = self.world.support_height(self._position, self.radius, self._position.y)
        self.grounded = self.grounded and abs(self._position.y - support) <= self.world.EPSILON
        if self.grounded:
            self.vertical_speed = 0.0
        else:
            vertical_delta = self.vertical_speed * delta_time - self.gravity * delta_time ** 2 / 2
            self.vertical_speed -= self.gravity * delta_time
            self._position, hit = self.world.move_vertical(
                self._position, vertical_delta, self.radius, self.height,
            )
            if hit:
                self.grounded = vertical_delta <= 0
                self.vertical_speed = 0.0
        self._camera_offset *= math.exp(-self._camera_smoothing * delta_time)
