from dataclasses import dataclass
import math


MAX_POINT_LIGHTS = 128


def validate_rgb(color):
    if len(color) != 3 or any(not math.isfinite(c) or c < 0 for c in color):
        raise ValueError("Light colors need three finite nonnegative channels")


@dataclass(frozen=True)
class PointLight:
    position: tuple[float, float, float]
    color: tuple[float, float, float] = (0.65, 0.8, 1.0)
    intensity: float = 1.8
    radius: float = 9.0

    def __post_init__(self):
        if len(self.position) != 3 or any(not math.isfinite(c) for c in self.position):
            raise ValueError("Light position needs three finite coordinates")
        validate_rgb(self.color)
        if not math.isfinite(self.intensity) or self.intensity < 0:
            raise ValueError("Light intensity must be finite and nonnegative")
        if not math.isfinite(self.radius) or self.radius <= 0.1:
            raise ValueError("Light radius must be finite and greater than 0.1")


@dataclass(frozen=True)
class Lighting:
    ambient: tuple[float, float, float]
    lights: tuple[PointLight, ...]
    shadow_resolution: int = 128

    def __post_init__(self):
        validate_rgb(self.ambient)
        if len(self.lights) > MAX_POINT_LIGHTS:
            raise ValueError(f"A level supports up to {MAX_POINT_LIGHTS} point lights")
        if self.shadow_resolution not in (64, 128, 256):
            raise ValueError("Shadow resolution must be 64, 128 or 256")
