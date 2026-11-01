import gc
from time import perf_counter
from collections.abc import Callable
from pathlib import Path

import pygame

from engine.core.window import Window
from engine.debug.panel import DebugSettings, DeveloperPanel
from engine.debug.geometry import DebugPath
from engine.debug.frame_log import SlowFrameLog
from engine.input.bindings import InputBindings
from engine.input.keyboard_mouse import KeyboardMouse
from engine.particles.snow import Snowfall
from engine.rendering.renderer import Renderer
from engine.rendering.hud import HudStyle
from engine.rendering.dialog import dialog_action_at
from engine.rendering.texture import TextureSettings
from engine.rendering.postprocess import PostProcessSettings
from engine.rendering.options import RenderOptions
from engine.rendering.fog import FogSettings
from engine.scene.entity import ControlledEntity, SimulationSystem
from engine.scene.level import Level
from engine.scene.lighting import SpotLight
from engine.scene.runtime import RuntimeScene
from engine.scene.session import Session
from engine.scene.inventory import InventoryView


class Application:
    """Соединяет системы движка и выполняет основной цикл."""

    def __init__(
        self,
        window_size: tuple[int, int],
        render_size: tuple[int, int],
        window_title: str,
        fps_limit: int,
        background_color: tuple[int, int, int],
        opengl_version: tuple[int, int],
        vsync: bool,
        controlled_entity: ControlledEntity,
        input_bindings: InputBindings,
        level: Level,
        snow: Snowfall | None = None,
        textures: TextureSettings | None = None,
        hud_style: HudStyle | None = None,
        postprocess: PostProcessSettings | None = None,
        debug: DebugSettings | None = None,
        render_options: RenderOptions | None = None,
        fog: FogSettings | None = None,
        dynamic_lights: tuple[SpotLight, ...] = (),
        dynamic_shadow_resolution: int = 512,
        systems: tuple[SimulationSystem, ...] = (),
        session: Session | None = None,
        debug_paths: Callable[[], tuple[DebugPath, ...]] | None = None,
        postprocess_presets: tuple[tuple[str, PostProcessSettings], ...] = (),
        scene_loader: Callable[[str], RuntimeScene] | None = None,
        debug_mode: bool = False,
    ):
        self._window_size = window_size
        self._render_size = render_size
        self._window_title = window_title
        self._fps_limit = fps_limit
        self._background_color = background_color
        self._opengl_version = opengl_version
        self._vsync = vsync
        self._controlled_entity = controlled_entity
        self._input_bindings = input_bindings
        self._level = level
        self._snow = snow
        self._textures = textures
        self._hud_style = hud_style
        self._postprocess = postprocess
        self._postprocess_presets = postprocess_presets
        self._debug_settings = debug or DebugSettings()
        self._debug = DeveloperPanel(self._debug_settings)
        self._debug_mode = debug_mode
        self._debug.enabled = debug_mode
        self._render_options = render_options
        self._fog = fog
        self._dynamic_lights = dynamic_lights
        self._dynamic_shadow_resolution = dynamic_shadow_resolution
        self._systems = systems
        self._session = session if session is not None else Session()
        self._debug_paths = debug_paths
        self._scene_loader = scene_loader
        self._result = "quit"
        self._running = False
        self._inventory_open = False
        self._inventory_page = 0

    def run(self):
        pygame.init()
        renderer = None
        input_device = None
        frame_log = None

        try:
            if self._debug_mode:
                frame_log = SlowFrameLog(Path(__file__).resolve().parents[2] / "logs")
                print(f"Performance log: {frame_log.path}")
            window = Window(
                size=self._window_size,
                title=self._window_title,
                opengl_version=self._opengl_version,
                vsync=self._vsync,
                minimum_size=self._render_size,
            )
            renderer = self._create_renderer()
            clock = pygame.time.Clock()
            input_device = KeyboardMouse(self._input_bindings)
            self._running = True

            while self._running:
                frame_started = perf_counter() if self._debug_mode else 0.0
                gc_before = (
                    tuple(generation["collections"] for generation in gc.get_stats())
                    if self._debug_mode else ()
                )
                # Clock возвращает миллисекунды, контроллер работает с секундами.
                delta_time = clock.tick(self._fps_limit) / 1000.0
                pacing_finished = perf_counter() if self._debug_mode else 0.0
                self._handle_events(input_device, window, renderer)
                if not self._running:
                    break

                if self._session.next_level is not None:
                    renderer = self._change_level(renderer, window)
                    input_device.reset_after_loading()
                    clock.tick()
                    continue

                inputs = input_device.read()
                profiling = self._debug_mode
                started = perf_counter() if profiling else 0.0
                system_timings = {}
                renderer.profile_enabled = profiling
                objects_updated = player_updated = systems_updated = animation_updated = started
                if not self._simulation_paused:
                    creator_was_active = getattr(self._controlled_entity, "creator_mode", False)
                    creator_is_being_toggled = (
                        inputs.toggle_camera_editor
                        and getattr(self._controlled_entity, "creator_mode_available", False)
                    )
                    if not creator_was_active and not creator_is_being_toggled:
                        for obj in self._level.objects:
                            obj.update(delta_time)
                    objects_updated = perf_counter() if profiling else 0.0
                    self._controlled_entity.update(delta_time, inputs)
                    if (inputs.recalculate_shadows
                            and getattr(self._controlled_entity, "creator_mode", False)):
                        renderer.recalculate_shadows()
                    player_updated = perf_counter() if profiling else 0.0
                    if not creator_was_active and not creator_is_being_toggled:
                        for index, system in enumerate(self._systems):
                            system_started = perf_counter() if profiling else 0.0
                            system.update(delta_time)
                            if profiling:
                                system_timings[
                                    f"system_{index}_{type(system).__name__}"
                                ] = perf_counter() - system_started
                            if self._session.next_level is not None:
                                break
                            if self._session.dialog is not None:
                                input_device.release()
                                break
                    systems_updated = perf_counter() if profiling else 0.0
                    if self._session.dialog is None:
                        if self._snow is not None and not getattr(
                            self._controlled_entity, "creator_mode", False,
                        ):
                            self._snow.update(delta_time)
                        renderer.update(
                            delta_time,
                            model_animation_speed=getattr(
                                self._controlled_entity, "model_animation_speed", 1.0,
                            ),
                        )
                    animation_updated = perf_counter() if profiling else 0.0
                if self._session.next_level is not None:
                    renderer = self._change_level(renderer, window)
                    input_device.reset_after_loading()
                    # Loading time must not become the next physics step.
                    clock.tick()
                    continue
                for system in self._systems:
                    pause = getattr(system, "set_paused", None)
                    if pause is not None:
                        pause(self._simulation_paused or getattr(self._controlled_entity, "creator_mode", False))
                updated = perf_counter() if profiling else 0.0
                renderer.render(window.size, hud_text=self._controlled_entity.status_text,
                                debug_text=self._debug.text, aim_text=self._controlled_entity.aim_text,
                                dialog=self._session.dialog,
                                inventory=self._inventory_view(),
                                camera_markers=getattr(self._controlled_entity, "camera_marker_boxes", ()),
                                creator_objects=getattr(self._controlled_entity, "creator_object_boxes", ()),
                                creator_lights=getattr(self._controlled_entity, "creator_lights", ()),
                                creator_light_boxes=getattr(
                                    self._controlled_entity, "creator_light_boxes", (),
                                ),
                                creator_help_text=getattr(
                                    self._controlled_entity, "creator_help_text", None,
                                ),
                                camera_effect_strength=(
                                    1.0 if getattr(
                                        self._controlled_entity, "fixed_camera_effect_active", False,
                                    ) else 0.0
                                ),
                                camera_transition_strength=getattr(
                                    self._controlled_entity, "camera_transition_strength", 0.0,
                                ),
                                player_transform=self._controlled_entity.transform,
                                debug_paths=self._debug_paths() if self._debug.enabled and self._debug_paths else ())
                rendered = perf_counter() if profiling else 0.0
                window.present()
                if frame_log is not None:
                    presented = perf_counter()
                    frame_log.record(presented - frame_started, {
                        "frame_pacing": pacing_finished - frame_started,
                        "events_input": started - pacing_finished,
                        "objects_doors": objects_updated - started,
                        "player_camera_collision": player_updated - objects_updated,
                        "systems_actors_session": systems_updated - player_updated,
                        **system_timings,
                        "animation_particles": animation_updated - systems_updated,
                        **renderer.frame_timings,
                        "present": presented - rendered,
                    }, lambda: {"scene": self._level.visual_style,
                                "delta_time_s": round(delta_time, 4),
                                "update_total_ms": round((updated - started) * 1000, 3),
                                "render_total_ms": round((rendered - updated) * 1000, 3),
                                "level_counts": {
                                    "collision_boxes": len(self._level.collision_boxes),
                                    "objects": len(self._level.objects),
                                    "render_boxes": len(self._level.object_boxes),
                                },
                                "gc_collections": [
                                    after - before for before, after in zip(
                                        gc_before,
                                        (generation["collections"] for generation in gc.get_stats()),
                                    )
                                ],
                                "position": tuple(self._controlled_entity.transform.position),
                                "camera": tuple(self._controlled_entity.camera.position),
                                "paused": self._simulation_paused,
                                "creator": getattr(self._controlled_entity, "creator_mode", False),
                                "details": self._debug_lines(renderer, input_device, window)})
                self._debug.update(delta_time, updated - started, rendered - updated,
                                   lambda: self._debug_lines(renderer, input_device, window))
        finally:
            for system in self._systems:
                release = getattr(system, "release", None)
                if release is not None:
                    release()
            if frame_log is not None:
                frame_log.close()
            self._running = False
            # GPU-ресурсы освобождаем, пока OpenGL-окно ещё существует.
            try:
                try:
                    if input_device is not None:
                        input_device.release()
                finally:
                    if renderer is not None:
                        renderer.release()
            finally:
                pygame.quit()
        return self._result

    def _create_renderer(self, context=None):
        return Renderer(
            render_size=self._render_size,
            background_color=self._background_color,
            opengl_version=self._opengl_version,
            camera=self._controlled_entity.camera,
            level=self._level,
            snow=self._snow,
            textures=self._textures,
            hud_style=self._hud_style,
            postprocess=self._postprocess,
            postprocess_presets=self._postprocess_presets,
            debug_style=HudStyle(self._debug_settings.font_size, self._debug_settings.margin,
                                 font_path=self._debug_settings.font_path,
                                 antialias=self._debug_settings.antialias),
            options=self._render_options,
            fog=self._fog,
            dynamic_lights=self._dynamic_lights,
            dynamic_shadow_resolution=self._dynamic_shadow_resolution,
            player_model=self._controlled_entity.model,
            context=context,
        )

    def _change_level(self, renderer: Renderer, window: Window) -> Renderer:
        if self._scene_loader is None:
            raise RuntimeError("A level transition requires a scene loader")
        for system in self._systems:
            release = getattr(system, "release", None)
            if release is not None:
                release()
        # Keep the existing SDL window and context, showing black during loading.
        renderer.context.screen.use()
        renderer.context.viewport = (0, 0, *window.size)
        renderer.context.clear(0, 0, 0, 1)
        window.present()
        scene = self._scene_loader(self._session.next_level)
        context = renderer.context
        renderer.release(release_context=False)
        self._level = scene.level
        self._controlled_entity = scene.player
        self._session = scene.session
        self._systems = scene.systems
        self._snow = scene.snow
        self._debug_paths = scene.debug_paths
        self._dynamic_lights = scene.player.dynamic_lights
        self._fog = scene.fog
        self._postprocess = scene.postprocess
        self._inventory_open = False
        self._inventory_page = 0
        return self._create_renderer(context=context)

    @property
    def _simulation_paused(self):
        return self._session.dialog is not None or self._inventory_open

    def _inventory_view(self):
        if not self._inventory_open:
            return None
        key = self._input_bindings.toggle_inventory
        label = pygame.key.name(key).title() if key is not None else "Tab"
        view = InventoryView(tuple(self._controlled_entity.inventory.items), self._inventory_page, label)
        self._inventory_page = max(0, min(view.page_count - 1, self._inventory_page))
        return InventoryView(view.items, self._inventory_page, label)

    def _close_inventory(self, input_device):
        self._inventory_open = False
        input_device.end_modal()

    def _handle_events(self, input_device: KeyboardMouse, window: Window, renderer: Renderer | None = None):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
                break
            elif (event.type == pygame.KEYDOWN and event.key == self._input_bindings.toggle_debug
                  and self._debug_mode and not getattr(event, "repeat", False)):
                self._debug.toggle()
            elif (event.type == pygame.KEYDOWN and event.key == self._input_bindings.cycle_postprocess
                  and renderer is not None and not self._simulation_paused and not getattr(event, "repeat", False)):
                renderer.cycle_postprocess()
            elif event.type == pygame.KEYDOWN and event.key == self._input_bindings.toggle_fullscreen:
                input_device.release()
                window.toggle_fullscreen()
            window.handle_event(event)
            if self._session.dialog is None:
                if (event.type == pygame.KEYDOWN and event.key == self._input_bindings.toggle_inventory
                        and not getattr(event, "repeat", False)):
                    if self._inventory_open:
                        self._close_inventory(input_device)
                    elif getattr(self._controlled_entity, "inventory", None) is not None:
                        self._inventory_open = True
                        self._inventory_page = 0
                        input_device.begin_modal()
                    continue
                if self._inventory_open:
                    if event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWFOCUSGAINED):
                        input_device.handle_event(event)
                    elif event.type == pygame.KEYDOWN and not getattr(event, "repeat", False):
                        if event.key in (pygame.K_ESCAPE, self._input_bindings.release_mouse):
                            self._close_inventory(input_device)
                        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                            self._inventory_page += 1 if event.key == pygame.K_RIGHT else -1
                    elif event.type == pygame.MOUSEWHEEL:
                        self._inventory_page -= event.y
                    continue
            if self._session.dialog is not None:
                action = None
                if event.type == pygame.KEYDOWN and not getattr(event, "repeat", False):
                    key = pygame.key.name(event.key)
                    action = next((button.action for button in self._session.dialog.buttons if key in button.keys), None)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    action = dialog_action_at(self._session.dialog, event.pos, window.size, self._render_size)
                if action is not None:
                    if self._session.handle_action(action):
                        if self._session.dialog is None:
                            input_device.reset_after_loading()
                        continue
                    self._result = action
                    self._running = False
                    break
            else:
                input_device.handle_event(event)

    def _debug_lines(self, renderer: Renderer, input_device: KeyboardMouse, window: Window) -> tuple[str, ...]:
        rw, rh = self._render_size
        ww, wh = window.size
        return (
            f"SIM: {'PAUSED' if self._simulation_paused else 'RUNNING'} | INPUT: {input_device.status_text}",
            *self._controlled_entity.debug_lines,
            *renderer.debug_lines,
            f"VIEW: {rw}x{rh} -> {ww}x{wh}",
            f"VSYNC: {'ON' if self._vsync else 'OFF'} | CAP: {self._fps_limit or 'OFF'}",
        )
