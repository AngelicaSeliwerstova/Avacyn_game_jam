from array import array
import math
from pathlib import Path

import glm
import moderngl

from engine.rendering.meshes.cube import CubeMesh
from engine.rendering.light_grid import build_light_grid
from engine.rendering.visibility import distance_to_box_squared
from engine.scene.level import Level


SHADOW_NEAR = 0.05
ATLAS_COLUMNS = 8
FACE_VIEWS = (
    ((1, 0, 0), (0, -1, 0)), ((-1, 0, 0), (0, -1, 0)),
    ((0, 1, 0), (0, 0, 1)), ((0, -1, 0), (0, 0, -1)),
    ((0, 0, 1), (0, -1, 0)), ((0, 0, -1), (0, -1, 0)),
)


class LevelLighting:
    """Запекание статических теней, локальное обновление геометрии и мерцание."""

    def __init__(self, context: moderngl.Context, program: moderngl.Program, level: Level,
                 cell_size: float = 4.0, extra_shadow_boxes=()):
        self._context = context
        self._scene_program = program
        self._grid_texture = None
        self._light_data = None
        self.grid = None
        self._texture = None
        self._framebuffer = None
        self._program = None
        self._cube = None
        self._elapsed = 0.0
        self._animated = ()
        self._scales = []
        self._level = level
        self._object_boxes = level.static_shadow_boxes
        static_decorations = level.decorations
        if level.creator_objects:
            static_decorations = static_decorations[:-len(level.creator_objects)]
        self._static_geometry = tuple((box, box.model_matrix.to_bytes(), box.bounds_half_size)
                                      for box in level.boxes + static_decorations)
        lighting = level.lighting
        program["lighting_enabled"].value = lighting is not None
        program["shadow_atlas"].value = 2
        program["local_light_grid"].value = 3
        program["light_data"].value = 4
        program["use_light_grid"].value = False
        if lighting is None:
            return
        try:
            program["ambient_light"].value = lighting.ambient
            program["light_count"].value = len(lighting.lights)
            positions, colors = array("f"), array("f")
            for light in lighting.lights:
                positions.extend((*light.position, light.radius))
                colors.extend((*light.color, light.intensity))
            if not lighting.lights:
                positions.extend([0.0] * 4)
                colors.extend([0.0] * 4)
            self._colors = colors
            self._scales = [1.0] * len(lighting.lights)
            self._animated = tuple((index, light) for index, light in enumerate(lighting.lights)
                                   if light.flicker is not None)
            self._light_data = context.texture((max(1, len(lighting.lights)), 2), 4,
                                               positions.tobytes() + colors.tobytes(), dtype="f4")
            self._light_data.filter = moderngl.NEAREST, moderngl.NEAREST
            resolution = lighting.shadow_resolution
            limit = context.info["GL_MAX_TEXTURE_SIZE"]
            self._atlas_columns = max(min(ATLAS_COLUMNS, limit // (3 * resolution)),
                                      math.ceil(len(lighting.lights) / (limit // (2 * resolution))))
            rows = max(1, math.ceil(len(lighting.lights) / self._atlas_columns))
            size = (self._atlas_columns * 3 * resolution, rows * 2 * resolution)
            if max(size) > context.info["GL_MAX_TEXTURE_SIZE"]:
                raise ValueError("Shadow atlas exceeds the GPU texture size limit")
            self._texture = context.depth_texture(size)
            self._texture.compare_func = ""
            self._texture.filter = moderngl.NEAREST, moderngl.NEAREST
            self._texture.repeat_x = self._texture.repeat_y = False
            self._framebuffer = context.framebuffer(depth_attachment=self._texture)
            program["shadow_grid"].value = self._atlas_columns * 3, rows * 2
            program["shadow_light_columns"].value = self._atlas_columns
            shaders = Path(__file__).resolve().parent / "shaders"
            self._program = context.program(
                vertex_shader=(shaders / "shadow.vert").read_text(encoding="utf-8"),
                fragment_shader=(shaders / "shadow.frag").read_text(encoding="utf-8"),
            )
            self._cube = CubeMesh(context, self._program, position_only=True)
            self._bake(level, resolution, extra_shadow_boxes)
            self.grid = build_light_grid(level, cell_size, context.info["GL_MAX_TEXTURE_SIZE"])
            if self.grid is not None:
                self._grid_texture = context.texture(self.grid.texture_size, 1, self.grid.indices, dtype="i4")
                self._grid_texture.filter = moderngl.NEAREST, moderngl.NEAREST
                program["light_grid_origin"].value = self.grid.origin
                program["light_grid_shape"].value = self.grid.shape
                program["light_grid_cell_size"].value = self.grid.cell_size
        except Exception:
            self.release()
            raise

    def _bake(self, level, resolution, extra_shadow_boxes=()):
        self._render_lights(range(len(level.lighting.lights)), resolution,
                            self._object_boxes + tuple(extra_shadow_boxes))

    def sync_objects(self, boxes):
        previous = self._object_boxes
        self._object_boxes = boxes
        if self._framebuffer is None or previous == boxes:
            return
        changed = tuple(box for box in previous if box not in boxes) + tuple(box for box in boxes if box not in previous)
        affected = [index for index, light in enumerate(self._level.lighting.lights)
                    if any(distance_to_box_squared(light.position, box.position, box.bounds_half_size)
                           < light.radius ** 2 for box in changed)]
        if affected:
            self._render_lights(affected, self._level.lighting.shadow_resolution,
                                boxes)

    def recalculate_shadows(self, extra_boxes=()):
        if self._framebuffer is None:
            return
        boxes = self._object_boxes + tuple(extra_boxes)
        self._render_lights(
            range(len(self._level.lighting.lights)),
            self._level.lighting.shadow_resolution,
            boxes,
        )

    def _render_lights(self, indices, resolution, boxes):
        self._framebuffer.use()
        self._context.scissor = None
        self._context.enable_only(moderngl.DEPTH_TEST)
        self._context.depth_func = "<"
        self._framebuffer.depth_mask = True
        prepared = self._static_geometry + tuple((box, box.model_matrix.to_bytes(), box.bounds_half_size)
                                                 for box in boxes)
        for index in indices:
            light = self._level.lighting.lights[index]
            origin = glm.vec3(light.position)
            projection = glm.perspective(glm.radians(90.0), 1.0, SHADOW_NEAR, light.radius)
            nearby = []
            for box, model, half_size in prepared:
                distance = distance_to_box_squared(light.position, box.position, half_size)
                if distance < light.radius ** 2:
                    nearby.append(model)
            for face, (direction, up) in enumerate(FACE_VIEWS):
                x = ((index % self._atlas_columns) * 3 + face % 3) * resolution
                y = ((index // self._atlas_columns) * 2 + face // 3) * resolution
                self._context.viewport = (x, y, resolution, resolution)
                # Очищаем только грань изменившейся лампы, остальные тени сохраняются.
                self._framebuffer.clear(depth=1.0, viewport=(x, y, resolution, resolution))
                matrix = projection * glm.lookAt(origin, origin + glm.vec3(direction), glm.vec3(up))
                self._program["m_light"].write(matrix)
                for model in nearby:
                    self._program["m_model"].write(model)
                    self._cube.render()
        self._context.scissor = None

    def update(self, delta_time: float, enabled: bool = True):
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Light delta time must be finite and nonnegative")
        self._elapsed += delta_time
        changed = False
        for index, light in self._animated:
            scale = light.flicker.brightness(self._elapsed) if enabled else 1.0
            if scale != self._scales[index]:
                self._scales[index] = scale
                self._colors[index * 4 + 3] = light.intensity * scale
                changed = True
        if changed:
            # Одна небольшая запись строки яркостей; геометрия, сетка и атлас теней прежние.
            self._light_data.write(self._colors.tobytes(), viewport=(0, 1, len(self._scales), 1))

    def emission(self, box):
        scale = self._scales[box.emission_light] if box.emission_light is not None else 1.0
        return box.emission if scale == 1.0 else tuple(c * scale for c in box.emission)

    def bind(self, local_lights=True):
        if self._texture is not None:
            self._texture.use(location=2)
        self._scene_program["use_light_grid"].value = local_lights and self.grid is not None
        if self._grid_texture is not None:
            self._grid_texture.use(location=3)
        if self._light_data is not None:
            self._light_data.use(location=4)

    def release(self):
        for name in ("_cube", "_program", "_framebuffer", "_texture", "_grid_texture", "_light_data"):
            resource = getattr(self, name)
            if resource is not None:
                resource.release()
                setattr(self, name, None)
