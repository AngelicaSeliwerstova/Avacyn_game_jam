from dataclasses import dataclass
import math
from pathlib import Path

import moderngl

from engine.rendering.render_target import RenderTarget


@dataclass(frozen=True)
class PostProcessSettings:
    tint: tuple[float, float, float]
    strength: float
    saturation: float
    shadow_color: tuple[float, float, float]
    bloom_color: tuple[float, float, float]
    bloom_threshold: float
    bloom_strength: float
    bloom_radius: float
    downsample: int
    contrast: float = 1.0
    vignette: float = 0.0

    def __post_init__(self):
        for color in (self.tint, self.shadow_color, self.bloom_color):
            if len(color) != 3 or any(not math.isfinite(c) or c < 0 for c in color):
                raise ValueError("Postprocess colors need three finite nonnegative channels")
        for value in (self.strength, self.saturation, self.bloom_threshold):
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Tint strength, saturation and bloom threshold must be from 0 to 1")
        if not math.isfinite(self.bloom_strength) or self.bloom_strength < 0:
            raise ValueError("Bloom strength must be finite and nonnegative")
        if not math.isfinite(self.bloom_radius) or self.bloom_radius <= 0:
            raise ValueError("Bloom radius must be finite and positive")
        if not isinstance(self.downsample, int) or self.downsample not in (1, 2, 4, 8):
            raise ValueError("Bloom downsample must be 1, 2, 4 or 8")
        if not math.isfinite(self.contrast) or not 0 < self.contrast <= 2:
            raise ValueError("Contrast must be finite and from 0 (exclusive) to 2")
        if not math.isfinite(self.vignette) or not 0 <= self.vignette <= 1:
            raise ValueError("Vignette must be finite and from 0 to 1")


class PostProcessor:
    """Цветокоррекция, контраст, виньетка и bloom перед показом готового кадра."""

    def __init__(self, context: moderngl.Context, size: tuple[int, int], settings: PostProcessSettings):
        self._context = context
        self._settings = settings
        self._elapsed = 0.0
        self.output = None
        self._bloom_a = None
        self._bloom_b = None
        self._programs = {}
        self._vertices = {}
        try:
            self.output = RenderTarget(context, size, with_depth=False)
            small = tuple(max(1, (length + settings.downsample - 1) // settings.downsample) for length in size)
            self._bloom_a = RenderTarget(context, small, with_depth=False, dtype="f2")
            self._bloom_b = RenderTarget(context, small, with_depth=False, dtype="f2")
            for target in (self._bloom_a, self._bloom_b):
                target.color.filter = moderngl.LINEAR, moderngl.LINEAR
            shaders = Path(__file__).resolve().parent / "shaders"
            vertex_shader = (shaders / "present.vert").read_text(encoding="utf-8")
            for name in ("bloom_extract", "bloom_blur", "color_grade"):
                program = context.program(vertex_shader=vertex_shader,
                                          fragment_shader=(shaders / f"{name}.frag").read_text(encoding="utf-8"))
                self._programs[name] = program
                self._vertices[name] = context.vertex_array(program, [])
                program["scene_texture"].value = 0
            self._programs["bloom_extract"]["sample_span"].value = 1 / small[0], 1 / small[1]
            grade = self._programs["color_grade"]
            grade["bloom_texture"].value = 1
            self.set_settings(settings)
        except Exception:
            self.release()
            raise

    def set_settings(self, settings: PostProcessSettings):
        """Меняет пресет без пересоздания шейдеров и буферов кадра."""
        if settings.downsample != self._settings.downsample:
            raise ValueError("Changing bloom downsample requires recreating the postprocessor")
        grade = self._programs["color_grade"]
        for name, value in (("grade_tint", settings.tint), ("grade_strength", settings.strength),
                            ("saturation", settings.saturation), ("shadow_color", settings.shadow_color),
                            ("bloom_color", settings.bloom_color), ("bloom_strength", settings.bloom_strength),
                            ("contrast", settings.contrast), ("vignette", settings.vignette)):
            grade[name].value = value
        self._programs["bloom_extract"]["threshold"].value = settings.bloom_threshold
        self._settings = settings

    def update(self, delta_time: float):
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Postprocess delta time must be finite and nonnegative")
        self._elapsed += delta_time

    def _draw(self, name: str, target: RenderTarget):
        target.framebuffer.use()
        self._context.viewport = (0, 0, *target.size)
        self._vertices[name].render(mode=moderngl.TRIANGLES, vertices=3)

    def apply(self, source: moderngl.Texture, *, camera_effect_strength: float = 0.0,
              transition_strength: float = 0.0) -> RenderTarget:
        for value in (camera_effect_strength, transition_strength):
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Camera effect strengths must be finite and from 0 to 1")
        self._context.scissor = None
        self._context.disable(moderngl.DEPTH_TEST | moderngl.BLEND)
        source.use(location=0)
        self._draw("bloom_extract", self._bloom_a)
        blur = self._programs["bloom_blur"]
        radius = self._settings.bloom_radius
        blur["direction"].value = radius, 0.0
        self._bloom_a.color.use(location=0)
        self._draw("bloom_blur", self._bloom_b)
        blur["direction"].value = 0.0, radius
        self._bloom_b.color.use(location=0)
        self._draw("bloom_blur", self._bloom_a)
        source.use(location=0)
        self._bloom_a.color.use(location=1)
        grade = self._programs["color_grade"]
        grade["camera_effect_strength"].value = camera_effect_strength
        grade["transition_strength"].value = transition_strength
        grade["effect_time"].value = self._elapsed
        self._draw("color_grade", self.output)
        return self.output

    def release(self):
        for vertices in self._vertices.values():
            vertices.release()
        self._vertices.clear()
        for program in self._programs.values():
            program.release()
        self._programs.clear()
        for name in ("output", "_bloom_a", "_bloom_b"):
            target = getattr(self, name)
            if target is not None:
                target.release()
                setattr(self, name, None)
