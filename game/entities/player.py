from pathlib import Path
from dataclasses import replace
import math

import glm
import pygame

from config import controls, settings
from engine.collision.world3d import CollisionWorld3D
from engine.controllers.first_person import FirstPersonController
from engine.input.state import InputState
from engine.physics.character import CharacterBody
from engine.raycasting.aabb import RayHit, cast_ray
from engine.scene.box import Box
from engine.scene.camera import Camera, FixedCameraZone
from engine.scene.entity import Entity
from engine.scene.level import Level
from engine.scene.lighting import LightFlicker, MAX_POINT_LIGHTS, SpotLight
from engine.scene.model import ModelComponent
from engine.scene.transform import Transform
from engine.scene.object import ObjectState
from game.entities.player_state import MovementState
from game.levels.cameras import camera_model_boxes, camera_wall_normal, save_fixed_cameras
from game.levels.creator import save_creator_objects
from game.levels.creator_lights import load_creator_lights, save_creator_lights
from game.entities.flashlight import Flashlight
from game.interactions import InteractionController
from game.inventory import Inventory


class Player(Entity):
    """Персонаж объединяет тело, управление, камеру и место для своей модели."""

    _CREATOR_ENTRY_HEIGHT = 0.5
    _CAMERA_ZONE_HYSTERESIS = 0.2
    _CAMERA_TRANSITION_DURATION = 0.22
    _CREATOR_LIGHT_COLORS = (
        ("WARM", (1.0, 0.68, 0.35)),
        ("NEUTRAL", (1.0, 0.94, 0.78)),
        ("COLD", (0.45, 0.72, 1.0)),
        ("RED", (1.0, 0.18, 0.12)),
        ("GREEN", (0.22, 1.0, 0.4)),
    )
    _CREATOR_LIGHT_FLICKER = (
        ("OFF", None),
        ("SOFT", LightFlicker(interval=6.0, duration=0.8, minimum=0.5, seed=1)),
        ("ERRATIC", LightFlicker(interval=3.2, duration=1.0, minimum=0.08, seed=2)),
    )

    def __init__(self, body: CharacterBody, camera: Camera,
                 controller: FirstPersonController, model: ModelComponent, level: Level | None = None,
                 creator_mode: bool = False):
        super().__init__(name="player", model=model)
        self.body = body
        self.camera = camera
        self.controller = controller
        self._interaction_camera = Camera(
            position=tuple(camera.position), target=tuple(camera.target),
            fov_degrees=camera.fov_degrees, near=camera.near, far=camera.far,
        )
        self._level = level
        self._exit_found = False
        self._sprinting = False
        self._look_back = False
        self._locked_movement_yaw = None
        self._movement_yaw = math.radians(controller.yaw_degrees)
        self._camera_save_path = level.camera_save_path if level is not None else None
        self._camera_zones_authored = bool(level is not None and level.fixed_cameras_authored)
        authored = level.authored_fixed_cameras if level is not None else None
        self._authored_camera_zones = tuple(
            authored if authored is not None else (
                level.fixed_cameras if self._camera_zones_authored else ()
            )
        ) if level is not None else ()
        self._automatic_camera_zones = tuple(
            zone for zone in (level.fixed_cameras if level is not None else ())
            if zone not in self._authored_camera_zones
        )
        self._camera_zones = (
            self._authored_camera_zones if self._camera_zones_authored
            else self._automatic_camera_zones
        )
        self._active_camera_zone = None
        self._camera_selection_initialized = False
        self._camera_transition_remaining = 0.0
        self._movement_camera_lock = False
        self._creator_mode = False
        self._camera_editor_message = ""
        self._creator_yaw = math.radians(controller.yaw_degrees)
        self._creator_pitch = math.radians(controller.pitch_degrees)
        self._creator_objects = tuple(level.creator_objects) if level is not None else ()
        self._creator_objects_path = level.creator_objects_path if level is not None else None
        self._creator_lights_path = level.creator_lights_path if level is not None else None
        self._creator_lights = (
            load_creator_lights(self._creator_lights_path)
            if self._creator_lights_path is not None else ()
        )
        base_light_count = len(level.lighting.lights) if level is not None and level.lighting else 0
        if len(self._creator_lights) + base_light_count > MAX_POINT_LIGHTS:
            raise ValueError(f"Creator lights exceed the level limit of {MAX_POINT_LIGHTS} static lights")
        self.body.world.set_creator_colliders(self._creator_objects)
        self._creator_materials = ("rust", "concrete", "plaster", "brick")
        self._creator_material_index = 0
        self._selected_camera_index = None
        self._saved_creator_view = None
        self._camera_blink_elapsed = 0.0
        self._camera_marker_phase = None
        self._camera_marker_cache = ()
        self.flashlight = Flashlight(camera)
        self.inventory = Inventory()
        self.enemy_status = ""
        self.objective_status = ""
        self.enemy_debug_lines: tuple[str, ...] = ()
        self._interactions = InteractionController(
            level.boxes + level.decorations if level is not None else (),
            settings.INTERACTION_REACH, settings.INTERACTION_MESSAGE_SECONDS,
            pygame.key.name(controls.INPUT_BINDINGS.interact).upper()
            if controls.INPUT_BINDINGS.interact is not None else "-",
            objects=level.objects if level is not None else (), inventory=self.inventory,
            aspect_ratio=settings.RENDER_SIZE[0] / settings.RENDER_SIZE[1],
        )
        self._sync_transform()
        self._sync_third_person_camera()
        if creator_mode and self._creator_objects_path is not None:
            self._enter_creator_mode()
        if level is not None:
            for obj in level.objects:
                obj.motion_guard = self._object_motion_allowed

    def _object_motion_allowed(self, state: ObjectState) -> bool:
        if not state.collidable:
            return True
        position = self.body.position
        for box in state.boxes:
            collider = box.collider
            if (collider.bottom < position.y + self.body.height - 1e-5
                    and collider.top > position.y + 1e-5
                    and collider.footprint.intersects_circle(position.x, position.z, self.body.radius)):
                return False
        return True

    @property
    def aim_text(self) -> str:
        if self._creator_mode:
            return f"CREATOR | {self._camera_editor_message}" if self._camera_editor_message else ""
        return self._interactions.text

    @property
    def creator_help_text(self) -> tuple[str, str] | None:
        if not self._creator_mode:
            return None
        if self._selected_camera_index is not None:
            left = (
                f"CAMERA {self._selected_camera_index + 1}\n\n"
                "W / S\nTilt up / down\n\n"
                "A / D\nPan left / right\n\n"
                "E\nSave and exit\n\n"
                "F6\nLeave Creator"
            )
        else:
            left = (
                "CREATOR\n\n"
                "W / A / S / D\nFly around\n\n"
                "Mouse\nLook around\n\n"
                "Space / Ctrl\nFly up / down\n\n"
                "Shift\nMove faster\n\n"
                "E\nEdit aimed camera"
            )
        right = (
            f"SCENE\n\n{len(self._authored_camera_zones)} cameras\n"
            f"{len(self._creator_objects)} objects\n"
            f"{len(self._creator_lights)} lamps\n\n"
            "F7\nPlace wall camera\n\n"
            "F8\nChange block material\n\n"
            "Aim lamp + F8\nChange lamp color\n\n"
            "Aim lamp + F4\nChange flicker\n\n"
            "F9\nPlace block\n\n"
            "F10\nPlace lamp\n\n"
            "F12\nRecalculate shadows\n\n"
            "Delete\nRemove aimed item\n\n"
            "F6\nExit Creator"
        )
        return left, right

    @property
    def camera_marker_boxes(self):
        if not self._camera_zones_authored:
            return ()
        cameras = self._authored_camera_zones
        phases = tuple((self._camera_blink_elapsed + index * 0.17) % 1.0 < 0.55
                       for index in range(len(cameras)))
        if phases != self._camera_marker_phase:
            self._camera_marker_phase = phases
            self._camera_marker_cache = tuple(
                box for camera, led_on in zip(cameras, phases)
                for box in camera_model_boxes(camera, led_on)
            )
        return self._camera_marker_cache

    @property
    def creator_object_boxes(self):
        return self._creator_objects

    @property
    def creator_lights(self):
        return self._creator_lights

    @property
    def creator_light_boxes(self):
        boxes = []
        base_light_count = len(self._level.lighting.lights) if self._level and self._level.lighting else 0
        for index, light in enumerate(self._creator_lights):
            x, y, z = light.position
            ceiling = y + 0.24
            boxes.append(Box((x, y + 0.17, z), (1.12, 0.12, 0.52), material="rust"))
            boxes.append(Box(
                (x, y + 0.10, z), (0.92, 0.04, 0.32),
                emission=tuple(channel * 1.8 for channel in light.color),
                emission_light=base_light_count + index,
            ))
            suspension = ceiling - (y + 0.23)
            if suspension > 0.05:
                boxes.append(Box((x, ceiling - suspension / 2, z), (0.04, suspension, 0.04),
                                 material="rust"))
        return tuple(boxes)

    @property
    def creator_mode(self) -> bool:
        return self._creator_mode

    @property
    def creator_mode_available(self) -> bool:
        return (self._camera_save_path is not None or self._creator_objects_path is not None
                or self._creator_lights_path is not None)

    @property
    def fixed_camera_effect_active(self) -> bool:
        return self._active_camera_zone is not None and not self._creator_mode

    @property
    def camera_transition_strength(self) -> float:
        if self._creator_mode:
            return 0.0
        return self._camera_transition_remaining / self._CAMERA_TRANSITION_DURATION

    @property
    def dynamic_lights(self):
        return (self.flashlight.light,)

    @property
    def status_text(self) -> str:
        text = self._location_text()
        if self._creator_mode:
            camera_count = len(self._authored_camera_zones)
            text += ("\n" if text else "") + (
                f"CREATOR  |  {camera_count} CAMERAS  |  {len(self._creator_objects)} OBJECTS"
            )
        if self.inventory.key_names:
            text += ("\n" if text else "") + "KEYS: " + ", ".join(self.inventory.key_names)
        if self.enemy_status:
            text += ("\n" if text else "") + self.enemy_status
        if self.objective_status:
            text += ("\n" if text else "") + self.objective_status
        return text

    def _location_text(self) -> str:
        if self._level is None or len(self._level.floor_heights) < 2:
            return ""
        if self._exit_found:
            return "EXIT FOUND"
        y = self.body.position.y
        heights = self._level.floor_heights
        floor = min(range(len(heights)), key=lambda index: abs(heights[index] - y))
        label = self._level.floor_labels[floor] if self._level.floor_labels else str(floor + 1)
        title = f"FLOOR {label}" if self._level.floor_labels else f"FLOOR {floor + 1} / {len(heights)}"
        if self.body.grounded and abs(heights[floor] - y) > self.body.step_height:
            title = f"STAIRS - NEAR FLOOR {label}"
        hint = self._level.floor_hints[floor] if self._level.floor_hints else (
            "Find stairs. Exit is upstairs." if floor == 0 else "Find the rusted exit frame."
        )
        return title + "\n" + hint

    def update(self, delta_time: float, inputs: InputState) -> None:
        self._camera_transition_remaining = max(0.0, self._camera_transition_remaining - delta_time)
        self._sprinting = inputs.sprint
        self._look_back = inputs.look_back
        self._camera_blink_elapsed += delta_time
        if inputs.toggle_camera_editor and (
            self._camera_save_path is not None or self._creator_objects_path is not None
            or self._creator_lights_path is not None
        ):
            self._locked_movement_yaw = None
            if self._creator_mode and self._selected_camera_index is not None:
                self._leave_camera_edit()
            self._creator_mode = not self._creator_mode
            self._camera_editor_message = ""
            if self._creator_mode:
                self._enter_creator_mode()
        if self._creator_mode:
            if self._selected_camera_index is None:
                self._update_creator_camera(delta_time, inputs)
                if inputs.interact:
                    self._select_camera_for_edit()
            elif inputs.interact:
                self._leave_camera_edit()
            else:
                self._update_selected_camera(delta_time, inputs)
            if self._selected_camera_index is None:
                if inputs.add_camera:
                    self._place_fixed_camera()
                if inputs.add_object:
                    self._place_creator_object()
                if inputs.add_creator_light:
                    self._place_creator_light()
                if inputs.recalculate_shadows:
                    self._camera_editor_message = "RECALCULATING SHADOWS"
                if inputs.cycle_creator_material:
                    lamp_index = self._aimed_creator_lamp_index()
                    if lamp_index is None:
                        self._creator_material_index = (
                            self._creator_material_index + 1
                        ) % len(self._creator_materials)
                        self._camera_editor_message = (
                            f"MATERIAL: {self._creator_materials[self._creator_material_index]}"
                        )
                    else:
                        self._cycle_creator_light_color(lamp_index)
                if inputs.cycle_creator_light_flicker:
                    lamp_index = self._aimed_creator_lamp_index()
                    if lamp_index is None:
                        self._camera_editor_message = "AIM AT A LAMP TO CHANGE FLICKER"
                    else:
                        self._cycle_creator_light_flicker(lamp_index)
                if inputs.delete_camera:
                    self._delete_nearest_editor_item()
            self.flashlight.update(self.camera, toggle=inputs.toggle_flashlight)
            return

        previous_position = self.body.position
        self._movement_camera_lock = inputs.forward != 0 or inputs.right != 0
        active_camera = self._active_fixed_camera()
        movement_yaw = None
        if active_camera is not None:
            if inputs.forward == 0 and inputs.right == 0:
                self._locked_movement_yaw = None
            elif self._locked_movement_yaw is None:
                direction = glm.vec3(active_camera.target) - glm.vec3(active_camera.position)
                self._locked_movement_yaw = math.atan2(direction.z, direction.x)
            movement_yaw = self._locked_movement_yaw
        else:
            self._locked_movement_yaw = None
        self.controller.update(
            delta_time, inputs.forward, inputs.right, inputs.mouse_delta,
            sprint=inputs.sprint, jump=inputs.jump,
            crouch=inputs.crouch,
            zoom=inputs.zoom,
            movement_yaw=movement_yaw,
        )
        displacement = self.body.position - previous_position
        if math.hypot(displacement.x, displacement.z) > 1e-6:
            self._movement_yaw = math.atan2(displacement.z, displacement.x)
        self._sync_transform()
        self._sync_third_person_camera()
        self._sync_fixed_camera()
        self._sync_interaction_camera()
        self.flashlight.update(self._interaction_camera, toggle=inputs.toggle_flashlight)
        self._interactions.update(
            delta_time, self.camera, inputs.interact,
            reach_origin=tuple(self._interaction_camera.position),
        )
        if self._level is not None and self._level.goal_position is not None:
            self._exit_found = self._exit_found or math.dist(
                tuple(self.body.position), self._level.goal_position,
            ) <= self._level.goal_radius

    @property
    def movement_state(self) -> MovementState:
        if not self.body.grounded:
            return MovementState.RISING if self.body.vertical_speed > 0 else MovementState.FALLING
        if self.body.horizontal_speed < 0.01:
            return MovementState.IDLE
        if self.body.is_crouching:
            return MovementState.CROUCHING
        return MovementState.RUNNING if self._sprinting else MovementState.WALKING

    @property
    def model_animation_speed(self) -> float:
        return {
            MovementState.IDLE: 0.0,
            MovementState.WALKING: 1.0,
            MovementState.RUNNING: 1.5,
            MovementState.CROUCHING: 0.6,
            MovementState.RISING: 0.0,
            MovementState.FALLING: 0.0,
        }[self.movement_state]

    @property
    def debug_lines(self) -> tuple[str, ...]:
        x, y, z = self.body.position
        cx, cy, cz = self.camera.position
        area = "AREA: -"
        if self._level is not None:
            heights = self._level.floor_heights
            floor = min(range(len(heights)), key=lambda index: abs(heights[index] - y))
            stairs = self.body.grounded and abs(heights[floor] - y) > self.body.step_height
            label = self._level.floor_labels[floor] if self._level.floor_labels else f"{floor + 1}/{len(heights)}"
            area = f"FLOOR: {label}" + (" (STAIRS)" if stairs else "")
        goal = "-" if self._level is None or self._level.goal_position is None else (
            "FOUND" if self._exit_found else "SEARCHING"
        )
        return (
            f"FEET XYZ: {x:+.2f} {y:+.2f} {z:+.2f}",
            f"CAM XYZ: {cx:+.2f} {cy:+.2f} {cz:+.2f}",
            f"LOOK: Y {self.controller.yaw_degrees:.1f} P {self.controller.pitch_degrees:+.1f}"
            f" | FOV: {self.camera.fov_degrees:.1f} | F: {'ON' if self.flashlight.light.enabled else 'OFF'}",
            f"MOVE: {self.movement_state.value} | {self.body.horizontal_speed:.2f} m/s",
            f"GROUND: {'YES' if self.body.grounded else 'NO'} | VY: {self.body.vertical_speed:+.2f}"
            f" | {'CROUCH' if self.body.is_crouching else 'STAND'}",
            f"{area} | EXIT: {goal}",
            *self.enemy_debug_lines,
        )

    def _sync_transform(self):
        # Локальное направление вперёд у сущности -Z; смотрим по фактическому движению.
        self.transform = Transform(
            position=tuple(self.body.position),
            rotation=(0.0, (-math.degrees(self._movement_yaw) - 90.0) % 360.0, 0.0),
        )

    def _sync_third_person_camera(self):
        body_yaw = math.radians(self.controller.yaw_degrees)
        yaw = body_yaw + (math.pi if self._look_back else 0.0)
        pitch = math.radians(self.controller.pitch_degrees)
        horizontal_distance = settings.PLAYER_CAMERA_DISTANCE * math.cos(pitch)
        shoulder = settings.PLAYER_CAMERA_SHOULDER_OFFSET if self._look_back else 0.0
        focus = glm.vec3(
            self.body.position.x,
            self.body.position.y + min(self.body.height * 0.8, settings.PLAYER_EYE_HEIGHT),
            self.body.position.z,
        )
        look_direction = glm.vec3(
            math.cos(yaw) * math.cos(pitch),
            math.sin(pitch),
            math.sin(yaw) * math.cos(pitch),
        )
        camera_offset = glm.vec3(
            -math.cos(yaw) * horizontal_distance - math.sin(body_yaw) * shoulder,
            settings.PLAYER_CAMERA_HEIGHT - settings.PLAYER_CAMERA_DISTANCE * math.sin(pitch),
            -math.sin(yaw) * horizontal_distance + math.cos(body_yaw) * shoulder,
        )
        desired_distance = glm.length(camera_offset)
        hit = cast_ray(tuple(focus), tuple(camera_offset), self.body.world.colliders, desired_distance)
        if hit is not None:
            safe_distance = max(0.0, hit.distance - settings.PLAYER_CAMERA_WALL_MARGIN)
            camera_offset *= safe_distance / desired_distance
        self.camera.position = focus + camera_offset
        self.camera.target = self.camera.position + look_direction * settings.PLAYER_CAMERA_DISTANCE * 2

    def _sync_fixed_camera(self):
        if self._level is None or self._creator_mode:
            return
        zone = self._active_fixed_camera()
        if zone is None:
            return

        self.camera.position = self._camera_view_position(zone) if zone in self._authored_camera_zones \
            else glm.vec3(zone.position)
        self.camera.target = glm.vec3(zone.target)

    def _active_fixed_camera(self):
        if self._level is None or self._creator_mode:
            return None
        position = tuple(self._player_eye_position())
        active = self._active_camera_zone
        authored = self._authored_camera_zones
        automatic = self._automatic_camera_zones
        candidates = authored + automatic
        visible_zones = tuple(
            (camera, score)
            for camera in candidates
            if (score := self._fixed_camera_framing_score(camera, position)) is not None
        )
        active_score = next(
            (score for camera, score in visible_zones if camera is active),
            None,
        )
        if active_score is not None and self._movement_camera_lock:
            return active
        if (active_score is not None
                and self._camera_zone_contains(active, position, self._CAMERA_ZONE_HYSTERESIS)):
            self._camera_selection_initialized = True
            return active

        contained_zones = tuple(
            (camera, score) for camera, score in visible_zones if camera.contains(position)
        )

        if not contained_zones and active_score is not None:
            self._camera_selection_initialized = True
            return active

        choices = contained_zones or visible_zones
        if choices:
            zone = min(
                choices,
                key=lambda item: (
                    self._camera_zone_distance(item[0], position),
                    item[1],
                ),
            )[0]
        else:
            zone = min(candidates, key=lambda camera: self._camera_zone_distance(camera, position)) if candidates else None
        if self._camera_selection_initialized and zone is not active:
            self._camera_transition_remaining = self._CAMERA_TRANSITION_DURATION
        self._camera_selection_initialized = True
        self._active_camera_zone = zone
        return zone

    @staticmethod
    def _camera_zone_contains(zone: FixedCameraZone, position, margin: float = 0.0) -> bool:
        return all(
            low - margin <= value <= high + margin
            for value, low, high in zip(position, zone.minimum, zone.maximum)
        )

    def _fixed_camera_framing_score(self, zone: FixedCameraZone, point) -> float | None:
        camera_position = self._camera_view_position(zone)
        forward = glm.normalize(glm.vec3(zone.target) - camera_position)
        world_up = glm.vec3(0, 1, 0)
        right = glm.cross(forward, world_up)
        if glm.length(right) < 1e-6:
            return None
        right = glm.normalize(right)
        up = glm.normalize(glm.cross(right, forward))
        vertical_tangent = math.tan(math.radians(settings.CAMERA_FOV_DEGREES) / 2)
        horizontal_tangent = vertical_tangent * settings.RENDER_SIZE[0] / settings.RENDER_SIZE[1]
        body_position = glm.vec3(self.body.position)
        body_points = (
            glm.vec3(point),
            body_position + glm.vec3(0, self.body.height * 0.55, 0),
            body_position + glm.vec3(0, self.body.height * 0.25, 0),
        )
        scores = []
        for body_point in body_points:
            relative = body_point - camera_position
            depth = glm.dot(relative, forward)
            if depth <= settings.CAMERA_NEAR or depth >= settings.CAMERA_FAR:
                continue
            horizontal = glm.dot(relative, right) / (depth * horizontal_tangent)
            vertical = glm.dot(relative, up) / (depth * vertical_tangent)
            if abs(horizontal) > 1 or abs(vertical) > 1:
                continue
            distance = glm.length(relative)
            blocker = cast_ray(
                tuple(camera_position), tuple(relative), self.body.world.colliders, distance,
            )
            if blocker is not None and blocker.distance < distance - 0.05:
                continue
            scores.append(horizontal * horizontal + vertical * vertical)
        return min(scores) if scores else None

    @staticmethod
    def _camera_zone_distance(zone: FixedCameraZone, position) -> float:
        center = tuple((low + high) / 2 for low, high in zip(zone.minimum, zone.maximum))
        return math.dist(position, center)

    @staticmethod
    def _camera_view_position(zone: FixedCameraZone):
        direction = glm.normalize(glm.vec3(zone.target) - glm.vec3(zone.position))
        return glm.vec3(zone.position) + direction * 0.45

    def _enter_creator_mode(self):
        self._creator_mode = True
        self._creator_yaw = math.radians(self.controller.yaw_degrees)
        self._creator_pitch = math.radians(self.controller.pitch_degrees)
        eye_position = self.body.eye_position(settings.PLAYER_EYE_HEIGHT)
        self.camera.position = eye_position + glm.vec3(0, self._CREATOR_ENTRY_HEIGHT, 0)
        self._update_creator_view()
        self._camera_editor_message = ""

    def _update_creator_camera(self, delta_time: float, inputs: InputState):
        sensitivity = math.radians(settings.MOUSE_SENSITIVITY)
        dx, dy = inputs.mouse_delta
        self._creator_yaw = (self._creator_yaw + dx * sensitivity) % math.tau
        self._creator_pitch = max(
            -math.radians(89), min(math.radians(89), self._creator_pitch - dy * sensitivity),
        )
        forward = self._creator_direction()
        right = glm.normalize(glm.cross(forward, self.camera.up))
        movement = forward * inputs.forward + right * inputs.right
        movement += self.camera.up * (float(inputs.creator_up) - float(inputs.crouch))
        if glm.length(movement) > 0:
            movement = glm.normalize(movement)
        speed = 16.0 if inputs.sprint else 6.0
        self.camera.position += movement * speed * min(delta_time, 0.1)
        self._update_creator_view()
        self._interaction_camera.position = glm.vec3(self.camera.position)
        self._interaction_camera.target = glm.vec3(self.camera.target)

    def _creator_direction(self):
        return glm.vec3(
            math.cos(self._creator_yaw) * math.cos(self._creator_pitch),
            math.sin(self._creator_pitch),
            math.sin(self._creator_yaw) * math.cos(self._creator_pitch),
        )

    def _update_creator_view(self):
        self.camera.target = self.camera.position + self._creator_direction()

    def _select_camera_for_edit(self):
        if self._camera_save_path is None:
            self._camera_editor_message = "CAMERAS CANNOT BE SAVED ON THIS LEVEL"
            return
        direction = glm.normalize(self.camera.target - self.camera.position)
        origin = self.camera.position
        candidates = []
        for index, zone in enumerate(self._authored_camera_zones):
            offset = glm.vec3(zone.position) - origin
            distance_along_view = glm.dot(offset, direction)
            if distance_along_view < 0 or distance_along_view > settings.CAMERA_FAR:
                continue
            closest = origin + direction * distance_along_view
            miss_distance = glm.length(glm.vec3(zone.position) - closest)
            if miss_distance <= 0.7:
                candidates.append((distance_along_view, index, zone))
        if not candidates:
            self._camera_editor_message = "AIM AT A CAMERA AND PRESS E"
            return
        _, index, zone = min(candidates, key=lambda candidate: candidate[0])
        self._selected_camera_index = index
        self._saved_creator_view = (
            glm.vec3(self.camera.position), self._creator_yaw, self._creator_pitch,
        )
        self._selected_camera_yaw, self._selected_camera_pitch = self._camera_angles(zone)
        self.camera.position = self._camera_view_position(zone)
        self.camera.target = glm.vec3(zone.target)
        self._camera_editor_message = f"EDITING CAMERA {index + 1} | WASD AIM, E DONE"

    @staticmethod
    def _camera_angles(zone: FixedCameraZone):
        direction = glm.normalize(glm.vec3(zone.target) - glm.vec3(zone.position))
        yaw = math.atan2(direction.z, direction.x)
        pitch = math.asin(max(-1.0, min(1.0, direction.y)))
        return yaw, pitch

    def _update_selected_camera(self, delta_time: float, inputs: InputState):
        index = self._selected_camera_index
        if index is None:
            return
        turn = math.radians(55) * min(delta_time, 0.1)
        self._selected_camera_yaw += inputs.right * turn
        self._selected_camera_pitch = max(
            -math.radians(80),
            min(math.radians(80), self._selected_camera_pitch + inputs.forward * turn),
        )
        zone = self._authored_camera_zones[index]
        direction = glm.vec3(
            math.cos(self._selected_camera_yaw) * math.cos(self._selected_camera_pitch),
            math.sin(self._selected_camera_pitch),
            math.sin(self._selected_camera_yaw) * math.cos(self._selected_camera_pitch),
        )
        target = glm.vec3(zone.position) + direction * glm.length(
            glm.vec3(zone.target) - glm.vec3(zone.position),
        )
        updated = replace(zone, target=tuple(target))
        cameras = (
            self._authored_camera_zones[:index] + (updated,)
            + self._authored_camera_zones[index + 1:]
        )
        self._authored_camera_zones = cameras
        self._camera_zones = cameras
        save_fixed_cameras(self._camera_save_path, cameras)
        self._camera_marker_phase = None
        self.camera.position = self._camera_view_position(updated)
        self.camera.target = glm.vec3(updated.target)
        self._camera_editor_message = f"EDITING CAMERA {index + 1} | WASD AIM, E DONE"

    def _leave_camera_edit(self):
        self._selected_camera_index = None
        if self._saved_creator_view is not None:
            position, self._creator_yaw, self._creator_pitch = self._saved_creator_view
            self.camera.position = position
            self._update_creator_view()
            self._saved_creator_view = None
        self._camera_editor_message = "CAMERA SAVED"

    def _editor_colliders(self):
        return self.body.world.colliders

    def _creator_surface_hit(self, origin, direction):
        colliders = self._editor_colliders()
        hit = cast_ray(origin, direction, colliders, settings.CAMERA_FAR)
        if direction[1] < -1e-8:
            floor_distance = (self._level.base_height - origin[1]) / direction[1]
            floor_x = origin[0] + direction[0] * floor_distance
            floor_z = origin[2] + direction[2] * floor_distance
            bounds = self._level.floor_bounds
            if (0 <= floor_distance <= settings.CAMERA_FAR
                    and bounds.min_x <= floor_x <= bounds.max_x
                    and bounds.min_z <= floor_z <= bounds.max_z
                    and (hit is None or floor_distance < hit.distance)):
                hit = RayHit(
                    len(colliders), floor_distance,
                    (floor_x, self._level.base_height, floor_z),
                )
                return hit, colliders, (0.0, 1.0, 0.0)
        if hit is None:
            return None, colliders, None
        normal = (
            (0.0, 1.0, 0.0) if hit.index == len(colliders)
            else camera_wall_normal(hit.position, colliders[hit.index])
        )
        return hit, colliders, normal

    def _place_fixed_camera(self):
        if self._camera_save_path is None:
            return
        colliders = self._editor_colliders()
        origin = tuple(self.camera.position)
        direction = tuple(self.camera.target - self.camera.position)
        hit = cast_ray(origin, direction, colliders, settings.CAMERA_FAR)
        if hit is None:
            self._camera_editor_message = "AIM AT A WALL TO PLACE"
            return
        normal = camera_wall_normal(hit.position, colliders[hit.index])
        if normal is None:
            self._camera_editor_message = "CAMERAS CAN ONLY MOUNT ON WALLS"
            return

        camera_position = glm.vec3(hit.position) + glm.vec3(normal) * 0.16
        camera_target = camera_position + glm.vec3(normal) * 8.0
        zone_center = glm.vec3(hit.position) + glm.vec3(normal) * 1.5
        zone_floor = hit.position[1] - settings.PLAYER_EYE_HEIGHT
        camera = FixedCameraZone(
            minimum=(zone_center.x - 2.5, zone_floor - 0.25, zone_center.z - 2.5),
            maximum=(zone_center.x + 2.5, zone_floor + settings.PLAYER_HEIGHT + 0.5,
                     zone_center.z + 2.5),
            position=tuple(camera_position),
            target=tuple(camera_target),
        )
        updated = self._authored_camera_zones + (camera,)
        save_fixed_cameras(self._camera_save_path, updated)
        self._authored_camera_zones = updated
        self._camera_zones = updated
        self._camera_zones_authored = True
        self._camera_marker_phase = None
        self._camera_editor_message = "CAMERA MOUNTED ON WALL"

    def _place_creator_object(self):
        if self._creator_objects_path is None:
            return
        hit, colliders, normal = self._creator_surface_hit(
            tuple(self.camera.position), tuple(self.camera.target - self.camera.position),
        )
        if hit is None:
            self._camera_editor_message = "AIM AT A SURFACE TO PLACE OBJECT"
            return
        normal = normal or (0.0, 1.0, 0.0)
        size = (0.6, 0.6, 0.6)
        offset = size[1] / 2 if normal == (0.0, 1.0, 0.0) else 0.31
        position = tuple(value + direction * offset for value, direction in zip(hit.position, normal))
        yaw = math.degrees(math.atan2(-normal[0], -normal[2]))
        placed = Box(
            position, size, material=self._creator_materials[self._creator_material_index],
            yaw_degrees=yaw,
        )
        updated = self._creator_objects + (placed,)
        save_creator_objects(self._creator_objects_path, updated)
        self._creator_objects = updated
        self.body.world.set_creator_colliders(updated)
        self._camera_editor_message = f"PLACED {placed.material.upper()} BLOCK"

    def _place_creator_light(self):
        if self._creator_lights_path is None:
            self._camera_editor_message = "LAMPS CANNOT BE SAVED ON THIS LEVEL"
            return
        base_light_count = len(self._level.lighting.lights) if self._level.lighting else 0
        if len(self._creator_lights) >= MAX_POINT_LIGHTS - base_light_count:
            self._camera_editor_message = (
                f"MAXIMUM {MAX_POINT_LIGHTS - base_light_count} CREATOR LAMPS REACHED"
            )
            return

        origin = tuple(self.camera.position)
        direction = tuple(self._creator_direction())
        colliders = self._editor_colliders()
        hit = cast_ray(origin, direction, colliders, settings.CAMERA_FAR)
        if hit is None:
            self._camera_editor_message = "AIM AT THE CEILING TO PLACE LAMP"
            return
        floor = min(self._level.floor_heights, key=lambda height: abs(height - self.body.position.y))
        room_height = self._level.creator_room_height
        ceiling = floor + room_height if room_height is not None else None
        if (direction[1] <= 0.1
                or abs(hit.position[1] - colliders[hit.index].bottom) > 0.05
                or ceiling is None
                or abs(hit.position[1] - ceiling) > 0.25):
            self._camera_editor_message = "AIM AT THIS FLOOR'S CEILING TO PLACE LAMP"
            return
        lamp = SpotLight(
            position=(hit.position[0], ceiling - 0.24, hit.position[2]),
            direction=(0.0, -1.0, 0.0),
            color=(1.0, 0.78, 0.52),
            intensity=3.5,
            radius=9.0,
            inner_angle=30.0,
            outer_angle=55.0,
            shadows=True,
        )
        updated = self._creator_lights + (lamp,)
        save_creator_lights(self._creator_lights_path, updated)
        self._creator_lights = updated
        self._camera_editor_message = f"PLACED WARM LAMP {len(updated)}"

    def _aimed_creator_lamp_index(self):
        if not self._creator_lights:
            return None
        origin = glm.vec3(self.camera.position)
        direction = glm.normalize(self.camera.target - self.camera.position)
        blocker = cast_ray(
            tuple(origin), tuple(direction), self.body.world.colliders, settings.CAMERA_FAR,
        )
        aimed = []
        for index, light in enumerate(self._creator_lights):
            position = glm.vec3(light.position[0], light.position[1] + 0.12, light.position[2])
            offset = position - origin
            distance = glm.dot(offset, direction)
            if distance <= 0 or distance > settings.CAMERA_FAR:
                continue
            miss = glm.length(offset - direction * distance)
            if (miss <= 0.7
                    and (blocker is None or distance - 0.7 <= blocker.distance + 0.05)):
                aimed.append((distance, index))
        return min(aimed)[1] if aimed else None

    def _update_creator_light(self, index, **changes):
        if self._creator_lights_path is None:
            return
        lamp = replace(self._creator_lights[index], **changes)
        updated = self._creator_lights[:index] + (lamp,) + self._creator_lights[index + 1:]
        save_creator_lights(self._creator_lights_path, updated)
        self._creator_lights = updated

    def _cycle_creator_light_color(self, index):
        light = self._creator_lights[index]
        current = next(
            (i for i, (_, color) in enumerate(self._CREATOR_LIGHT_COLORS) if color == light.color),
            -1,
        )
        name, color = self._CREATOR_LIGHT_COLORS[(current + 1) % len(self._CREATOR_LIGHT_COLORS)]
        self._update_creator_light(index, color=color)
        self._camera_editor_message = f"LAMP COLOR: {name}"

    def _cycle_creator_light_flicker(self, index):
        light = self._creator_lights[index]
        current = next(
            (i for i, (_, flicker) in enumerate(self._CREATOR_LIGHT_FLICKER)
             if flicker == light.flicker),
            -1,
        )
        name, flicker = self._CREATOR_LIGHT_FLICKER[
            (current + 1) % len(self._CREATOR_LIGHT_FLICKER)
        ]
        self._update_creator_light(index, flicker=flicker)
        self._camera_editor_message = f"LAMP FLICKER: {name}"

    def _delete_nearest_editor_item(self):
        origin = tuple(self.camera.position)
        direction = glm.normalize(self.camera.target - self.camera.position)
        blocker = cast_ray(origin, tuple(direction), self.body.world.colliders, settings.CAMERA_FAR)
        aimed = []

        def consider(kind, index, position, radius):
            offset = glm.vec3(position) - glm.vec3(origin)
            distance = glm.dot(offset, direction)
            if distance <= 0 or distance > settings.CAMERA_FAR:
                return
            miss = glm.length(offset - direction * distance)
            if miss <= radius and (blocker is None or distance - radius <= blocker.distance + 0.05):
                aimed.append((distance, kind, index))

        for index, camera in enumerate(self._authored_camera_zones):
            consider("camera", index, camera.position, 0.65)
        for index, box in enumerate(self._creator_objects):
            consider("object", index, box.position, max(box.bounds_half_size))
        for index, light in enumerate(self._creator_lights):
            consider("lamp", index, (light.position[0], light.position[1] + 0.12, light.position[2]), 0.7)
        if not aimed:
            self._camera_editor_message = "AIM AT AN ITEM AND PRESS DELETE"
            return
        _, kind, index = min(aimed)
        if kind == "camera" and self._camera_save_path is not None:
            self._authored_camera_zones = (
                self._authored_camera_zones[:index] + self._authored_camera_zones[index + 1:]
            )
            self._camera_zones = (
                self._authored_camera_zones if self._camera_zones_authored
                else self._automatic_camera_zones
            )
            save_fixed_cameras(self._camera_save_path, self._authored_camera_zones)
            self._camera_marker_phase = None
        elif kind == "object" and self._creator_objects_path is not None:
            self._creator_objects = self._creator_objects[:index] + self._creator_objects[index + 1:]
            self.body.world.set_creator_colliders(self._creator_objects)
            save_creator_objects(self._creator_objects_path, self._creator_objects)
        elif kind == "lamp" and self._creator_lights_path is not None:
            self._creator_lights = self._creator_lights[:index] + self._creator_lights[index + 1:]
            save_creator_lights(self._creator_lights_path, self._creator_lights)
        else:
            return
        self._camera_editor_message = f"REMOVED {kind.upper()}"

    def _sync_interaction_camera(self):
        position = self._player_eye_position()
        yaw = math.radians(self.controller.yaw_degrees) + (math.pi if self._look_back else 0.0)
        pitch = math.radians(self.controller.pitch_degrees)
        direction = glm.vec3(
            math.cos(yaw) * math.cos(pitch),
            math.sin(pitch),
            math.sin(yaw) * math.cos(pitch),
        )
        self._interaction_camera.position = position
        self._interaction_camera.target = position + direction

    def _player_eye_position(self):
        height_range = self.body.standing_height - self.body.crouch_height
        stance = ((self.body.height - self.body.crouch_height) / height_range
                  if height_range > 0 else 1.0)
        eye_height = (settings.PLAYER_CROUCH_EYE_HEIGHT
                      + (settings.PLAYER_EYE_HEIGHT - settings.PLAYER_CROUCH_EYE_HEIGHT) * stance)
        return self.body.eye_position(eye_height)


def create_player(level: Level, world: CollisionWorld3D, creator_mode: bool = False) -> Player:
    x, y, z = level.spawn_position
    body = CharacterBody(
        position=(x, y - settings.PLAYER_EYE_HEIGHT, z), world=world,
        radius=settings.PLAYER_RADIUS, height=settings.PLAYER_HEIGHT,
        step_height=settings.PLAYER_STEP_HEIGHT, gravity=settings.GRAVITY,
        collision_max_step=settings.COLLISION_MAX_STEP, physics_step=settings.PHYSICS_STEP,
        camera_smoothing=settings.STAIR_CAMERA_SMOOTHING, jump_height=settings.JUMP_HEIGHT,
        crouch_height=settings.PLAYER_CROUCH_HEIGHT, stance_speed=settings.PLAYER_STANCE_SPEED,
    )
    camera = Camera(
        position=level.spawn_position, target=level.spawn_target,
        fov_degrees=settings.CAMERA_FOV_DEGREES, near=settings.CAMERA_NEAR, far=settings.CAMERA_FAR,
    )
    controller = FirstPersonController(
        camera=camera, body=body, eye_height=settings.PLAYER_EYE_HEIGHT,
        move_speed=settings.MOVE_SPEED, sprint_speed=settings.SPRINT_SPEED,
        crouch_speed=settings.CROUCH_SPEED, crouch_eye_height=settings.PLAYER_CROUCH_EYE_HEIGHT,
        zoom_fov_degrees=settings.CAMERA_ZOOM_FOV_DEGREES, zoom_speed=settings.CAMERA_ZOOM_SPEED,
        mouse_sensitivity=settings.MOUSE_SENSITIVITY,
        pitch_limit_degrees=settings.PITCH_LIMIT_DEGREES, max_delta_time=settings.MAX_DELTA_TIME,
        player_radius=settings.PLAYER_RADIUS, collision_max_step=settings.COLLISION_MAX_STEP,
    )
    model_root = Path(__file__).resolve().parents[2] / "resources" / "models"
    source = None if settings.PLAYER_MODEL is None else model_root / settings.PLAYER_MODEL
    model = ModelComponent(
        source_path=source,
        local_transform=Transform(
            position=settings.PLAYER_MODEL_OFFSET, rotation=settings.PLAYER_MODEL_ROTATION,
            scale=(settings.PLAYER_MODEL_SCALE,) * 3,
        ),
    )
    return Player(body, camera, controller, model, level=level, creator_mode=creator_mode)
