from pathlib import Path

import moderngl
import glm

from engine.particles.snow import Snowfall
from engine.rendering.meshes.cube import CubeMesh
from engine.rendering.meshes.floor import FloorMesh
from engine.rendering.presentation import PixelPresenter
from engine.rendering.render_target import RenderTarget
from engine.rendering.snow import SnowRenderer
from engine.rendering.texture import Texture2D, TextureSettings
from engine.rendering.hud import HudStyle, TextOverlay
from engine.rendering.postprocess import PostProcessor, PostProcessSettings
from engine.scene.camera import Camera
from engine.scene.level import Level


class Renderer:
    """Управляет OpenGL-ресурсами и рисует содержимое кадра."""

    def __init__(
        self,
        render_size: tuple[int, int],
        background_color: tuple[int, int, int],
        opengl_version: tuple[int, int],
        camera: Camera,
        level: Level,
        snow: Snowfall | None = None,
        textures: TextureSettings | None = None,
        hud_style: HudStyle | None = None,
        postprocess: PostProcessSettings | None = None,
    ):
        major, minor = opengl_version
        self.context = moderngl.create_context(require=major * 100 + minor * 10)
        self._program = None
        self._cube = None
        self._floor = None
        self._render_target = None
        self._presenter = None
        self._snow = None
        self._hud = None
        self._postprocess = None
        self._floor_texture = None
        self._wall_texture = None
        self._fallback_texture = None
        self._textures = textures
        self._texture_cache = {}
        self._materials = {}
        self._camera = camera
        self._level = level

        try:
            # Pygame использует 0–255, OpenGL принимает цвет в диапазоне 0–1.
            self._background_color = tuple(channel / 255 for channel in background_color)
            shader_dir = Path(__file__).resolve().parent / "shaders"
            self._program = self.context.program(
                vertex_shader=(shader_dir / "color.vert").read_text(encoding="utf-8"),
                fragment_shader=(shader_dir / "color.frag").read_text(encoding="utf-8"),
            )
            width, height = render_size
            self._program["m_projection"].write(camera.projection_matrix(width / height))
            self._program["surface_texture"].value = 0
            self._fallback_texture = self.context.texture((1, 1), 3, b"\xff\xff\xff")
            if textures is not None:
                if textures.floor is not None:
                    self._floor_texture = self._load_texture(textures.floor)
                if textures.wall is not None:
                    self._wall_texture = self._load_texture(textures.wall)
                for material in textures.materials:
                    self._materials[material.name] = self._load_texture(material.path), material.world_size
                used_materials = {box.material for box in level.boxes} | {level.floor_material}
                unknown = used_materials - {None} - self._materials.keys()
                if unknown:
                    raise ValueError(f"Unknown materials in level: {sorted(unknown)}")
            self._cube = CubeMesh(self.context, self._program)
            self._floor = FloorMesh(
                self.context, self._program, level.floor_size, level.floor_tile_size,
                colors=level.floor_colors,
            )
            self._render_target = RenderTarget(self.context, render_size)
            if postprocess is not None:
                self._postprocess = PostProcessor(self.context, render_size, postprocess)
            self._presenter = PixelPresenter(self.context)
            self._hud = TextOverlay(self.context, hud_style or HudStyle())
            if snow is not None and snow.settings.count > 0:
                self._snow = SnowRenderer(self.context, snow, camera, render_size)
        except Exception:
            self.release()
            raise

    def render(self, window_size: tuple[int, int], hud_text: str = ""):
        self._render_target.framebuffer.use()
        self.context.viewport = (0, 0, *self._render_target.size)
        self.context.enable(moderngl.DEPTH_TEST)
        self.context.clear(*self._background_color, alpha=1.0, depth=1.0)
        self._program["m_view"].write(self._camera.view_matrix)
        self._program["m_model"].write(glm.mat4(1.0))
        self._use_material(self._level.floor_material, self._floor_texture,
                           self._textures.floor_world_size if self._textures else 1.0)
        self._floor.render()
        for box in self._level.boxes:
            self._use_material(box.material, self._wall_texture,
                               self._textures.wall_world_size if self._textures else 1.0)
            self._program["m_model"].write(box.model_matrix)
            self._cube.render()
        if self._snow is not None:
            self._snow.render(self._camera)
        if self._postprocess is not None:
            self._postprocess.apply(self._render_target.color)
        target = self.output_target
        self._hud.draw(hud_text, target.size)
        self._presenter.present(target.color, self.context.screen, window_size)

    @property
    def output_target(self) -> RenderTarget:
        """Готовый кадр после эффектов и HUD, до масштабирования в окно."""
        return self._postprocess.output if self._postprocess is not None else self._render_target

    def _load_texture(self, path: Path) -> Texture2D:
        key = Path(path).resolve()
        if key not in self._texture_cache:
            self._texture_cache[key] = Texture2D(
                self.context, key, self._textures.mipmaps, self._textures.anisotropy,
            )
        return self._texture_cache[key]

    def _use_material(self, name: str | None, texture: Texture2D | None, world_size: float):
        if texture is not None and name is not None:
            texture, world_size = self._materials[name]
        self._program["textured"].value = texture is not None
        self._program["texture_world_size"].value = world_size
        if texture is None:
            self._fallback_texture.use(location=0)
        else:
            texture.use(location=0)

    def release(self):
        if self._postprocess is not None:
            self._postprocess.release()
            self._postprocess = None
        if self._hud is not None:
            self._hud.release()
            self._hud = None
        for texture in self._texture_cache.values():
            texture.release()
        self._texture_cache.clear()
        self._materials.clear()
        self._floor_texture = None
        self._wall_texture = None
        if self._fallback_texture is not None:
            self._fallback_texture.release()
            self._fallback_texture = None
        if self._snow is not None:
            self._snow.release()
            self._snow = None
        if self._presenter is not None:
            self._presenter.release()
            self._presenter = None
        if self._render_target is not None:
            self._render_target.release()
            self._render_target = None
        if self._floor is not None:
            self._floor.release()
            self._floor = None
        if self._cube is not None:
            self._cube.release()
            self._cube = None
        if self._program is not None:
            self._program.release()
            self._program = None
        if self.context is not None:
            self.context.release()
            self.context = None
