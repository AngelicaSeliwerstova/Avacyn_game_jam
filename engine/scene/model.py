from dataclasses import dataclass, field
from pathlib import Path

import glm

from engine.scene.transform import Transform


@dataclass(frozen=True)
class ModelComponent:
    """Место для будущей GLB-модели: ссылка на ресурс и локальная трансформация.

    Не читает файл и не создаёт GPU-ресурсы. Загрузчик будет отдельной системой.
    """

    source_path: Path | None = None
    local_transform: Transform = field(default_factory=Transform)

    def __post_init__(self):
        if self.source_path is not None:
            path = Path(self.source_path)
            if path.suffix.lower() != ".glb":
                raise ValueError("Model source must use the .glb extension")
            object.__setattr__(self, "source_path", path)

    def world_matrix(self, owner: Transform) -> glm.mat4:
        return owner.matrix * self.local_transform.matrix
