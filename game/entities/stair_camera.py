"""A visual tremor driven by actual movement on authored stair surfaces."""

import math

from config import settings


class StairCameraShake:
    def __init__(self, surfaces=()):
        self._cells = {}
        for surface in surfaces:
            collider = surface.collider
            footprint = collider.footprint
            for x in range(math.floor(footprint.min_x / 2), math.floor(footprint.max_x / 2) + 1):
                for z in range(math.floor(footprint.min_z / 2), math.floor(footprint.max_z / 2) + 1):
                    self._cells.setdefault((x, z), []).append(collider)
        self.reset()

    def reset(self):
        self.strength = self._time = self._walking_time = self._rest_time = 0.0
        self.stress = 0.0

    def on_stairs(self, body):
        if not body.grounded:
            return False
        x, y, z = body.position
        # Include neighbouring cells for feet at the edge of a tread.
        radius = body.radius
        for cell_x in range(math.floor((x - radius) / 2), math.floor((x + radius) / 2) + 1):
            for cell_z in range(math.floor((z - radius) / 2), math.floor((z + radius) / 2) + 1):
                for collider in self._cells.get((cell_x, cell_z), ()):
                    if (abs(collider.top - y) < 0.06
                            and collider.footprint.intersects_circle(x, z, radius)):
                        return True
        return False

    def update(self, delta_time, body):
        """Return a visual rotation and an event after a sustained stair walk ends."""
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Stair shake delta time must be finite and nonnegative")
        delta_time = min(delta_time, settings.MAX_DELTA_TIME)
        moving = body.horizontal_speed > 0.1 and self.on_stairs(body)
        finished = False
        if moving:
            self._walking_time += delta_time
            self._rest_time = 0.0
            self.strength = min(1.0, self.strength + delta_time / settings.STAIR_SHAKE_FADE_IN)
            self.stress = min(1.0, self.stress + delta_time / settings.STAIR_STRESS_FADE_IN)
        else:
            self.strength = max(0.0, self.strength - delta_time / settings.STAIR_SHAKE_FADE_OUT)
            self.stress = max(0.0, self.stress - delta_time / settings.STAIR_STRESS_FADE_OUT)
            self._rest_time += delta_time
            if self._rest_time >= settings.STAIR_COMMENT_REST_SECONDS and body.grounded:
                finished = self._walking_time >= settings.STAIR_COMMENT_MIN_WALK_SECONDS
                self._walking_time = 0.0
        self._time += delta_time
        phase = self._time * math.tau * settings.STAIR_SHAKE_FREQUENCY
        waves = (
            0.7 * math.sin(phase) + 0.3 * math.sin(phase * 2.17),
            0.65 * math.sin(phase * 1.31 + 0.8) + 0.35 * math.sin(phase * 2.63),
            0.7 * math.sin(phase * 0.83 + 1.7) + 0.3 * math.sin(phase * 1.93),
        )
        gain = self.strength if settings.STAIR_SHAKE_ENABLED else 0.0
        return tuple(gain * amplitude * wave for amplitude, wave in
                     zip(settings.STAIR_SHAKE_ROTATION_DEGREES, waves)), finished
