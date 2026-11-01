"""Check fixed-camera coverage and capture actual selected gameplay shots."""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import glm
import pygame

from config import settings
from engine.collision.world3d import CollisionWorld3D
from engine.rendering.renderer import Renderer
from game.entities.player import create_player
from game.levels import create_level
from game.levels.spiral import SpiralStair


VIEWS = {
    "entrance": (0, 0, 11),
    "reception": (11.5, 0, 8),
    "plan": (13.4, 0, 2.2),
    "office_corridor": (-15, 0, -4.4),
    "doctor": (-16, 0, -10),
    "archive": (-1.8, 0, 3.2),
    "surgery_corridor": (5, 4.8, -6),
    "operating_room": (-8, 4.8, -17),
    "recovery": (10, 4.8, 4),
    "patient_corridor": (10, 9.6, -7),
    "television": (11, 9.6, -20),
    "nursery": (26, 9.6, -20),
    "ward_313": (13.5, 9.6, 5),
    "upper_landing": (-10, 9.6, 6.9),
}
VIEWS.update({f"stairs_{i}": point for i, point in enumerate(SpiralStair().walking_path()) if i % 9 == 0})


def make_player(name, open_doors=False):
    level = create_level(name)
    if open_doors:
        for obj in level.objects:
            if "open" in obj.states:
                obj.set_state("open")
                obj.update(2)
    world = CollisionWorld3D((box.collider for box in level.collision_boxes), level.floor_bounds,
                             level.base_height, objects=tuple(o for o in level.objects if o.entity is None))
    return level, create_player(level, world)


def pose(player, point):
    player.body._position = glm.vec3(point)
    player._active_camera_zone = None
    player._movement_camera_lock = False
    player._sync_transform()
    player._sync_fixed_camera()
    return player._active_camera_zone


def check_coverage(name, output):
    level, player = make_player(name, open_doors=True)
    world = player.body.world
    samples = dict(VIEWS)
    for floor, height in enumerate(level.floor_heights):
        width, depth = (42, 28) if floor == 0 else (60, 48)
        for x in range(-width // 2 + 1, width // 2, 3):
            for z in range(-depth // 2 + 1, depth // 2, 3):
                point = glm.vec3(x, height + .03, z)
                if world.is_blocked(point, settings.PLAYER_RADIUS, player.body.height):
                    continue
                support = world.support_height(point, settings.PLAYER_RADIUS, height + .08)
                if abs(support - height) > .08:
                    continue
                samples[f"grid_{floor}_{x}_{z}"] = (x, height, z)
    blind, outside = {}, {}
    for label, point in samples.items():
        zone = pose(player, point)
        eye = player._player_eye_position()
        if zone is None or player._fixed_camera_framing_score(zone, eye) is None:
            blind[label] = point
        elif not zone.contains(tuple(eye)):
            outside[label] = point
    embedded = []
    for index, zone in enumerate(level.fixed_cameras):
        lens = player._camera_view_position(zone)
        if world.is_blocked(lens, .04, .08):
            embedded.append(index)
    report = dict(level=name, cameras=len(level.fixed_cameras), samples=len(samples),
                  blind=blind, outside_zones=outside, embedded_lenses=embedded)
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{name}_coverage.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({**report, "outside_zones": len(outside)}, indent=2), flush=True)
    return report


def capture(name, output, views):
    from game.campaign import Campaign
    from main import run_session

    scene = Campaign().load_level(name)
    player = scene.player
    for obj in scene.level.objects:
        if "open" in obj.states:
            obj.set_state("open")
            obj.update(2)
    output.mkdir(parents=True, exist_ok=True)
    original_mode, original_render = pygame.display.set_mode, Renderer.render
    frame, tiles = 0, []

    def hidden_mode(size, flags=0, **kwargs):
        return original_mode(size, flags | pygame.HIDDEN, **kwargs)

    def render(renderer, window_size, *args, **kwargs):
        nonlocal frame
        label = views[frame]
        pose(player, VIEWS[label])
        kwargs.update(hud_text="", aim_text="", debug_text="", dialog=None,
                      player_transform=player.transform, camera_transition_strength=0,
                      camera_effect_strength=1, stress_strength=0)
        original_render(renderer, window_size, *args, **kwargs)
        raw = renderer.context.screen.read(components=3, alignment=1)
        surface = pygame.transform.flip(pygame.image.fromstring(raw, window_size, "RGB"), False, True)
        pygame.image.save(surface, output / f"{name}_{label}.png")
        tile = pygame.Surface((400, 325))
        tile.blit(pygame.transform.smoothscale(surface, (400, 300)), (0, 0))
        tile.blit(pygame.font.SysFont("consolas", 17).render(label, True, "white"), (8, 303))
        tiles.append(tile)
        frame += 1
        if frame == len(views):
            sheet = pygame.Surface((1600, 325 * ((len(tiles) + 3) // 4)))
            for i, tile in enumerate(tiles):
                sheet.blit(tile, ((i % 4) * 400, (i // 4) * 325))
            path = output / f"{name}_contact.png"
            pygame.image.save(sheet, path)
            print(path.resolve(), flush=True)
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    with patch("pygame.display.set_mode", side_effect=hidden_mode), \
         patch.object(Renderer, "render", render), patch.object(Campaign, "load_level", return_value=scene):
        run_session(level_name=name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", default="start", choices=("peaceful", "start", "act1", "act2"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/camera-qa"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--views", nargs="+", choices=tuple(VIEWS), default=list(VIEWS))
    args = parser.parse_args()
    if args.check:
        check_coverage(args.level, args.output_dir)
    else:
        capture(args.level, args.output_dir, args.views)
