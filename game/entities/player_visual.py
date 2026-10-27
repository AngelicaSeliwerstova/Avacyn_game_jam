from dataclasses import replace
import math

from engine.scene.box import Box
from engine.scene.object import ObjectState, SceneObject


class PlayerVisual:
    """Временный персонаж из блоков, пока нет загрузки внешних моделей."""

    def __init__(self, player):
        self.player = player
        self.scene_object = SceneObject("player_visual", {"default": ObjectState(collidable=False)},
                                        entity=player, static_shadows=False)
        self._phase = 0.0
        self._pose = None

    def update(self, delta_time, visible):
        body = self.player.body
        moving = body.grounded and body.horizontal_speed > 0.05
        if moving:
            self._phase = (self._phase + body.horizontal_speed * delta_time * 7) % math.tau
        stride = math.sin(self._phase) * 0.10 if moving else 0.0
        pose = (self.player.transform, body.height, stride, visible)
        if pose == self._pose:
            return
        self._pose = pose
        if not visible:
            self.scene_object.set_geometry(())
            return
        height_scale = body.height / body.standing_height
        parts = [((0, 1.08, 0), (0.34, 0.64, 0.24), "rust"),
                 ((0, 1.55, 0), (0.26, 0.30, 0.26), "plaster"),
                 ((0, 1.73, 0.01), (0.28, 0.06, 0.28), "asphalt")]
        for side in (-1, 1):
            parts.extend((((side * 0.11, 0.41, side * stride), (0.15, 0.66, 0.18), "asphalt"),
                          ((side * 0.11, 0.07, side * stride - 0.035), (0.17, 0.14, 0.27), "wood"),
                          ((side * 0.23, 1.05, -side * stride), (0.12, 0.58, 0.16), "rust")))
        boxes = []
        for (x, y, z), (w, h, d), material in parts:
            box = Box((x, y * height_scale, z), (w, h * height_scale, d), material=material, local_texture=True)
            box = box.rotated_around((0, 0, 0), self.player.transform.rotation[1])
            boxes.append(replace(box, position=tuple(p + offset for p, offset in
                                                    zip(self.player.transform.position, box.position))))
        self.scene_object.set_geometry(tuple(boxes))
