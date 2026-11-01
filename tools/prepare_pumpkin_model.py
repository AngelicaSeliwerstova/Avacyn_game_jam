"""Export the user's pumpkin, with a floor-level origin and unit diameter.

Run with Blender: blender --background --python tools/prepare_pumpkin_model.py
The source .blend is opened without executing embedded scripts and never saved.
"""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pumpkin_1.blend"
OUTPUT = ROOT / "resources/models/props/pumpkin.glb"


def export():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    meshes = []
    for obj in tuple(bpy.context.scene.objects):
        if obj.type != "MESH" or obj.hide_render:
            continue
        mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
        mesh.transform(obj.matrix_world)
        meshes.append(mesh)
    if not meshes:
        raise ValueError("Pumpkin source contains no visible mesh")

    points = [vertex.co for mesh in meshes for vertex in mesh.vertices]
    low = Vector(tuple(min(point[i] for point in points) for i in range(3)))
    high = Vector(tuple(max(point[i] for point in points) for i in range(3)))
    diameter = max(high.x - low.x, high.y - low.y)
    origin = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
    bpy.ops.object.select_all(action="DESELECT")
    for index, mesh in enumerate(meshes):
        for vertex in mesh.vertices:
            vertex.co = (vertex.co - origin) / diameter
        obj = bpy.data.objects.new(f"Pumpkin_{index}", mesh)
        bpy.context.collection.objects.link(obj)
        obj.select_set(True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(OUTPUT), export_format="GLB", use_selection=True,
                              export_animations=False, export_yup=True)
    print(f"Exported {OUTPUT}")
    print(f"Normalized dimensions (Blender XYZ): {tuple((high - low) / diameter)}")
    print(f"Vertices: {sum(len(mesh.vertices) for mesh in meshes)}")


if __name__ == "__main__":
    export()
