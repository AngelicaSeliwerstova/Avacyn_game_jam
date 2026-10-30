import json
from pathlib import Path

from engine.scene.lighting import LightFlicker, SpotLight


def creator_lights_path() -> Path:
    return Path(__file__).resolve().parents[2] / "resources" / "levels" / "maze_lights.json"


def load_creator_lights(path: Path) -> tuple[SpotLight, ...]:
    if not path.exists():
        return ()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("lights"), list):
        raise ValueError(f"Creator light layout must contain a 'lights' list: {path}")
    result = []
    for index, value in enumerate(data["lights"]):
        if not isinstance(value, dict):
            raise ValueError(f"Light {index + 1} must be an object: {path}")
        try:
            flicker_data = value.get("flicker")
            if flicker_data is not None and not isinstance(flicker_data, dict):
                raise ValueError("flicker must be an object or null")
            result.append(SpotLight(
                position=tuple(value["position"]),
                direction=tuple(value.get("direction", (0.0, -1.0, 0.0))),
                color=tuple(value.get("color", (1.0, 0.78, 0.52))),
                intensity=value.get("intensity", 3.5),
                radius=value.get("radius", 9.0),
                inner_angle=value.get("inner_angle", 30.0),
                outer_angle=value.get("outer_angle", 55.0),
                shadows=value.get("shadows", True),
                flicker=LightFlicker(**flicker_data) if flicker_data is not None else None,
            ))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid light {index + 1} in {path}: {error}") from error
    return tuple(result)


def save_creator_lights(path: Path, lights: tuple[SpotLight, ...]) -> None:
    data = {
        "lights": [
            {
                "position": light.position,
                "direction": light.direction,
                "color": light.color,
                "intensity": light.intensity,
                "radius": light.radius,
                "inner_angle": light.inner_angle,
                "outer_angle": light.outer_angle,
                "shadows": light.shadows,
                "flicker": None if light.flicker is None else {
                    "interval": light.flicker.interval,
                    "duration": light.flicker.duration,
                    "minimum": light.flicker.minimum,
                    "seed": light.flicker.seed,
                },
            }
            for light in lights
        ],
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
