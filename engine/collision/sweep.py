"""Continuous circle contacts with a rectangle, including its rounded corners."""
import math
from engine.collision.obb import OBB


def circle_contact(box, x, z, dx, dz, radius):
    rotated = isinstance(box, OBB)
    if rotated:
        x, z = box.local_point(x, z)
        dx, dz = box.local_direction(dx, dz)
        lo_x, hi_x = -box.half_width, box.half_width
        lo_z, hi_z = -box.half_depth, box.half_depth
    else:
        lo_x, hi_x, lo_z, hi_z = box.min_x, box.max_x, box.min_z, box.max_z
    if (max(x, x + dx) < lo_x - radius or min(x, x + dx) > hi_x + radius
            or max(z, z + dz) < lo_z - radius or min(z, z + dz) > hi_z + radius):
        return None
    contacts = []
    # A float32 position can begin a few micrometres inside the last contact.
    # Resolve that contact at t=0, even when a nearly tangent velocity makes
    # the analytic entry time substantially negative.
    near_x = max(lo_x, min(hi_x, x))
    near_z = max(lo_z, min(hi_z, z))
    gap_x, gap_z = x - near_x, z - near_z
    gap2 = gap_x * gap_x + gap_z * gap_z
    if 1e-20 < gap2 <= (radius + 2e-6) ** 2:
        gap = math.sqrt(gap2)
        nx, nz = gap_x / gap, gap_z / gap
        if dx * nx + dz * nz < -1e-12:
            contacts.append((0, nx, nz))
    for plane, normal in ((lo_x - radius, -1), (hi_x + radius, 1)):
        if dx * normal < -1e-12:
            t = (plane - x) / dx
            if -1e-5 <= t <= 1 and lo_z - 1e-8 <= z + dz * t <= hi_z + 1e-8:
                contacts.append((max(0, t), normal, 0))
    for plane, normal in ((lo_z - radius, -1), (hi_z + radius, 1)):
        if dz * normal < -1e-12:
            t = (plane - z) / dz
            if -1e-5 <= t <= 1 and lo_x - 1e-8 <= x + dx * t <= hi_x + 1e-8:
                contacts.append((max(0, t), 0, normal))
    length2 = dx * dx + dz * dz
    if length2 > 1e-20:
        for cx, sx in ((lo_x, -1), (hi_x, 1)):
            for cz, sz in ((lo_z, -1), (hi_z, 1)):
                rx, rz = x - cx, z - cz
                b = rx * dx + rz * dz
                discriminant = b * b - length2 * (rx * rx + rz * rz - radius * radius)
                if discriminant <= 0:
                    continue
                t = (-b - math.sqrt(discriminant)) / length2
                if -1e-5 <= t <= 1:
                    nx, nz = (rx + dx * t) / radius, (rz + dz * t) / radius
                    if nx * sx >= -1e-8 and nz * sz >= -1e-8 and dx * nx + dz * nz < -1e-12:
                        contacts.append((max(0, t), nx, nz))
    if not contacts:
        return None
    t, nx, nz = min(contacts, key=lambda c: c[0])
    if rotated:
        nx, nz = box._cos * nx + box._sin * nz, -box._sin * nx + box._cos * nz
    return t, nx, nz
