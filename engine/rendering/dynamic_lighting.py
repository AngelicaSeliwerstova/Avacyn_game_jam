from array import array
from dataclasses import dataclass
import math
from pathlib import Path

import glm
import moderngl

from engine.rendering.meshes.cube import CubeMesh
from engine.rendering.visibility import ViewFrustum, distance_to_box_squared
from engine.scene.lighting import MAX_DYNAMIC_SPOT_LIGHTS, SpotLight


@dataclass
class _LightView:
    light: SpotLight
    direction: glm.vec3
    right: glm.vec3
    up: glm.vec3
    matrix: glm.mat4
    tangent: float


class DynamicLighting:
    """До 16 подвижных спотов с отдельным атласом обновляемых теней."""

    def __init__(self, context, program, lights: tuple[SpotLight, ...], resolution: int):
        if len(lights) > MAX_DYNAMIC_SPOT_LIGHTS:
            raise ValueError(f"At most {MAX_DYNAMIC_SPOT_LIGHTS} dynamic spotlights are supported")
        if resolution not in (128, 256, 512, 1024):
            raise ValueError("Dynamic shadow resolution must be 128, 256, 512 or 1024")
        self._context, self._scene_program, self._lights = context, program, lights
        self._resolution = resolution
        self._texture = self._framebuffer = self._program = self._cube = None
        self._shadow_key = self._shadow_objects = None
        self.active_count = self.shadow_draw_calls = 0
        program["dynamic_light_count"].value = 0
        program["dynamic_shadow_atlas"].value = 5
        if not lights:
            return
        self._columns = min(2, len(lights))
        rows = math.ceil(len(lights) / self._columns)
        try:
            self._texture = context.depth_texture((resolution * self._columns, resolution * rows))
            self._texture.compare_func = ""
            self._texture.filter = moderngl.NEAREST, moderngl.NEAREST
            self._texture.repeat_x = self._texture.repeat_y = False
            self._framebuffer = context.framebuffer(depth_attachment=self._texture)
            program["dynamic_shadow_grid"].value = self._columns, rows
            shaders = Path(__file__).resolve().parent / "shaders"
            self._program = context.program(
                vertex_shader=(shaders / "shadow.vert").read_text(encoding="utf-8"),
                fragment_shader=(shaders / "shadow.frag").read_text(encoding="utf-8"),
            )
            self._cube = CubeMesh(context, self._program, position_only=True)
        except Exception:
            self.release()
            raise

    def render_shadows(self, objects):
        views = []
        for light in self._lights:
            if not light.enabled or light.intensity == 0:
                continue
            light.validate()
            direction = glm.normalize(glm.vec3(light.direction))
            up = glm.vec3(0, 0, 1) if abs(direction.y) > 0.999 else glm.vec3(0, 1, 0)
            right = glm.normalize(glm.cross(direction, up))
            up = glm.cross(right, direction)
            origin = glm.vec3(light.position)
            matrix = (glm.perspective(glm.radians(light.outer_angle * 2), 1, 0.05, light.radius)
                      * glm.lookAt(origin, origin + direction, up))
            views.append(_LightView(light, direction, right, up, matrix,
                                    math.tan(math.radians(light.outer_angle))))
        self.active_count = len(views)
        self.shadow_draw_calls = 0
        self._scene_program["dynamic_light_count"].value = len(views)
        if not views:
            self._shadow_key = None
            return
        self._upload(views)
        key = tuple((id(v.light), tuple(v.light.position), tuple(v.direction), v.light.radius,
                     v.light.outer_angle, v.light.shadows) for v in views)
        if key == self._shadow_key and objects is self._shadow_objects:
            return
        if any(v.light.shadows for v in views):
            self._framebuffer.use()
            self._context.scissor = None
            self._context.enable_only(moderngl.DEPTH_TEST)
            self._context.depth_func = "<"
            self._framebuffer.depth_mask = True
            self._framebuffer.clear(depth=1.0)
            for index, view in enumerate(views):
                if not view.light.shadows:
                    continue
                self._context.viewport = ((index % self._columns) * self._resolution,
                                          (index // self._columns) * self._resolution,
                                          self._resolution, self._resolution)
                self._program["m_light"].write(view.matrix.to_bytes())
                frustum = ViewFrustum(view.matrix)
                for box, model, half_size in objects:
                    if (distance_to_box_squared(view.light.position, box.position, half_size) < view.light.radius ** 2
                            and frustum.intersects(box.position, half_size)):
                        self._program["m_model"].write(model)
                        self._cube.render()
                        self.shadow_draw_calls += 1
        self._shadow_key, self._shadow_objects = key, objects

    def _upload(self, views):
        def vectors(name, values):
            padded = values + [(0.0,) * 4] * (MAX_DYNAMIC_SPOT_LIGHTS - len(values))
            self._scene_program[name].write(array("f", (c for row in padded for c in row)).tobytes())

        vectors("dynamic_positions", [(*v.light.position, v.light.radius) for v in views])
        vectors("dynamic_colors", [(*v.light.color, v.light.intensity) for v in views])
        vectors("dynamic_directions", [(*v.direction, 0) for v in views])
        vectors("dynamic_right", [(*v.right, v.tangent) for v in views])
        vectors("dynamic_up", [(*v.up, 0) for v in views])
        vectors("dynamic_cones", [(math.cos(math.radians(v.light.inner_angle)),
                                    math.cos(math.radians(v.light.outer_angle)), float(v.light.shadows), 0)
                                   for v in views])
        matrices = [v.matrix for v in views] + [glm.mat4(1)] * (MAX_DYNAMIC_SPOT_LIGHTS - len(views))
        self._scene_program["dynamic_matrices"].write(b"".join(m.to_bytes() for m in matrices))

    def bind(self):
        if self._texture is not None:
            self._texture.use(location=5)

    def release(self):
        for name in ("_cube", "_program", "_framebuffer", "_texture"):
            resource = getattr(self, name)
            if resource is not None:
                resource.release()
                setattr(self, name, None)
