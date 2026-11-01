"""Small leafless tree assemblies for the Creator prop catalog."""

import math

import glm

from engine.scene.box import Box


def dead_tree(height=4.1, broken=False):
    boxes = []

    def branch(start, end, thickness, exposed=False):
        a, b = glm.vec3(start), glm.vec3(end)
        direction = b - a
        unit = glm.normalize(direction)
        rotation = glm.normalize(glm.quat(1 + unit.y, unit.z, 0, -unit.x))
        boxes.append(Box(tuple((a + b) / 2), (thickness, glm.length(direction), thickness),
                         material="dead_wood" if exposed else "dead_bark",
                         local_texture=True, orientation=tuple(rotation)))

    # Tapered, slightly crooked trunk with a snapped pale tip.
    points = [(0, 0, 0), (0.04, height * 0.31, 0.02),
              (-0.07, height * 0.61, 0.04), (0.06, height * 0.85, -0.03),
              (0.11, height, 0.03)]
    for index in range(len(points) - 1):
        branch(points[index], points[index + 1], height * (0.085 - index * 0.016), exposed=index == 3)
    for angle in (0, 75, 155, 240, 310):
        rad = math.radians(angle)
        branch((0, 0.13, 0), (math.cos(rad) * height * 0.15, 0.07,
                              math.sin(rad) * height * 0.15), height * 0.045)
    if not broken:
        for index, angle in enumerate((20, 125, 235)):
            rad = math.radians(angle)
            start = glm.vec3(points[2 if index != 1 else 1])
            elbow = start + glm.vec3(math.cos(rad) * height * 0.22, height * 0.13,
                                     math.sin(rad) * height * 0.22)
            tip = elbow + glm.vec3(math.cos(rad + 0.3) * height * 0.13, height * 0.24,
                                   math.sin(rad + 0.3) * height * 0.13)
            branch(start, elbow, height * 0.04)
            branch(elbow, tip, height * 0.024)
            for side in (-1, 1):
                twig = elbow + glm.vec3(math.cos(rad + side * 0.8) * height * 0.17,
                                        height * 0.18, math.sin(rad + side * 0.8) * height * 0.17)
                branch(elbow, twig, height * 0.013, exposed=side == 1)
    return tuple(boxes)
