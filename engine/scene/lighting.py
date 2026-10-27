from dataclasses import dataclass
import math


MAX_POINT_LIGHTS = 512
MAX_DYNAMIC_SPOT_LIGHTS = 4


def validate_rgb(color):
    if len(color) != 3 or any(not math.isfinite(c) or c < 0 for c in color):
        raise ValueError("Light colors need three finite nonnegative channels")


@dataclass(frozen=True)
class LightFlicker:
    """Редкий короткий сбой лампы; результат зависит от времени, а не числа кадров."""

    interval: float = 8.0
    duration: float = 0.7
    minimum: float = 0.3
    seed: int = 0

    def __post_init__(self):
        if (not math.isfinite(self.interval) or not math.isfinite(self.duration)
                or not 0 < self.duration < self.interval
                or not math.isfinite(self.minimum) or not 0 <= self.minimum <= 1
                or not isinstance(self.seed, int)):
            raise ValueError("Flicker needs 0 < duration < interval, minimum in 0..1 and an integer seed")

    def brightness(self, elapsed: float) -> float:
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("Light animation time must be finite and nonnegative")
        phase = ((self.seed * 1103515245 + 12345) & 0x7fffffff) / 2147483648
        local = (elapsed + phase * self.interval) % self.interval
        if local >= self.duration:
            return 1.0
        progress = local / self.duration

        def pulse(center, width):
            value = max(0.0, 1.0 - abs(progress - center) / width)
            return value * value * (3.0 - 2.0 * value)

        dip = max(pulse(0.27, 0.22), 0.7 * pulse(0.66, 0.25))
        return 1.0 - (1.0 - self.minimum) * dip


@dataclass(frozen=True)
class PointLight:
    position: tuple[float, float, float]
    color: tuple[float, float, float] = (0.65, 0.8, 1.0)
    intensity: float = 1.8
    radius: float = 9.0
    flicker: LightFlicker | None = None

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


@dataclass
class SpotLight:
    """Подвижный направленный источник. Положение и параметры можно менять каждый кадр."""

    position: tuple[float, float, float]
    direction: tuple[float, float, float]
    color: tuple[float, float, float] = (1.0, 0.96, 0.85)
    intensity: float = 4.5
    radius: float = 18.0
    inner_angle: float = 12.0
    outer_angle: float = 24.0
    enabled: bool = True
    shadows: bool = True

    def __post_init__(self):
        self.validate()

    def validate(self):
        if (len(self.position) != 3 or len(self.direction) != 3
                or not all(math.isfinite(v) for v in (*self.position, *self.direction))
                or math.hypot(*self.direction) == 0):
            raise ValueError("Spotlight needs a finite position and a nonzero finite direction")
        validate_rgb(self.color)
        if (not math.isfinite(self.intensity) or self.intensity < 0
                or not math.isfinite(self.radius) or self.radius <= 0.1
                or not 0 <= self.inner_angle < self.outer_angle < 89):
            raise ValueError("Spotlight needs nonnegative intensity, radius > 0.1 and 0 <= inner < outer < 89")
