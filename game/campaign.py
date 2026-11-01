from dataclasses import dataclass, field, replace
import math

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.particles.snow import Snowfall, SnowSettings
from engine.scene.runtime import RuntimeScene
from game.entities.player import create_player
from game.entities.companion import Companion
from game.enemies import EnemySystem
from game.companions import CompanionSystem
from game.footsteps import FootstepSystem
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
    def __init__(self, creator_mode: bool = False, *, puzzle_store=None):
        from game.puzzles.cctv_puzzle import CCTVProgressStore
        self.puzzle_store = CCTVProgressStore() if puzzle_store is None else puzzle_store
        self.progress = CampaignProgress()
        self.creator_mode = creator_mode
        self._scene: RuntimeScene | None = None

    def load_level(self, name: str) -> RuntimeScene:
        level = create_level(name)
        for obj in level.objects:
            action = obj.states["default"].interaction
            if action and action.command == "pickup_key" and self.progress.inventory.has_key(action.argument):
                obj.set_state("collected")
        previous = self._scene
        transforming = (previous is not None and level.story is not None
                        and previous.level.story == level.story
                        and getattr(previous.session, "preserve_scene_on_transition", False))
        if transforming:
            old_player = previous.player
            eye = tuple(old_player.body.eye_position(settings.PLAYER_EYE_HEIGHT))
            yaw = math.radians(old_player.controller.yaw_degrees)
            level = replace(level, spawn_position=eye,
                            spawn_target=(eye[0] + math.cos(yaw), eye[1], eye[2] + math.sin(yaw)))
            old_objects = {obj.name: obj for obj in previous.level.objects}
            for obj in level.objects:
                old = old_objects.get(obj.name)
                if old is None:
                    continue
                if isinstance(obj.entity, Companion):
                    obj.entity.transform = replace(old.entity.transform, position=tuple(old.entity.body.position))
                    obj.entity._yaw = old.entity._yaw
                    obj.set_geometry(obj.entity._geometry())
                elif old.state_name in obj.states:
                    obj.set_state(old.state_name)
                    obj.update(10)
        world = CollisionWorld3D(
            colliders=(box.collider for box in level.collision_boxes),
            bounds=level.floor_bounds, ground_height=level.base_height,
            objects=tuple(obj for obj in level.objects if not isinstance(obj.entity, Companion)),
        )
        player = create_player(level, world, creator_mode=self.creator_mode,
                               inventory=self.progress.inventory)
        if self._scene is not None:
            player.flashlight.light.enabled = self._scene.player.flashlight.light.enabled
        if level.story is not None and not self.creator_mode:
            from game.story import StorySession
            from game.story_loader import load_story
            session = StorySession(level, player, self.progress.flags, load_story(level.story), name,
                                   puzzle_store=self.puzzle_store)
        else:
            session = GameSession(level, player, flags=self.progress.flags)
        enemies = EnemySystem(level, player, on_caught=session.lose)
        companions = CompanionSystem(level, player)
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
        footsteps = FootstepSystem(level, player)
        from game.levels.story_props import StoryPropSystem
        props = StoryPropSystem(level)
        audio = ()
        if level.audio_profile is not None:
            from game.hospital_audio import HospitalAudioSystem
            audio = (HospitalAudioSystem(level, player, session),)
        scene = RuntimeScene(level, player, session, (companions, enemies, props, footsteps, *audio, session), snow,
                             lambda: enemies.debug_paths() + companions.debug_paths(),
                             fog=fog, postprocess=postprocess)
        if self.progress.current_level is not None:
            self.progress.completed_levels.add(self.progress.current_level)
        self.progress.current_level = name
        self._scene = scene
        return scene
