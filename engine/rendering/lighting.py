from array import array
import math
from pathlib import Path

import glm
import moderngl

from engine.rendering.meshes.cube import CubeMesh
from engine.scene.level import Level
from engine.scene.lighting import MAX_POINT_LIGHTS


SHADOW_NEAR = 0.05
ATLAS_COLUMNS = 8
FACE_VIEWS = (
    ((1, 0, 0), (0, -1, 0)), ((-1, 0, 0), (0, -1, 0)),
    ((0, 1, 0), (0, 0, 1)), ((0, -1, 0), (0, 0, -1)),
    ((0, 0, 1), (0, -1, 0)), ((0, 0, -1), (0, -1, 0)),
)


class LevelLighting:
    """Статические карты теней ламп. Запекаются один раз при загрузке уровня."""

    def __init__(self, context: moderngl.Context, program: moderngl.Program, level: Level):
        self._context = context
        self._texture = None
        self._framebuffer = None
        self._program = None
        self._cube = None
        lighting = level.lighting
        program["lighting_enabled"].value = lighting is not None
        program["shadow_atlas"].value = 2
        if lighting is None:
            return
        try:
            program["ambient_light"].value = lighting.ambient
            program["light_count"].value = len(lighting.lights)
            positions, colors = array("f"), array("f")
            for light in lighting.lights:
                positions.extend((*light.position, light.radius))
                colors.extend((*light.color, light.intensity))
            positions.extend([0.0] * (4 * MAX_POINT_LIGHTS - len(positions)))
            colors.extend([0.0] * (4 * MAX_POINT_LIGHTS - len(colors)))
            program["light_position_radius"].write(positions.tobytes())
            program["light_color_intensity"].write(colors.tobytes())
            rows = max(1, math.ceil(len(lighting.lights) / ATLAS_COLUMNS))
            resolution = lighting.shadow_resolution
            size = (ATLAS_COLUMNS * 3 * resolution, rows * 2 * resolution)
            if max(size) > context.info["GL_MAX_TEXTURE_SIZE"]:
                raise ValueError("Shadow atlas exceeds the GPU texture size limit")
            self._texture = context.depth_texture(size)
            self._texture.compare_func = ""
            self._texture.filter = moderngl.NEAREST, moderngl.NEAREST
            self._texture.repeat_x = self._texture.repeat_y = False
            self._framebuffer = context.framebuffer(depth_attachment=self._texture)
            program["shadow_grid"].value = ATLAS_COLUMNS * 3, rows * 2
            shaders = Path(__file__).resolve().parent / "shaders"
            self._program = context.program(
                vertex_shader=(shaders / "shadow.vert").read_text(encoding="utf-8"),
                fragment_shader=(shaders / "shadow.frag").read_text(encoding="utf-8"),
            )
            self._cube = CubeMesh(context, self._program, position_only=True)
            self._bake(level, resolution)
            # Геометрия и шейдер запекания больше не нужны, остаётся только атлас.
            self._cube.release()
            self._cube = None
            self._program.release()
            self._program = None
            self._framebuffer.release()
            self._framebuffer = None
        except Exception:
            self.release()
            raise

    def _bake(self, level, resolution):
        self._framebuffer.use()
        self._context.scissor = None
        self._context.enable_only(moderngl.DEPTH_TEST)
        self._framebuffer.clear(depth=1.0)
        for index, light in enumerate(level.lighting.lights):
            origin = glm.vec3(light.position)
            projection = glm.perspective(glm.radians(90.0), 1.0, SHADOW_NEAR, light.radius)
            nearby = []
            for box in level.boxes + level.decorations:
                distance = sum(max(0, abs(p - c) - s / 2) ** 2
                               for p, c, s in zip(light.position, box.position, box.size))
                if distance < light.radius ** 2:
                    nearby.append(box)
            for face, (direction, up) in enumerate(FACE_VIEWS):
                x = ((index % ATLAS_COLUMNS) * 3 + face % 3) * resolution
                y = ((index // ATLAS_COLUMNS) * 2 + face // 3) * resolution
                self._context.viewport = (x, y, resolution, resolution)
                matrix = projection * glm.lookAt(origin, origin + glm.vec3(direction), glm.vec3(up))
                self._program["m_light"].write(matrix)
                for box in nearby:
                    self._program["m_model"].write(box.model_matrix)
                    self._cube.render()
        self._context.scissor = None

    def bind(self):
        if self._texture is not None:
            self._texture.use(location=2)

    def release(self):
        for name in ("_cube", "_program", "_framebuffer", "_texture"):
            resource = getattr(self, name)
            if resource is not None:
                resource.release()
                setattr(self, name, None)
