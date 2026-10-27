import pygame
from time import perf_counter

from engine.core.window import Window
from engine.debug.panel import DebugSettings, DeveloperPanel
from engine.input.bindings import InputBindings
from engine.input.keyboard_mouse import KeyboardMouse
from engine.particles.snow import Snowfall
from engine.rendering.renderer import Renderer
from engine.rendering.hud import HudStyle
from engine.rendering.texture import TextureSettings
from engine.rendering.postprocess import PostProcessSettings
from engine.rendering.options import RenderOptions
from engine.rendering.fog import FogSettings
from engine.scene.entity import ControlledEntity
from engine.scene.level import Level
from engine.scene.lighting import SpotLight


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
        self._debug_settings = debug or DebugSettings()
        self._debug = DeveloperPanel(self._debug_settings)
        self._render_options = render_options
        self._fog = fog
        self._dynamic_lights = dynamic_lights
        self._dynamic_shadow_resolution = dynamic_shadow_resolution
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
                debug_style=HudStyle(self._debug_settings.font_size, self._debug_settings.margin,
                                     font_path=self._debug_settings.font_path,
                                     antialias=self._debug_settings.antialias),
                options=self._render_options,
                fog=self._fog,
                dynamic_lights=self._dynamic_lights,
                dynamic_shadow_resolution=self._dynamic_shadow_resolution,
            )
            clock = pygame.time.Clock()
            input_device = KeyboardMouse(self._input_bindings)
            self._running = True

            while self._running:
                # Clock возвращает миллисекунды, контроллер работает с секундами.
                delta_time = clock.tick(self._fps_limit) / 1000.0
                self._handle_events(input_device, window)
                if not self._running:
                    break

                inputs = input_device.read()
                profiling = self._debug.enabled
                started = perf_counter() if profiling else 0.0
                self._controlled_entity.update(delta_time, inputs)
                if self._snow is not None:
                    self._snow.update(delta_time)
                renderer.update(delta_time)
                updated = perf_counter() if profiling else 0.0
                renderer.render(window.size, hud_text=self._controlled_entity.status_text,
                                debug_text=self._debug.text, aim_text=self._controlled_entity.aim_text)
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

    def _handle_events(self, input_device: KeyboardMouse, window: Window):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
            elif (event.type == pygame.KEYDOWN and event.key == self._input_bindings.toggle_debug
                  and not getattr(event, "repeat", False)):
                self._debug.toggle()
            elif event.type == pygame.KEYDOWN and event.key == self._input_bindings.toggle_fullscreen:
                input_device.release()
                window.toggle_fullscreen()
            window.handle_event(event)
            input_device.handle_event(event)

    def _debug_lines(self, renderer: Renderer, input_device: KeyboardMouse, window: Window) -> tuple[str, ...]:
        rw, rh = self._render_size
        ww, wh = window.size
        return (
            f"SIM: RUNNING | INPUT: {input_device.status_text}",
            *self._controlled_entity.debug_lines,
            *renderer.debug_lines,
            f"VIEW: {rw}x{rh} -> {ww}x{wh}",
            f"VSYNC: {'ON' if self._vsync else 'OFF'} | CAP: {self._fps_limit or 'OFF'}",
        )
