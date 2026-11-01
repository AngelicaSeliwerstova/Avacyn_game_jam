"""Decorative blood trail aligned with the actual spiral treads and parapet."""

import random

from engine.scene.box import Box


def stair_blood(stair):
    rng = random.Random(1789)
    stains = []

    def stain(position, width, depth, yaw=0, *, vertical=False):
        shade = rng.uniform(0.82, 1.12)
        size = (width, depth, 0.004) if vertical else (width, 0.004, depth)
        stains.append(Box(position, size, color=(0.39 * shade, 0.022 * shade, 0.015 * shade),
                          yaw_degrees=yaw, decal=True))

    delta = 360 / stair.steps
    # Small, uneven droplets on the walking line of both flights.
    for step in range(stair.landing_steps, stair.steps * stair.flights):
        angle = 90 - (step + 0.5) * delta
        top = stair.step_height(step)
        for _ in range(1 if step % 3 else 2):
            radius = rng.uniform(2.1, 3.45)
            point = stair.point(angle + rng.uniform(-1.3, 1.3), radius, top + 0.006)
            size = rng.uniform(0.08, 0.19)
            stain(point, size, size * rng.uniform(0.9, 1.65), rng.uniform(0, 180))
        # Blood running down the outward face of the inner parapet.
        if step % 5 == 1:
            length = rng.uniform(0.25, 0.65)
            radius = stair.inner_radius + 0.014
            point = stair.point(angle, radius, top + 0.75 - length / 2)
            stain(point, rng.uniform(0.055, 0.11), length, 90 - angle, vertical=True)
            point = stair.point(angle, stair.inner_radius - 0.09, top + 1.081)
            stain(point, 0.22, 0.12, -angle)

    # Dense overlapping pools on the ground at the foot, outside the first rise.
    # Keep them clear of the upper bridge so they remain visible from the hall.
    for x, z, width, depth in ((-0.1, 4.0, 2.0, 1.5), (0.8, 3.0, 1.6, 1.8),
                               (-1.2, 3.6, 1.45, 1.0), (1.5, 3.75, 1.1, 1.6)):
        stain((stair.center[0] + x, 0.006, stair.center[1] + z), width, depth, rng.uniform(0, 180))
    for _ in range(34):
        x = stair.center[0] + rng.uniform(-2.2, 2.5)
        z = stair.center[1] + rng.uniform(2.1, 5.2)
        size = rng.uniform(0.055, 0.3)
        stain((x, 0.007, z), size, size * rng.uniform(0.7, 1.9), rng.uniform(0, 180))
    return tuple(stains)
