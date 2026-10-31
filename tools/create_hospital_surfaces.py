"""Build deterministic, seamless low-resolution hospital material swatches."""

import math
from pathlib import Path
import random

import pygame


SURFACES = {
    "paint_ivory": ((204, 201, 183), "paint"),
    "paint_sage": ((154, 176, 160), "paint"),
    "paint_mint": ((166, 193, 179), "paint"),
    "enamel_white": ((204, 212, 201), "enamel"),
    "ceramic_white": ((222, 222, 208), "enamel"),
    "brushed_steel": ((157, 169, 164), "steel"),
    "oak_veneer": ((139, 107, 72), "wood"),
    "vinyl_burgundy": ((100, 49, 41), "vinyl"),
    "vinyl_sage": ((97, 130, 113), "vinyl"),
    "linen_ivory": ((216, 214, 193), "linen"),
    "blanket_sage": ((106, 136, 113), "linen"),
    "curtain_sage": ((146, 177, 159), "curtain"),
    "linoleum_sage": ((142, 162, 150), "linoleum"),
    "ceiling_clean": ((207, 209, 196), "ceiling"),
    "tile_mint_clean": ((174, 193, 181), "tile"),
    "tile_cream_clean": ((207, 205, 185), "tile"),
    "linoleum_blue_clean": ((145, 162, 164), "linoleum"),
    "vinyl_burgundy_worn": ((77, 40, 33), "worn_fabric"),
    "vinyl_sage_worn": ((77, 103, 86), "worn_fabric"),
    "linen_worn": ((166, 163, 139), "worn_fabric"),
    "blanket_worn": ((81, 106, 84), "worn_fabric"),
    "curtain_worn": ((108, 133, 112), "worn_fabric"),
}


def generate(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for index, (name, (base, kind)) in enumerate(SURFACES.items()):
        rng = random.Random(701 + index)
        surface = pygame.Surface((256, 256))
        for y in range(256):
            for x in range(256):
                u, v = x / 256, y / 256
                cloud = math.sin(2 * math.pi * (u + 2 * v)) + 0.5 * math.cos(2 * math.pi * (3 * u - v))
                value = cloud * 1.5 + rng.uniform(-2, 2)
                if kind == "steel":
                    value += 4 * math.sin(2 * math.pi * 64 * v) + rng.uniform(-2, 2)
                elif kind == "wood":
                    value += 9 * math.sin(2 * math.pi * (12 * u + 0.15 * math.sin(2 * math.pi * v)))
                    value += 4 * math.cos(2 * math.pi * 37 * u)
                elif kind == "vinyl":
                    value += 3 * math.sin(2 * math.pi * 64 * u) * math.cos(2 * math.pi * 64 * v)
                elif kind == "linen":
                    value += 4 if (x // 2 + y // 2) % 2 else -4
                elif kind == "worn_fabric":
                    value += (4 if (x // 2 + y // 2) % 2 else -4) + min(0, cloud) * 12
                elif kind == "curtain":
                    value += 6 * math.sin(2 * math.pi * 8 * u) + 2 * math.cos(2 * math.pi * 64 * v)
                elif kind == "linoleum":
                    value += 4 * math.sin(2 * math.pi * (5 * u + 3 * v)) * math.cos(2 * math.pi * (2 * u - 4 * v))
                elif kind in ("ceiling", "tile"):
                    period = 128 if kind == "ceiling" else 64
                    seam = min(x % period, y % period)
                    value += -28 if seam < 2 else (4 if seam < 4 else 0)
                elif kind == "enamel":
                    value *= 0.5
                surface.set_at((x, y), tuple(max(0, min(255, round(c + value))) for c in base))
        for size in (128, 256):
            image = surface if size == 256 else pygame.transform.smoothscale(surface, (size, size))
            pygame.image.save(image, root / f"{name}_{size}.png")
    print(f"Generated {len(SURFACES) * 2} hospital surface textures in {root}")


if __name__ == "__main__":
    generate(Path(__file__).resolve().parents[1] / "resources/textures/surfaces")
