from pathlib import Path
import math

import pygame

from config import controls, settings
from engine.collision.world3d import CollisionWorld3D
from engine.controllers.first_person import FirstPersonController
from engine.input.state import InputState
from engine.physics.character import CharacterBody
from engine.scene.camera import Camera
from engine.scene.entity import Entity
from engine.scene.level import Level
from engine.scene.model import ModelComponent
from engine.scene.transform import Transform
from engine.scene.object import ObjectState
from game.entities.player_state import MovementState
from game.entities.flashlight import Flashlight
from game.interactions import InteractionController
from game.inventory import Inventory


class Player(Entity):
    """Персонаж объединяет тело, управление, камеру и место для своей модели."""

    def __init__(self, body: CharacterBody, camera: Camera,
                 controller: FirstPersonController, model: ModelComponent, level: Level | None = None):
        super().__init__(name="player", model=model)
        self.body = body
        self.camera = camera
        self.controller = controller
        self._level = level
        self._exit_found = False
        self._sprinting = False
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
        )
        self._sync_transform()
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
        return self._interactions.text

    @property
    def dynamic_lights(self):
        return (self.flashlight.light,)

    @property
    def status_text(self) -> str:
        text = self._location_text()
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
        self._sprinting = inputs.sprint
        self.controller.update(
            delta_time, inputs.forward, inputs.right, inputs.mouse_delta,
            sprint=inputs.sprint, jump=inputs.jump,
            crouch=inputs.crouch,
            zoom=inputs.zoom,
        )
        self._sync_transform()
        self.flashlight.update(self.camera, toggle=inputs.toggle_flashlight)
        self._interactions.update(delta_time, self.camera, inputs.interact)
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
        # Локальное направление вперёд у сущности -Z; наклон взгляда не наклоняет тело.
        self.transform = Transform(
            position=tuple(self.body.position),
            rotation=(0.0, (-self.controller.yaw_degrees - 90.0) % 360.0, 0.0),
        )


def create_player(level: Level, world: CollisionWorld3D) -> Player:
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
    return Player(body, camera, controller, model, level=level)
