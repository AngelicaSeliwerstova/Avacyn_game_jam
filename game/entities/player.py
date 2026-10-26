from pathlib import Path

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.controllers.first_person import FirstPersonController
from engine.input.state import InputState
from engine.physics.character import CharacterBody
from engine.scene.camera import Camera
from engine.scene.entity import Entity
from engine.scene.level import Level
from engine.scene.model import ModelComponent
from engine.scene.transform import Transform


class Player(Entity):
    """Персонаж объединяет тело, управление, камеру и место для своей модели."""

    def __init__(self, body: CharacterBody, camera: Camera,
                 controller: FirstPersonController, model: ModelComponent):
        super().__init__(name="player", model=model)
        self.body = body
        self.camera = camera
        self.controller = controller
        self._sync_transform()

    def update(self, delta_time: float, inputs: InputState) -> None:
        self.controller.update(
            delta_time, inputs.forward, inputs.right, inputs.mouse_delta,
            sprint=inputs.sprint, jump=inputs.jump,
        )
        self._sync_transform()

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
    )
    camera = Camera(
        position=level.spawn_position, target=level.spawn_target,
        fov_degrees=settings.CAMERA_FOV_DEGREES, near=settings.CAMERA_NEAR, far=settings.CAMERA_FAR,
    )
    controller = FirstPersonController(
        camera=camera, body=body, eye_height=settings.PLAYER_EYE_HEIGHT,
        move_speed=settings.MOVE_SPEED, sprint_speed=settings.SPRINT_SPEED,
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
    return Player(body, camera, controller, model)
