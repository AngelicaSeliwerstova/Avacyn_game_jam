from array import array
from bisect import bisect_right
from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path
import struct

import glm
import moderngl
import pygame


_COMPONENTS = {
    5120: ("b", 1),
    5121: ("B", 1),
    5122: ("h", 2),
    5123: ("H", 2),
    5125: ("I", 4),
    5126: ("f", 4),
}
_TYPE_WIDTHS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
_SKIN_TEXTURE_UNIT = 10


@dataclass
class _Primitive:
    vertex_buffer: moderngl.Buffer
    index_buffer: moderngl.Buffer | None
    vertex_array: moderngl.VertexArray
    index_count: int
    material: int | None
    skin_texture: moderngl.Texture | None
    center: tuple[float, float, float]
    alpha_mode: int
    alpha_cutoff: float
    alpha: float


class GLTFModel:
    """Loads a GLB mesh, its materials, and a looping skeletal animation."""

    def __init__(
        self, context: moderngl.Context, program: moderngl.Program, path: Path,
        fallback_texture: moderngl.Texture,
    ):
        self._context = context
        self._program = program
        self._fallback_texture = fallback_texture
        self._buffers: list[moderngl.Buffer] = []
        self._vertex_arrays: list[moderngl.VertexArray] = []
        self._textures: list[moderngl.Texture] = []
        self._skin_textures: list[moderngl.Texture] = []
        self._primitives: list[tuple[int, int, _Primitive]] = []
        self._time = 0.0
        try:
            self._read_glb(path)
            self._load_scene()
            self._load_animation()
            self._update_skin_textures()
        except Exception:
            self.release()
            raise

    def _read_glb(self, path: Path):
        data = Path(path).read_bytes()
        if len(data) < 20:
            raise ValueError(f"Invalid GLB file: {path}")
        magic, version, length = struct.unpack_from("<4sII", data)
        if magic != b"glTF" or version != 2 or length != len(data):
            raise ValueError(f"Unsupported or malformed GLB file: {path}")
        offset = 12
        self._document = None
        self._binary = b""
        while offset < length:
            chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
            offset += 8
            chunk = data[offset:offset + chunk_length]
            offset += chunk_length
            if chunk_type == 0x4E4F534A:
                self._document = json.loads(chunk.decode("utf-8").rstrip(" \t\r\n\0"))
            elif chunk_type == 0x004E4942:
                self._binary = chunk
        if self._document is None:
            raise ValueError(f"GLB file has no JSON scene: {path}")
        if self._document.get("asset", {}).get("version") != "2.0":
            raise ValueError("Only glTF 2.0 models are supported")

    def _read_accessor(self, index: int) -> list[tuple[int | float, ...]]:
        accessor = self._document["accessors"][index]
        if "sparse" in accessor:
            raise ValueError("Sparse glTF accessors are not supported")
        component_format, component_size = _COMPONENTS[accessor["componentType"]]
        width = _TYPE_WIDTHS[accessor["type"]]
        view = self._document["bufferViews"][accessor["bufferView"]]
        stride = view.get("byteStride", component_size * width)
        start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        unpack = struct.Struct("<" + component_format * width).unpack_from
        values = [unpack(self._binary, start + row * stride) for row in range(accessor["count"])]
        if accessor.get("normalized") and accessor["componentType"] != 5126:
            maximum = {5120: 127, 5121: 255, 5122: 32767, 5123: 65535}[accessor["componentType"]]
            signed = accessor["componentType"] in (5120, 5122)
            values = [tuple(max(-1.0, value / maximum) if signed else value / maximum
                            for value in row) for row in values]
        return values

    @staticmethod
    def _node_transform(node: dict) -> glm.mat4:
        if "matrix" in node:
            result = glm.mat4(1.0)
            for column in range(4):
                for row in range(4):
                    result[column][row] = node["matrix"][column * 4 + row]
            return result
        translation = glm.vec3(node.get("translation", (0.0, 0.0, 0.0)))
        rotation = node.get("rotation", (0.0, 0.0, 0.0, 1.0))
        quaternion = glm.quat(rotation[3], rotation[0], rotation[1], rotation[2])
        scale = glm.vec3(node.get("scale", (1.0, 1.0, 1.0)))
        return (glm.translate(glm.mat4(1.0), translation) * glm.mat4_cast(quaternion)
                * glm.scale(glm.mat4(1.0), scale))

    def _load_images(self):
        self._image_textures = []
        for image in self._document.get("images", ()):
            if "bufferView" not in image:
                raise ValueError("GLB images must be embedded in the binary file")
            view = self._document["bufferViews"][image["bufferView"]]
            start = view.get("byteOffset", 0)
            encoded = self._binary[start:start + view["byteLength"]]
            surface = pygame.image.load(BytesIO(encoded), image.get("name") or "model texture")
            size = surface.get_size()
            texture = self._context.texture(
                size, 4, pygame.image.tobytes(surface, "RGBA", False), alignment=1,
            )
            texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
            texture.repeat_x = True
            texture.repeat_y = True
            self._textures.append(texture)
            self._image_textures.append(texture)
        self._material_textures = []
        for texture in self._document.get("textures", ()):
            source = texture.get("source")
            self._material_textures.append(None if source is None else self._image_textures[source])

    def _load_scene(self):
        self._load_images()
        self._nodes = self._document.get("nodes", [])
        self._local_matrices = [self._node_transform(node) for node in self._nodes]
        self._world_matrices = [glm.mat4(1.0) for _ in self._nodes]
        self._scene_roots = self._document["scenes"][self._document.get("scene", 0)]["nodes"]
        self._skins = []
        for skin in self._document.get("skins", ()):
            inverse_bind = ([glm.mat4(1.0) for _ in skin["joints"]]
                            if "inverseBindMatrices" not in skin else
                            [self._matrix(value) for value in self._read_accessor(skin["inverseBindMatrices"])])
            self._skins.append((skin["joints"], inverse_bind))
        self._update_world_matrices()
        materials = self._document.get("materials", ())
        mesh_nodes = []
        for index, node in enumerate(self._nodes):
            if "mesh" not in node:
                continue
            if node.get("skin") is not None:
                skin = self._skins[node["skin"]]
                matrices = self._skin_matrices(index, skin)
                texture = self._context.texture((4, len(matrices)), 4,
                                                b"".join(matrix.to_bytes() for matrix in matrices),
                                                dtype="f4", alignment=1)
                texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
                self._skin_textures.append(texture)
            else:
                texture = None
            mesh_nodes.append((index, texture))
            for primitive_data in self._document["meshes"][node["mesh"]]["primitives"]:
                if primitive_data.get("mode", 4) != 4:
                    raise ValueError("Only triangle-list GLB meshes are supported")
                attributes = primitive_data["attributes"]
                positions = self._read_accessor(attributes["POSITION"])
                normals = self._read_accessor(attributes["NORMAL"]) if "NORMAL" in attributes else [
                    (0.0, 1.0, 0.0)
                ] * len(positions)
                uvs = self._read_accessor(attributes["TEXCOORD_0"]) if "TEXCOORD_0" in attributes else [
                    (0.0, 0.0)
                ] * len(positions)
                joints = self._read_accessor(attributes["JOINTS_0"]) if "JOINTS_0" in attributes else [
                    (0, 0, 0, 0)
                ] * len(positions)
                weights = self._read_accessor(attributes["WEIGHTS_0"]) if "WEIGHTS_0" in attributes else [
                    (0.0, 0.0, 0.0, 0.0)
                ] * len(positions)
                material_index = primitive_data.get("material")
                material = {} if material_index is None else materials[material_index]
                factor = material.get("pbrMetallicRoughness", {}).get(
                    "baseColorFactor", (1.0, 1.0, 1.0, 1.0),
                )
                alpha_mode = {"OPAQUE": 0, "MASK": 1, "BLEND": 2}.get(
                    material.get("alphaMode", "OPAQUE"),
                )
                if alpha_mode is None:
                    raise ValueError(f"Unknown glTF material alpha mode: {material['alphaMode']}")
                vertex_data = array("f")
                for position, normal, uv, joint, weight in zip(positions, normals, uvs, joints, weights):
                    vertex_data.extend(position)
                    vertex_data.extend(tuple(channel * factor[i] for i, channel in enumerate((1.0, 1.0, 1.0))))
                    vertex_data.extend(normal)
                    vertex_data.extend(uv)
                    vertex_data.extend(joint)
                    vertex_data.extend(weight)
                vertex_buffer = self._context.buffer(vertex_data.tobytes())
                self._buffers.append(vertex_buffer)
                index_buffer = None
                index_count = len(positions)
                if "indices" in primitive_data:
                    indices = self._read_accessor(primitive_data["indices"])
                    index_values = [value[0] for value in indices]
                    component_type = self._document["accessors"][primitive_data["indices"]]["componentType"]
                    index_format = {5121: "B", 5123: "H", 5125: "I"}[component_type]
                    index_element_size = _COMPONENTS[component_type][1]
                    index_buffer = self._context.buffer(struct.pack(
                        "<" + index_format * len(index_values), *index_values,
                    ))
                    self._buffers.append(index_buffer)
                    index_count = len(index_values)
                vertex_array = self._context.vertex_array(
                    self._program,
                    [(vertex_buffer, "3f 3f 3f 2f 4f 4f",
                      "in_position", "in_color", "in_normal", "in_uv", "in_joints", "in_weights")],
                    index_buffer=index_buffer,
                    index_element_size=2 if index_buffer is None else index_element_size,
                )
                self._vertex_arrays.append(vertex_array)
                self._primitives.append((index, material_index, _Primitive(
                    vertex_buffer, index_buffer, vertex_array, index_count, material_index, texture,
                    tuple(sum(position[axis] for position in positions) / len(positions) for axis in range(3)),
                    alpha_mode, material.get("alphaCutoff", 0.5), factor[3],
                )))
        self._mesh_nodes = mesh_nodes

    @staticmethod
    def _matrix(values) -> glm.mat4:
        result = glm.mat4(1.0)
        for column in range(4):
            for row in range(4):
                result[column][row] = values[column * 4 + row]
        return result

    def _update_world_matrices(self):
        def visit(index: int, parent: glm.mat4):
            self._world_matrices[index] = parent * self._local_matrices[index]
            for child in self._nodes[index].get("children", ()):
                visit(child, self._world_matrices[index])

        for root in self._scene_roots:
            visit(root, glm.mat4(1.0))

    def _skin_matrices(self, mesh_node: int, skin) -> list[glm.mat4]:
        inverse_mesh = glm.inverse(self._world_matrices[mesh_node])
        joints, inverse_bind = skin
        return [inverse_mesh * self._world_matrices[joint] * inverse_bind[index]
                for index, joint in enumerate(joints)]

    def _load_animation(self):
        self._channels = []
        self._duration = 0.0
        animations = self._document.get("animations", ())
        if not animations:
            return
        animation = animations[0]
        samplers = animation["samplers"]
        for channel in animation["channels"]:
            sampler = samplers[channel["sampler"]]
            if sampler.get("interpolation", "LINEAR") not in ("LINEAR", "STEP"):
                raise ValueError("Only LINEAR and STEP glTF animation interpolation is supported")
            times = [float(value[0]) for value in self._read_accessor(sampler["input"])]
            values = self._read_accessor(sampler["output"])
            self._duration = max(self._duration, times[-1] if times else 0.0)
            self._channels.append((
                channel["target"]["node"], channel["target"]["path"], times, values,
                sampler.get("interpolation", "LINEAR"),
            ))

    def _sample_channel(self, channel, time: float):
        _, path, times, values, interpolation = channel
        if not times:
            return None
        right = bisect_right(times, time)
        left = max(0, right - 1)
        if interpolation == "STEP" or right == 0:
            return values[left]
        if right == len(times):
            return values[-1]
        amount = (time - times[left]) / (times[right] - times[left])
        if path == "rotation":
            first = glm.quat(values[left][3], values[left][0], values[left][1], values[left][2])
            second = glm.quat(values[right][3], values[right][0], values[right][1], values[right][2])
            result = glm.normalize(glm.slerp(first, second, amount))
            return result.x, result.y, result.z, result.w
        return tuple(a + (b - a) * amount for a, b in zip(values[left], values[right]))

    def update(self, delta_time: float, speed: float = 1.0):
        if not self._channels or self._duration <= 0:
            return
        self._time = (self._time + delta_time * speed) % self._duration if speed > 0 else 0.0
        animated = {}
        for channel in self._channels:
            node_index, path, *_ = channel
            value = self._sample_channel(channel, self._time)
            if value is not None:
                animated.setdefault(node_index, {})[path] = value
        for index, node in enumerate(self._nodes):
            if index not in animated or "matrix" in node:
                continue
            current = animated[index]
            translation = current.get("translation", node.get("translation", (0.0, 0.0, 0.0)))
            rotation = current.get("rotation", node.get("rotation", (0.0, 0.0, 0.0, 1.0)))
            scale = current.get("scale", node.get("scale", (1.0, 1.0, 1.0)))
            quaternion = glm.quat(rotation[3], rotation[0], rotation[1], rotation[2])
            self._local_matrices[index] = (
                glm.translate(glm.mat4(1.0), glm.vec3(translation)) * glm.mat4_cast(quaternion)
                * glm.scale(glm.mat4(1.0), glm.vec3(scale))
            )
        self._update_world_matrices()
        self._update_skin_textures()

    def _update_skin_textures(self):
        for node_index, texture in self._mesh_nodes:
            if texture is None:
                continue
            skin = self._skins[self._nodes[node_index]["skin"]]
            matrices = self._skin_matrices(node_index, skin)
            texture.write(b"".join(matrix.to_bytes() for matrix in matrices), alignment=1)

    def render(self, world_matrix: glm.mat4, camera_position):
        count = 0
        def distance_squared(item):
            node_index, _, primitive = item
            center = glm.vec3(
                world_matrix * self._world_matrices[node_index] * glm.vec4(*primitive.center, 1.0)
            )
            difference = center - glm.vec3(camera_position)
            return glm.dot(difference, difference)

        transparent = sorted(
            (item for item in self._primitives if item[2].alpha_mode == 2),
            key=distance_squared,
            reverse=True,
        )
        opaque = [item for item in self._primitives if item[2].alpha_mode != 2]
        self._context.enable(moderngl.BLEND)
        self._context.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        try:
            for node_index, _, primitive in opaque + transparent:
                self._program["m_model"].write(world_matrix * self._world_matrices[node_index])
                self._program["local_texture"].value = False
                self._program["use_uv"].value = True
                self._program["use_skinning"].value = primitive.skin_texture is not None
                self._program["material_color_enabled"].value = True
                self._program["material_alpha_mode"].value = primitive.alpha_mode
                self._program["material_alpha"].value = primitive.alpha
                self._program["material_alpha_cutoff"].value = primitive.alpha_cutoff
                self._program["emission"].value = (0.0, 0.0, 0.0)
                if primitive.material is None:
                    texture = None
                else:
                    material = self._document["materials"][primitive.material]
                    texture_info = material.get("pbrMetallicRoughness", {}).get("baseColorTexture")
                    texture = None if texture_info is None else self._material_textures[texture_info["index"]]
                self._program["textured"].value = texture is not None
                self._program["texture_world_size"].value = 1.0
                (texture if texture is not None else self._fallback_texture).use(location=0)
                if primitive.skin_texture is not None:
                    primitive.skin_texture.use(location=_SKIN_TEXTURE_UNIT)
                self._program["skin_matrices"].value = _SKIN_TEXTURE_UNIT
                primitive.vertex_array.render(mode=moderngl.TRIANGLES, vertices=primitive.index_count)
                count += primitive.index_count // 3
        finally:
            self._context.disable(moderngl.BLEND)
            self._program["use_uv"].value = False
            self._program["use_skinning"].value = False
            self._program["material_color_enabled"].value = False
            self._program["material_alpha_mode"].value = 0
            self._program["material_alpha"].value = 1.0
        return len(self._primitives), count

    def release(self):
        for vertex_array in self._vertex_arrays:
            vertex_array.release()
        for buffer in self._buffers:
            buffer.release()
        for texture in self._skin_textures + self._textures:
            texture.release()
