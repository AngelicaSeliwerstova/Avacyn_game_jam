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
from engine.rendering.hud import AimOverlay, CreatorSidebarOverlay, HudStyle, TextOverlay
from engine.rendering.dialog import DialogOverlay
from engine.rendering.debug_lines import DebugLineRenderer
from engine.debug.geometry import DebugPath
from engine.rendering.postprocess import PostProcessor, PostProcessSettings
from engine.rendering.lighting import LevelLighting
from engine.rendering.dynamic_lighting import DynamicLighting
from engine.rendering.options import RenderOptions
from engine.rendering.fog import FogSettings, configure_fog
from engine.rendering.visibility import ViewFrustum, distance_to_box_squared
from engine.scene.box import Box
from engine.scene.camera import Camera
from engine.scene.level import Level
from engine.scene.lighting import SpotLight
from engine.scene.model import ModelComponent
from engine.scene.transform import Transform
from engine.scene.session import Dialog
from engine.rendering.gltf_model import GLTFModel


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
        debug_style: HudStyle | None = None,
        options: RenderOptions | None = None,
        fog: FogSettings | None = None,
        dynamic_lights: tuple[SpotLight, ...] = (),
        dynamic_shadow_resolution: int = 512,
        postprocess_presets: tuple[tuple[str, PostProcessSettings], ...] = (),
        player_model: ModelComponent | None = None,
    ):
        major, minor = opengl_version
        self.context = moderngl.create_context(require=major * 100 + minor * 10)
        self._program = None
        self._cube = None
        self._floor = None
        self._render_target = None
        self._presenter = None
        self._snow = None
        self._player_model = None
        self._hud = None
        self._debug_hud = None
        self._aim_hud = None
        self._creator_sidebar = None
        self._dialog = None
        self._debug_lines = None
        self._postprocess = None
        self._postprocess_presets = postprocess_presets
        self._postprocess_index = next((i for i, (_, style) in enumerate(postprocess_presets) if style == postprocess), -1)
        self._lighting = None
        self._dynamic_lighting = None
        self._floor_texture = None
        self._wall_texture = None
        self._fallback_texture = None
        self._textures = textures
        self._player_model_component = player_model
        self._texture_cache = {}
        self._materials = {}
        self._camera = camera
        self._level = level
        self._projection_settings = None
        self.options = options or RenderOptions()
        static_decorations = level.decorations
        if level.creator_objects:
            static_decorations = static_decorations[:-len(level.creator_objects)]
        self._static_objects = tuple((box, box.model_matrix.to_bytes(), box.bounds_half_size)
                                     for box in level.boxes + static_decorations)
        self._object_boxes = level.object_boxes
        self._camera_marker_boxes = ()
        self._camera_marker_objects = ()
        self._creator_object_boxes = ()
        self._creator_objects = ()
        self._objects = self._static_objects + self._prepare_objects(self._object_boxes)
        self._submitted_objects = len(self._objects)
        self._submitted_triangles = 0
        self._draw_calls = 0
        self._model_draw_calls = 0
        self._depth_draw_calls = 0

        try:
            # Pygame использует 0–255, OpenGL принимает цвет в диапазоне 0–1.
            self._background_color = tuple(channel / 255 for channel in background_color)
            if fog is not None:
                self._background_color = fog.color
            shader_dir = Path(__file__).resolve().parent / "shaders"
            self._program = self.context.program(
                vertex_shader=(shader_dir / "color.vert").read_text(encoding="utf-8"),
                fragment_shader=(shader_dir / "color.frag").read_text(encoding="utf-8").replace(
                    '#include "dynamic_lighting.glsl"',
                    (shader_dir / "dynamic_lighting.glsl").read_text(encoding="utf-8")),
            )
            configure_fog(self._program, fog)
            self._update_projection(render_size)
            self._program["surface_texture"].value = 0
            self._fallback_texture = self.context.texture((1, 1), 3, b"\xff\xff\xff")
            if player_model is not None and player_model.source_path is not None:
                if not player_model.source_path.is_file():
                    raise FileNotFoundError(f"Player model does not exist: {player_model.source_path}")
                self._player_model = GLTFModel(
                    self.context, self._program, player_model.source_path, self._fallback_texture,
                )
                self._program["skin_matrices"].value = 10
            if textures is not None:
                if textures.floor is not None:
                    self._floor_texture = self._load_texture(textures.floor)
                if textures.wall is not None:
                    self._wall_texture = self._load_texture(textures.wall)
                for material in textures.materials:
                    self._materials[material.name] = self._load_texture(material.path), material.world_size
                used_materials = {box.material for box in level.boxes + level.decorations + level.all_object_boxes} | {level.floor_material}
                unknown = used_materials - {None} - self._materials.keys()
                if unknown:
                    raise ValueError(f"Unknown materials in level: {sorted(unknown)}")
            self._cube = CubeMesh(self.context, self._program)
            self._floor = FloorMesh(
                self.context, self._program, level.floor_size, level.floor_tile_size,
                colors=level.floor_colors, height=level.base_height,
            )
            self._lighting = LevelLighting(self.context, self._program, level, self.options.light_cell_size)
            self._dynamic_lighting = DynamicLighting(self.context, self._program, dynamic_lights,
                                                      dynamic_shadow_resolution)
            self._render_target = RenderTarget(self.context, render_size)
            if postprocess is not None:
                self._postprocess = PostProcessor(self.context, render_size, postprocess)
            self._presenter = PixelPresenter(self.context)
            self._hud = TextOverlay(self.context, hud_style or HudStyle())
            self._debug_hud = TextOverlay(self.context, debug_style or HudStyle(font_size=16))
            self._aim_hud = AimOverlay(self.context, hud_style or HudStyle())
            self._creator_sidebar = CreatorSidebarOverlay(self.context, hud_style or HudStyle())
            self._dialog = DialogOverlay(self.context, hud_style or HudStyle())
            if snow is not None and snow.settings.count > 0:
                self._snow = SnowRenderer(self.context, snow, camera, render_size, fog=fog)
        except Exception:
            self.release()
            raise

    def update(self, delta_time: float, model_animation_speed: float = 1.0):
        """Продвигает время визуальных эффектов отдельно от повторной отрисовки."""
        self._lighting.update(delta_time, enabled=self.options.light_flicker)
        if self._player_model is not None:
            self._player_model.update(delta_time, speed=model_animation_speed)

    def set_camera_markers(self, boxes: tuple[Box, ...]):
        if boxes == self._camera_marker_boxes:
            return
        self._camera_marker_boxes = boxes
        self._camera_marker_objects = self._prepare_objects(boxes)
        self._rebuild_objects()

    def set_creator_objects(self, boxes: tuple[Box, ...]):
        if boxes == self._creator_object_boxes:
            return
        self._creator_object_boxes = boxes
        self._creator_objects = self._prepare_objects(boxes)
        self._rebuild_objects()

    def _rebuild_objects(self):
        self._objects = (self._static_objects + self._prepare_objects(self._object_boxes)
                         + self._creator_objects + self._camera_marker_objects)

    def cycle_postprocess(self):
        if self._postprocess is None or not self._postprocess_presets:
            return
        index = (self._postprocess_index + 1) % len(self._postprocess_presets)
        self._postprocess.set_settings(self._postprocess_presets[index][1])
        self._postprocess_index = index

    def render(self, window_size: tuple[int, int], hud_text: str = "", debug_text: str = "",
               *, aim_text: str | None = None, dialog: Dialog | None = None,
               debug_paths: tuple[DebugPath, ...] = (),
               player_transform: Transform | None = None,
               camera_markers: tuple[Box, ...] = (),
               creator_objects: tuple[Box, ...] = (),
               creator_help_text: tuple[str, str] | None = None):
        self.set_camera_markers(camera_markers)
        self.set_creator_objects(creator_objects)
        boxes = self._level.object_boxes
        if boxes != self._object_boxes:
            self._lighting.sync_objects(self._level.static_shadow_boxes)
            self._object_boxes = boxes
            self._rebuild_objects()
        self._dynamic_lighting.render_shadows(self._objects)
        self._render_target.framebuffer.use()
        self.context.viewport = (0, 0, *self._render_target.size)
        self.context.enable(moderngl.DEPTH_TEST)
        self.context.clear(*self._background_color, alpha=1.0, depth=1.0)
        self._update_projection(self._render_target.size)
        view = self._camera.view_matrix
        self._program["m_view"].write(view)
        self._program["camera_position"].value = tuple(self._camera.position)
        self._lighting.bind(self.options.local_lights)
        self._dynamic_lighting.bind()
        frustum = ViewFrustum(self._projection * view)
        objects = [item for item in self._objects if not self.options.frustum_culling
                   or frustum.intersects(item[0].position, item[2])]
        self._current_material = None
        self._program["use_uv"].value = False
        self._program["use_skinning"].value = False
        self._program["material_color_enabled"].value = False
        self._program["material_alpha_mode"].value = 0
        self._program["material_alpha"].value = 1.0
        self._program["material_alpha_cutoff"].value = 0.5
        draw_floor = not self.options.frustum_culling or frustum.intersects(
            (0, self._level.base_height, 0), (self._level.floor_size[0] / 2, 0, self._level.floor_size[1] / 2),
        )
        if self.options.depth_prepass:
            self._draw_depth(objects, draw_floor)
            self.context.depth_func = "<="
            self._render_target.framebuffer.depth_mask = False
            # При равной глубине сохраняем прежний приоритет копланарных поверхностей.
            objects.reverse()
        if draw_floor and not self.options.depth_prepass:
            self._draw_floor()
        try:
            for box, model, _ in objects:
                self._program["emission"].value = self._lighting.emission(box)
                self._program["object_color_enabled"].value = box.color is not None
                self._program["object_color"].value = box.color or (1.0, 1.0, 1.0)
                self._program["local_texture"].value = box.local_texture
                self._use_material(box.material, self._wall_texture,
                                   self._textures.wall_world_size if self._textures else 1.0)
                self._program["m_model"].write(model)
                self._cube.render()
            self._program["object_color_enabled"].value = False
            self._program["object_color"].value = (1.0, 1.0, 1.0)
            if draw_floor and self.options.depth_prepass:
                self._draw_floor()
            model_draw_calls = 0
            model_triangles = 0
            if self._player_model is not None and player_transform is not None:
                # The world depth prepass does not include the skinned character.
                self._render_target.framebuffer.depth_mask = True
                model_draw_calls, model_triangles = self._player_model.render(
                    self._player_model_component.world_matrix(player_transform),
                    self._camera.position,
                )
        finally:
            self._render_target.framebuffer.depth_mask = True
            self.context.depth_func = "<"
        self._submitted_objects = len(objects) + int(model_draw_calls > 0)
        self._draw_calls = len(objects) + int(draw_floor) + model_draw_calls
        self._model_draw_calls = model_draw_calls
        self._depth_draw_calls = (len(objects) + int(draw_floor)) if self.options.depth_prepass else 0
        self._submitted_triangles = len(objects) * self._cube.triangle_count + (
            self._floor.triangle_count if draw_floor else 0
        ) + model_triangles
        self._current_material = None
        if self._snow is not None:
            self._snow.render(self._camera)
        if self._postprocess is not None:
            self._postprocess.apply(self._render_target.color)
        target = self.output_target
        if dialog is None:
            if debug_paths:
                if self._debug_lines is None:
                    self._debug_lines = DebugLineRenderer(self.context)
                target.framebuffer.use()
                self.context.viewport = (0, 0, *target.size)
                self._debug_lines.draw(debug_paths, self._projection * view)
            self._hud.draw(hud_text, target.size)
            if aim_text is not None:
                self._aim_hud.draw(aim_text, target.size)
            self._debug_hud.draw(debug_text, target.size, anchor="bottom_right")
        else:
            self._dialog.draw(dialog, target.size, window_size)
        self._presenter.present(target.color, self.context.screen, window_size)
        if creator_help_text is not None and dialog is None:
            self._creator_sidebar.draw(window_size, target.size, creator_help_text)

    @property
    def output_target(self) -> RenderTarget:
        """Готовый кадр после эффектов и HUD, до масштабирования в окно."""
        return self._postprocess.output if self._postprocess is not None else self._render_target

    @staticmethod
    def _prepare_objects(boxes):
        return tuple((box, box.model_matrix.to_bytes(), box.bounds_half_size) for box in boxes)

    @property
    def debug_lines(self) -> tuple[str, ...]:
        lights = len(self._level.lighting.lights) if self._level.lighting is not None else 0
        particles = self._snow.particle_count if self._snow is not None else 0
        local = f" (local <= {self._lighting.grid.max_lights})" if (
            self.options.local_lights and self._lighting.grid is not None
        ) else ""
        look = (self._postprocess_presets[self._postprocess_index][0].upper()
                if self._postprocess_index >= 0 else "CUSTOM") if self._postprocess is not None else "OFF"
        return (f"SCENE: {self._submitted_triangles} tris | {self._draw_calls}/"
                f"{len(self._objects) + 1 + self._model_draw_calls} draws",
                f"ZPASS: {self._depth_draw_calls} | LIGHTS: {lights}{local}"
                f" | SPOT: {self._dynamic_lighting.active_count}",
                f"LOOK: {look} | F5: NEXT",
                *((f"SNOW: {particles}",) if particles else ()))

    def _draw_floor(self):
        self._program["local_texture"].value = False
        self._program["m_model"].write(glm.mat4(1.0))
        self._program["emission"].value = (0, 0, 0)
        self._use_material(self._level.floor_material, self._floor_texture,
                           self._textures.floor_world_size if self._textures else 1.0)
        self._floor.render()

    def _update_projection(self, render_size: tuple[int, int]):
        camera = self._camera
        state = (render_size, camera.fov_degrees, camera.near, camera.far)
        if state != self._projection_settings:
            self._projection = camera.projection_matrix(render_size[0] / render_size[1])
            self._program["m_projection"].write(self._projection)
            self._projection_settings = state

    def _draw_depth(self, objects, draw_floor):
        target = self._render_target.framebuffer
        target.color_mask = (False, False, False, False)
        self._program["depth_only"].value = True
        self._program["use_uv"].value = False
        self._program["use_skinning"].value = False
        try:
            position = tuple(self._camera.position)
            for _, model, _ in sorted(objects, key=lambda item: distance_to_box_squared(
                    position, item[0].position, item[2])):
                self._program["m_model"].write(model)
                self._cube.render()
            if draw_floor:
                self._program["m_model"].write(glm.mat4(1.0))
                self._floor.render()
        finally:
            target.color_mask = (True, True, True, True)
            self._program["depth_only"].value = False

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
        key = (texture, world_size)
        if key == self._current_material:
            return
        self._current_material = key
        self._program["textured"].value = texture is not None
        self._program["texture_world_size"].value = world_size
        if texture is None:
            self._fallback_texture.use(location=0)
        else:
            texture.use(location=0)

    def release(self):
        if self._debug_lines is not None:
            self._debug_lines.release()
            self._debug_lines = None
        if self._dialog is not None:
            self._dialog.release()
            self._dialog = None
        if self._dynamic_lighting is not None:
            self._dynamic_lighting.release()
            self._dynamic_lighting = None
        if self._aim_hud is not None:
            self._aim_hud.release()
            self._aim_hud = None
        if self._creator_sidebar is not None:
            self._creator_sidebar.release()
            self._creator_sidebar = None
        if self._debug_hud is not None:
            self._debug_hud.release()
            self._debug_hud = None
        if self._lighting is not None:
            self._lighting.release()
            self._lighting = None
        if self._postprocess is not None:
            self._postprocess.release()
            self._postprocess = None
        if self._hud is not None:
            self._hud.release()
            self._hud = None
        if self._player_model is not None:
            self._player_model.release()
            self._player_model = None
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
