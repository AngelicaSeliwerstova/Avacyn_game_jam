import pygame
from time import perf_counter
from collections.abc import Callable

from engine.core.window import Window
from engine.debug.panel import DebugSettings, DeveloperPanel
from engine.debug.geometry import DebugPath
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
from engine.scene.session import Session


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
        self._render_options = render_options
        self._fog = fog
        self._dynamic_lights = dynamic_lights
        self._dynamic_shadow_resolution = dynamic_shadow_resolution
        self._systems = systems
        self._session = session if session is not None else Session()
        self._debug_paths = debug_paths
        self._result = "quit"
        self._running = False

    def run(self):
        pygame.init()
        renderer = None
        input_device = None

        try:
            window = Window(
                size=self._window_size,
                title=self._window_title,
                opengl_version=self._opengl_version,
                vsync=self._vsync,
                minimum_size=self._render_size,
            )
            renderer = Renderer(
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
            )
            clock = pygame.time.Clock()
            input_device = KeyboardMouse(self._input_bindings)
            self._running = True

            while self._running:
                # Clock возвращает миллисекунды, контроллер работает с секундами.
                delta_time = clock.tick(self._fps_limit) / 1000.0
                self._handle_events(input_device, window, renderer)
                if not self._running:
                    break

                inputs = input_device.read()
                profiling = self._debug.enabled
                started = perf_counter() if profiling else 0.0
                if self._session.dialog is None:
                    for obj in self._level.objects:
                        obj.update(delta_time)
                    self._controlled_entity.update(delta_time, inputs)
                    for system in self._systems:
                        system.update(delta_time)
                        if self._session.dialog is not None:
                            input_device.release()
                            break
                    if self._session.dialog is None:
                        if self._snow is not None:
                            self._snow.update(delta_time)
                        renderer.update(
                            delta_time,
                            model_animation_speed=getattr(
                                self._controlled_entity, "model_animation_speed", 1.0,
                            ),
                        )
                updated = perf_counter() if profiling else 0.0
                renderer.render(window.size, hud_text=self._controlled_entity.status_text,
                                debug_text=self._debug.text, aim_text=self._controlled_entity.aim_text,
                                dialog=self._session.dialog,
                                player_transform=self._controlled_entity.transform,
                                debug_paths=self._debug_paths() if self._debug.enabled and self._debug_paths else ())
                rendered = perf_counter() if profiling else 0.0
                window.present()
                self._debug.update(delta_time, updated - started, rendered - updated,
                                   lambda: self._debug_lines(renderer, input_device, window))
        finally:
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

    def _handle_events(self, input_device: KeyboardMouse, window: Window, renderer: Renderer | None = None):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
                break
            elif (event.type == pygame.KEYDOWN and event.key == self._input_bindings.toggle_debug
                  and not getattr(event, "repeat", False)):
                self._debug.toggle()
            elif (event.type == pygame.KEYDOWN and event.key == self._input_bindings.cycle_postprocess
                  and renderer is not None and self._session.dialog is None and not getattr(event, "repeat", False)):
                renderer.cycle_postprocess()
            elif event.type == pygame.KEYDOWN and event.key == self._input_bindings.toggle_fullscreen:
                input_device.release()
                window.toggle_fullscreen()
            window.handle_event(event)
            if self._session.dialog is not None:
                action = None
                if event.type == pygame.KEYDOWN and not getattr(event, "repeat", False):
                    key = pygame.key.name(event.key)
                    action = next((button.action for button in self._session.dialog.buttons if key in button.keys), None)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    action = dialog_action_at(self._session.dialog, event.pos, window.size, self._render_size)
                if action is not None:
                    self._result = action
                    self._running = False
                    break
            else:
                input_device.handle_event(event)

    def _debug_lines(self, renderer: Renderer, input_device: KeyboardMouse, window: Window) -> tuple[str, ...]:
        rw, rh = self._render_size
        ww, wh = window.size
        return (
            f"SIM: {'PAUSED' if self._session.dialog is not None else 'RUNNING'} | INPUT: {input_device.status_text}",
            *self._controlled_entity.debug_lines,
            *renderer.debug_lines,
            f"VIEW: {rw}x{rh} -> {ww}x{wh}",
            f"VSYNC: {'ON' if self._vsync else 'OFF'} | CAP: {self._fps_limit or 'OFF'}",
        )
