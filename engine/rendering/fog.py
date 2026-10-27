from dataclasses import dataclass
import math


@dataclass(frozen=True)
class FogSettings:
    color: tuple[float, float, float] = (0.075, 0.10, 0.13)
    start: float = 6.0
    end: float = 30.0

    def __post_init__(self):
        if (len(self.color) != 3 or any(not math.isfinite(c) or not 0 <= c <= 1 for c in self.color)
                or not math.isfinite(self.start) or not math.isfinite(self.end)
                or not 0 <= self.start < self.end):
            raise ValueError("Fog needs an RGB color in 0..1 and finite distances 0 <= start < end")


def configure_fog(program, settings: FogSettings | None):
    program["fog_enabled"].value = settings is not None
    if settings is not None:
        program["fog_color"].value = settings.color
        program["fog_start"].value = settings.start
        program["fog_end"].value = settings.end
