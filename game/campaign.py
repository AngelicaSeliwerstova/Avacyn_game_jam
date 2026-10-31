from dataclasses import dataclass, field

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.particles.snow import Snowfall, SnowSettings
from engine.scene.runtime import RuntimeScene
from game.entities.player import create_player
from game.enemies import EnemySystem
from game.inventory import Inventory
from game.levels import create_level
from game.session import GameSession
from game.effects import create_scene_effects


@dataclass
class CampaignProgress:
    """Состояние прохождения в памяти; новая игра создаёт новый экземпляр."""

    inventory: Inventory = field(default_factory=Inventory)
    flags: set[str] = field(default_factory=set)
    completed_levels: set[str] = field(default_factory=set)
    current_level: str | None = None


class Campaign:
    def __init__(self, creator_mode: bool = False):
        self.progress = CampaignProgress()
        self.creator_mode = creator_mode
        self._scene: RuntimeScene | None = None

    def load_level(self, name: str) -> RuntimeScene:
        level = create_level(name)
        world = CollisionWorld3D(
            colliders=(box.collider for box in level.collision_boxes),
            bounds=level.floor_bounds, ground_height=level.base_height,
            objects=level.objects,
        )
        player = create_player(level, world, creator_mode=self.creator_mode,
                               inventory=self.progress.inventory)
        if self._scene is not None:
            player.flashlight.light.enabled = self._scene.player.flashlight.light.enabled
        session = GameSession(level, player)
        enemies = EnemySystem(level, player, on_caught=session.lose)
        snow = None
        if settings.SNOW_ENABLED and level.snow_enabled:
            snow = Snowfall(
                settings=SnowSettings(
                    count=settings.SNOW_COUNT, height=settings.SNOW_HEIGHT,
                    fall_speed=settings.SNOW_FALL_SPEED, flake_size=settings.SNOW_FLAKE_SIZE,
                    color=settings.SNOW_COLOR, seed=settings.SNOW_SEED,
                ),
                bounds=level.floor_bounds,
                obstacles=tuple(box.footprint for box in level.boxes),
            )
        fog, postprocess = create_scene_effects(level.visual_style)
        scene = RuntimeScene(level, player, session, (enemies, session), snow,
                             enemies.debug_paths, fog=fog, postprocess=postprocess)
        if self.progress.current_level is not None:
            self.progress.completed_levels.add(self.progress.current_level)
        self.progress.current_level = name
        self._scene = scene
        return scene
