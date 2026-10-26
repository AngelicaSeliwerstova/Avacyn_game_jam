from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RenderOptions:
    frustum_culling: bool = True
    depth_prepass: bool = True
    local_lights: bool = True
    light_cell_size: float = 4.0

    def __post_init__(self):
        if not math.isfinite(self.light_cell_size) or self.light_cell_size <= 0:
            raise ValueError("Light grid cell size must be finite and positive")
