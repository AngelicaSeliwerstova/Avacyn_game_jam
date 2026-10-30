import math

import glm

from engine.collision.world import CollisionWorld
from engine.scene.camera import Camera
from engine.physics.character import CharacterBody


class FirstPersonController:
    """Обзор и направление ходьбы; вертикальное движение считает тело игрока."""

    def __init__(
        self,
        camera: Camera,
        move_speed: float,
        mouse_sensitivity: float,
        pitch_limit_degrees: float,
        max_delta_time: float,
        player_radius: float,
        collision_max_step: float,
        collision_world: CollisionWorld | None = None,
        body: CharacterBody | None = None,
        eye_height: float = 1.6,
        sprint_speed: float | None = None,
        crouch_speed: float | None = None,
        crouch_eye_height: float | None = None,
        zoom_fov_degrees: float | None = None,
        zoom_speed: float = 12.0,
    ):
        if move_speed < 0 or mouse_sensitivity < 0:
            raise ValueError("Movement speed and mouse sensitivity must be nonnegative")
        if sprint_speed is not None and (not math.isfinite(sprint_speed) or sprint_speed < move_speed):
            raise ValueError("Sprint speed must be finite and at least the walking speed")
        crouch_speed = move_speed / 2 if crouch_speed is None else crouch_speed
        if not math.isfinite(crouch_speed) or not 0 <= crouch_speed <= move_speed:
            raise ValueError("Crouch speed must be finite and between zero and walking speed")
        zoom_fov_degrees = camera.fov_degrees if zoom_fov_degrees is None else zoom_fov_degrees
        if (not 0 < zoom_fov_degrees <= camera.fov_degrees
                or not math.isfinite(zoom_speed) or zoom_speed <= 0):
            raise ValueError("Zoom FOV must fit the normal view; zoom speed must be positive")
        if not 0 < pitch_limit_degrees < 90:
            raise ValueError("Pitch limit must be between 0 and 90 degrees")
        if max_delta_time <= 0:
            raise ValueError("Maximum delta time must be positive")
        if player_radius <= 0 or collision_max_step <= 0:
            raise ValueError("Player radius and collision step must be positive")
        if body is not None and collision_world is not None:
            raise ValueError("Choose either a character body or planar collisions")
        if body is not None:
            body.eye_position(eye_height)
            if crouch_eye_height is None:
                crouch_eye_height = eye_height * body.crouch_height / body.standing_height
            if (not math.isfinite(crouch_eye_height)
                    or not 0 < crouch_eye_height < body.crouch_height
                    or crouch_eye_height > eye_height):
                raise ValueError("Crouch eye height must fit the crouching body and standing view")
        if collision_world is not None and collision_world.is_blocked(camera.position, player_radius):
            raise ValueError("Player spawn overlaps an obstacle or lies outside the floor")

        direction = camera.target - camera.position
        if glm.length(direction) == 0:
            raise ValueError("Camera target must differ from its position")
        self._camera = camera
        self._move_speed = move_speed
        self._sprint_speed = move_speed if sprint_speed is None else sprint_speed
        self._crouch_speed = crouch_speed
        self._crouch_eye_height = crouch_eye_height
        self._normal_fov = camera.fov_degrees
        self._zoom_fov = zoom_fov_degrees
        self._zoom_speed = zoom_speed
        self._normal_tan_half_fov = math.tan(math.radians(camera.fov_degrees) / 2)
        self._sensitivity = math.radians(mouse_sensitivity)
        self._pitch_limit = math.radians(pitch_limit_degrees)
        self._max_delta_time = max_delta_time
        self._player_radius = player_radius
        self._collision_max_step = collision_max_step
        self._collision_world = collision_world
        self._body = body
        self._eye_height = eye_height
        self._yaw = math.atan2(direction.z, direction.x)
        self._pitch = math.atan2(direction.y, math.hypot(direction.x, direction.z))
        self._pitch = max(-self._pitch_limit, min(self._pitch_limit, self._pitch))
        self._update_target()

    @property
    def yaw_degrees(self) -> float:
        """Направление тела в XZ: 0 градусов соответствует +X."""
        return math.degrees(self._yaw)

    @property
    def pitch_degrees(self) -> float:
        return math.degrees(self._pitch)

    def update(
        self,
        delta_time: float,
        forward_axis: float = 0.0,
        right_axis: float = 0.0,
        mouse_delta: tuple[int, int] = (0, 0),
        sprint: bool = False,
        jump: bool = False,
        crouch: bool = False,
        zoom: bool = False,
        movement_yaw: float | None = None,
    ):
        if delta_time < 0:
            raise ValueError("Delta time must be nonnegative")
        delta_time = min(delta_time, self._max_delta_time)

        target_fov = self._zoom_fov if zoom else self._normal_fov
        fov = target_fov + (self._camera.fov_degrees - target_fov) * math.exp(-self._zoom_speed * delta_time)
        self._camera.fov_degrees = target_fov if abs(fov - target_fov) < 0.001 else fov
        # Сохраняем комфортную скорость наведения в экранных координатах при зуме.
        sensitivity = (self._sensitivity * math.tan(math.radians(self._camera.fov_degrees) / 2)
                       / self._normal_tan_half_fov)

        # Мышь передаёт пройденные пиксели; умножать их на delta_time не нужно.
        dx, dy = mouse_delta
        self._yaw = (self._yaw + dx * sensitivity) % math.tau
        self._pitch = max(
            -self._pitch_limit,
            min(self._pitch_limit, self._pitch - dy * sensitivity),
        )

        # Fixed views can supply a camera-relative walking direction without changing look controls.
        walk_yaw = self._yaw if movement_yaw is None else movement_yaw
        forward = glm.vec3(math.cos(walk_yaw), 0.0, math.sin(walk_yaw))
        right = glm.cross(forward, self._camera.up)
        movement = forward * forward_axis + right * right_axis
        if glm.length(movement) > 0:
            movement = glm.normalize(movement)
        speed = self._sprint_speed if sprint else self._move_speed
        if self._body is not None:
            if self._body.is_crouching or (crouch and self._body.grounded and not jump):
                speed = self._crouch_speed
            self._body.update(delta_time, movement * speed, jump=jump, crouch=crouch)
            height_range = self._body.standing_height - self._body.crouch_height
            stance = ((self._body.height - self._body.crouch_height) / height_range
                      if height_range > 0 else 1.0)
            eye_height = self._crouch_eye_height + (self._eye_height - self._crouch_eye_height) * stance
            self._camera.position = self._body.eye_position(eye_height)
        elif glm.length(movement) > 0:
            displacement = movement * speed * delta_time
            if self._collision_world is None:
                self._camera.position += displacement
            else:
                self._camera.position = self._collision_world.move(
                    self._camera.position, displacement,
                    self._player_radius, self._collision_max_step,
                )
        self._update_target()

    def _update_target(self):
        direction = glm.vec3(
            math.cos(self._yaw) * math.cos(self._pitch),
            math.sin(self._pitch),
            math.sin(self._yaw) * math.cos(self._pitch),
        )
        self._camera.target = self._camera.position + direction
