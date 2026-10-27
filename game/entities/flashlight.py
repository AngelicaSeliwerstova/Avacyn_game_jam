import math

import glm

from config import settings
from engine.scene.camera import Camera
from engine.scene.lighting import SpotLight


class Flashlight:
    """Фонарик персонажа управляет обычным динамическим источником движка."""

    def __init__(self, camera: Camera, offset=None):
        self.light = SpotLight(
            position=(0, 0, 0), direction=(0, 0, -1),
            color=settings.FLASHLIGHT_COLOR, intensity=settings.FLASHLIGHT_INTENSITY,
            radius=settings.FLASHLIGHT_RANGE, inner_angle=settings.FLASHLIGHT_INNER_ANGLE,
            outer_angle=settings.FLASHLIGHT_OUTER_ANGLE, enabled=settings.FLASHLIGHT_STARTS_ON,
            shadows=settings.FLASHLIGHT_SHADOWS,
        )
        self._offset = glm.vec3(settings.FLASHLIGHT_OFFSET if offset is None else offset)
        self._aim_distance = settings.FLASHLIGHT_AIM_DISTANCE
        if (not math.isfinite(self._aim_distance) or self._aim_distance <= 0
                or not all(math.isfinite(v) for v in self._offset)):
            raise ValueError("Flashlight offset must be finite and aim distance must be positive")
        self.update(camera)

    def update(self, camera: Camera, toggle: bool = False):
        if toggle:
            self.light.enabled = not self.light.enabled
        forward = glm.normalize(camera.target - camera.position)
        right = glm.normalize(glm.cross(forward, camera.up))
        up = glm.cross(right, forward)
        origin = (camera.position + right * self._offset.x + up * self._offset.y
                  + forward * self._offset.z)
        target = camera.position + forward * self._aim_distance
        self.light.position = tuple(origin)
        self.light.direction = tuple(glm.normalize(target - origin))
