import math

import glm

from engine.scene.camera import Camera


class FirstPersonController:
    """Горизонтальное движение и обзор камеры; получает уже прочитанный ввод."""

    def __init__(
        self,
        camera: Camera,
        move_speed: float,
        mouse_sensitivity: float,
        pitch_limit_degrees: float,
        max_delta_time: float,
    ):
        if move_speed < 0 or mouse_sensitivity < 0:
            raise ValueError("Movement speed and mouse sensitivity must be nonnegative")
        if not 0 < pitch_limit_degrees < 90:
            raise ValueError("Pitch limit must be between 0 and 90 degrees")
        if max_delta_time <= 0:
            raise ValueError("Maximum delta time must be positive")

        direction = camera.target - camera.position
        if glm.length(direction) == 0:
            raise ValueError("Camera target must differ from its position")
        self._camera = camera
        self._move_speed = move_speed
        self._sensitivity = math.radians(mouse_sensitivity)
        self._pitch_limit = math.radians(pitch_limit_degrees)
        self._max_delta_time = max_delta_time
        self._yaw = math.atan2(direction.z, direction.x)
        self._pitch = math.atan2(direction.y, math.hypot(direction.x, direction.z))
        self._pitch = max(-self._pitch_limit, min(self._pitch_limit, self._pitch))
        self._update_target()

    def update(
        self,
        delta_time: float,
        forward_axis: float = 0.0,
        right_axis: float = 0.0,
        mouse_delta: tuple[int, int] = (0, 0),
    ):
        if delta_time < 0:
            raise ValueError("Delta time must be nonnegative")
        delta_time = min(delta_time, self._max_delta_time)

        # Мышь передаёт пройденные пиксели; умножать их на delta_time не нужно.
        dx, dy = mouse_delta
        self._yaw = (self._yaw + dx * self._sensitivity) % math.tau
        self._pitch = max(
            -self._pitch_limit,
            min(self._pitch_limit, self._pitch - dy * self._sensitivity),
        )

        # Ходьба остаётся в плоскости XZ независимо от вертикального обзора.
        forward = glm.vec3(math.cos(self._yaw), 0.0, math.sin(self._yaw))
        right = glm.cross(forward, self._camera.up)
        movement = forward * forward_axis + right * right_axis
        if glm.length(movement) > 0:
            movement = glm.normalize(movement)
            self._camera.position += movement * self._move_speed * delta_time
        self._update_target()

    def _update_target(self):
        direction = glm.vec3(
            math.cos(self._yaw) * math.cos(self._pitch),
            math.sin(self._pitch),
            math.sin(self._yaw) * math.cos(self._pitch),
        )
        self._camera.target = self._camera.position + direction
