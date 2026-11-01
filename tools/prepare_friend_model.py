"""Bake a resting pose from friend.glb; run with Blender's Python."""
from pathlib import Path
import math
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]


def export():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / "friend.glb"))
    # The source stores its painted albedo in emission with a black base colour.
    # Move that same texture into albedo so the game's hospital lighting can shade it.
    for material in bpy.data.materials:
        if not material.node_tree:
            continue
        for node in material.node_tree.nodes:
            if node.type != 'BSDF_PRINCIPLED':
                continue
            base, emission = node.inputs['Base Color'], node.inputs['Emission Color']
            if emission.is_linked and not base.is_linked and max(base.default_value[:3]) == 0:
                socket = emission.links[0].from_socket
                material.node_tree.links.new(socket, base)
                base.default_value = (1, 1, 1, 1)
                for link in tuple(emission.links):
                    material.node_tree.links.remove(link)
                node.inputs['Emission Strength'].default_value = 0
    bpy.context.scene.frame_set(1)
    graph = bpy.context.evaluated_depsgraph_get()
    meshes = []
    for obj in tuple(bpy.context.scene.objects):
        if obj.type == "MESH" and not obj.name.startswith("Icosphere"):
            mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(graph))
            mesh.transform(obj.matrix_world)
            meshes.append(mesh)
    points = [v.co for mesh in meshes for v in mesh.vertices]
    height = max(p.z for p in points) - min(p.z for p in points)
    rotation = Matrix.Rotation(math.pi / 2, 4, "Z") @ Matrix.Rotation(-math.pi / 2, 4, "X")
    for mesh in meshes:
        mesh.transform(rotation)
    points = [v.co for mesh in meshes for v in mesh.vertices]
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    origin = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
    bpy.ops.object.select_all(action="DESELECT")
    for index, mesh in enumerate(meshes):
        for vertex in mesh.vertices:
            vertex.co = (vertex.co - origin) * (1.7 / height)
        obj = bpy.data.objects.new(f"RestingFriend_{index}", mesh)
        bpy.context.collection.objects.link(obj)
        obj.select_set(True)
    output = ROOT / "resources/models/props/friend_rest.glb"
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(output), export_format="GLB", use_selection=True,
                             export_animations=False)
    print(output)


if __name__ == "__main__":
    export()
