"""Этажные перекрытия, лестничные проёмы и независимые объекты каждого этажа."""

from dataclasses import replace
import math

from engine.scene.box import Box
from engine.scene.lighting import Lighting, PointLight
from game.levels.objects import build_objects
from game.levels.hospital_finishes import MATERIAL_ROLES


def assemble_storeys(level, boxes, decorations, definitions, lights, stair, count=3,
                     material_map=None, ceiling_material="concrete", surgical_floor=None,
                     patient_floor=None):
    all_boxes, all_decorations, all_objects, all_lights = [], [], [], []
    base_lights = level.lighting.lights if level.lighting else ()
    height, slab = stair.height, 0.24
    material_map = material_map or {}

    def move(box, offset, light_offset=0):
        return replace(box, position=(box.position[0], box.position[1] + offset, box.position[2]),
                       material=material_map.get(box.material, box.material),
                       color=None if box.material in MATERIAL_ROLES else box.color,
                       emission_light=box.emission_light + light_offset
                       if box.emission_light is not None else None)

    def plate(x1, x2, z1, z2, top, material="hospital_floor"):
        all_boxes.append(Box(((x1 + x2) / 2, top - slab / 2, (z1 + z2) / 2),
                             (x2 - x1, slab, z2 - z1), material=material_map.get(material, material)))

    def ceiling_under(plates, finish):
        # Match the actual slab footprints, including the circular stair opening.
        # The lower face looks into the room; the exterior roof keeps concrete.
        for item in plates:
            if abs(item.size[1] - slab) < 1e-6:
                all_decorations.append(replace(
                    item, position=(item.position[0], item.collider.bottom - 0.01, item.position[2]),
                    size=(item.size[0], 0.02, item.size[2]), material=material_map.get(finish, ceiling_material),
                ))

    def surgical_plate(top, material):
        cx, cz = stair.center
        half = 4.6
        plate(-30, cx - half, -24, 24, top, material)
        bridge_end = cx + 6
        bridge_z = cz + 2.9
        bridge_half_depth = 2.65 / 2
        plate(cx + half, bridge_end, -24, bridge_z - bridge_half_depth, top, material)
        plate(bridge_end, 30, -24, 24, top, material)
        plate(cx + half, bridge_end, bridge_z + bridge_half_depth, 24, top, material)
        plate(cx - half, cx + half, -24, cz - half, top, material)
        plate(cx - half, cx + half, cz + half, 24, top, material)

    def gallery(top, *, fill_landing=True):
        cx, cz = stair.center
        half = 4.6
        if fill_landing:
            for x1, x2, z1, z2 in ((-21, cx - half, -2, 9), (cx + half, -5, -2, 9),
                                    (cx - half, cx + half, -2, cz - half),
                                    (cx - half, cx + half, cz + half, 9)):
                plate(x1, x2, z1, z2, top, material="concrete")
            # Торцы радиальных плит не закрывают углы квадрата точно: перекрываем швы
            # прямыми полосами и угловыми плитами, оставаясь снаружи круглого проёма.
            for side in (-1, 1):
                a, b = sorted((side * 4.35, side * half))
                plate(cx + a, cx + b, cz - half, cz + half, top, material="concrete")
                plate(cx - half, cx + half, cz + a, cz + b, top, material="concrete")
        # Square corner pockets fall outside the radial segments but remain outside
        # the stair opening, so keep them even when the old landing fill is disabled.
        for side in (-1, 1):
            for other_side in (-1, 1):
                c, d = sorted((other_side * 3.1, other_side * half))
                e, f = sorted((side * 3.1, side * half))
                plate(cx + c, cx + d, cz + e, cz + f, top, material="concrete")
        for i in range(64):
            angle = (i + 0.5) * 360 / 64
            rad = math.radians(angle)
            outer = half / max(abs(math.cos(rad)), abs(math.sin(rad)))
            inner = 4.35
            radius = (inner + outer) / 2
            depth = 2 * outer * math.tan(math.pi / 64) + 0.025
            all_boxes.append(Box(stair.point(angle, radius, top - slab / 2),
                                 (outer - inner + 0.025, slab, depth),
                                 material=material_map.get("concrete", "concrete"),
                                 yaw_degrees=-angle))
            if not 20 < angle < 75:
                radius = stair.gallery_radius
                depth = 2 * (radius + 0.12) * math.tan(math.pi / 64) + 0.04
                all_boxes.append(Box(stair.point(angle, radius, top + (1.0 - stair.gallery_drop) / 2),
                                     (0.2, 1.0 + stair.gallery_drop, depth),
                                     material=material_map.get("stair_wall", "plaster"), yaw_degrees=-angle))
                all_boxes.append(Box(stair.point(angle, radius, top + 1.04), (0.26, 0.12, depth),
                                     material=material_map.get("rail_metal", "rust"), yaw_degrees=-angle))

    for floor in range(count):
        offset = floor * height
        custom = floor == 1 and surgical_floor is not None
        patient_custom = floor == 2 and patient_floor is not None
        storey_boxes, storey_decorations, storey_lights, storey_definitions = (
            surgical_floor if custom else patient_floor if patient_custom
            else (boxes, decorations, lights, definitions)
        )
        def authored_move(box, light_offset=0):
            moved = move(box, offset, light_offset)
            return replace(moved, authored_group=f"floor_{floor + 1}/{box.authored_group}") if box.authored_group else moved
        all_boxes.extend(authored_move(box) for box in storey_boxes)
        light_offset = floor * len(lights)
        if surgical_floor is not None and floor > 1:
            light_offset += len(surgical_floor[2]) - len(lights)
        all_decorations.extend(authored_move(box, light_offset) for box in storey_decorations)
        all_lights.extend(replace(light, position=(light.position[0], light.position[1] + offset,
                                                  light.position[2])) for light in storey_lights)
        current_definitions = []
        for original in storey_definitions:
            if floor and original["id"].startswith(("main_entrance", "side_entrance")):
                continue
            data = dict(original)
            for key in ("panel_material", "frame_material", "handle_material"):
                if key in data:
                    data[key] = material_map.get(data[key], data[key])
            data["position"] = (data["position"][0], data["position"][1] + offset, data["position"][2])
            if floor:
                data["id"] = f"f{floor + 1}_{data['id']}"
                data["name"] = f"{floor + 1} этаж — {data.get('name', 'Дверь')}"
            current_definitions.append(data)
        all_objects.extend(build_objects(current_definitions))
        slab_start = len(all_boxes)
        if custom or patient_custom:
            surgical_plate(offset, "clinical_floor" if custom else "ward_floor")
            gallery(offset, fill_landing=False)
        elif floor == 2 and surgical_floor is not None:
            surgical_plate(offset, "ward_floor")
            gallery(offset, fill_landing=False)
        elif floor:
            # На верхних этажах у наружных дверей сплошные стены, без выходов в воздух.
            for low, high, material in ((0, 1.35, "hospital_tiles"), (1.35, height - slab, "plaster")):
                y = offset + (low + high) / 2
                all_boxes.append(Box((-0.5, y, 14), (1.9, high - low, 0.24),
                                     material=material_map.get(material, material)))
                all_boxes.append(Box((21, y, -3.5), (0.24, high - low, 1.9),
                                     material=material_map.get(material, material)))
            plate(-21, 21, -14, -2, offset)
            plate(-5, 21, -2, 14, offset)
            plate(-21, -5, 9, 14, offset)
            gallery(offset)
        if floor:
            ceiling_under(all_boxes[slab_start:], "ceiling_clinical" if floor == 2 else "ceiling_room")
    # Крыша находится над третьим этажом; колодец открыт между всеми тремя этажами.
    slab_start = len(all_boxes)
    if surgical_floor is None:
        plate(-21, 21, -14, 14, count * height, material="roof_concrete")
    else:
        plate(-30, 30, -24, 24, count * height, material="roof_concrete")
    ceiling_under(all_boxes[slab_start:], "ceiling_room")
    all_boxes.extend(move(box, 0) for box in stair.build())
    all_lights.append(PointLight((-13, count * height - 0.6, 4), (1, 0.83, 0.61), 3.5, 9))
    return replace(level, boxes=tuple(all_boxes) + level.boxes,
                   floor_material=material_map.get("lobby_floor", level.floor_material),
                   decorations=tuple(all_decorations) + level.decorations,
                   objects=tuple(all_objects) + level.objects,
                   lighting=Lighting(level.lighting.ambient if level.lighting else (0.23, 0.25, 0.23),
                                     base_lights + tuple(all_lights)),
                   floor_heights=tuple(i * height for i in range(count)),
                   floor_labels=tuple(str(i + 1) for i in range(count)),
                   floor_hints=("",) * count, creator_room_height=height - slab)
