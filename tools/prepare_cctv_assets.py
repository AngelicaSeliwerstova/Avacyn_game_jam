"""Capture four anonymous staged figures on the game's actual hospital staircase."""
from array import array
from dataclasses import replace
import math
from pathlib import Path
import random
import sys
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import glm
import pygame
from engine.rendering.renderer import Renderer
from engine.scene.box import Box
from engine.scene.camera import Camera
from engine.scene.object import ObjectState, SceneObject
from game.campaign import Campaign
from main import run_session

ROOT = Path(__file__).resolve().parents[1]


def figure(x, z, *, shade=0.48, facing=-1, pose="idle", lean=0, pendant=False):
    base = glm.vec3(x, 4.8, z)
    rotation = glm.angleAxis(math.radians(lean), glm.vec3(0, 0, 1))
    boxes = []
    color = (shade * 0.86, shade, shade * 0.9)

    def point(p):
        return base + rotation * glm.vec3(p)

    def part(p, size):
        boxes.append(Box(tuple(point(p)), size, color=color, emission=(0.11, 0.12, 0.11),
                         orientation=(rotation.w, rotation.x, rotation.y, rotation.z)))

    def limb(a, b, width=0.1):
        pa, pb = point(a), point(b)
        direction = pb - pa
        unit = glm.normalize(direction)
        axis = glm.cross(glm.vec3(0, 1, 0), unit)
        q = glm.normalize(glm.quat(1 + glm.dot(glm.vec3(0, 1, 0), unit), axis.x, axis.y, axis.z))
        boxes.append(Box(tuple((pa + pb) / 2), (width, glm.length(direction), width), color=color,
                         emission=(0.11, 0.12, 0.11), orientation=(q.w, q.x, q.y, q.z)))

    part((0, 1.52, 0), (0.23, 0.28, 0.23))
    part((0, 1.13, 0), (0.35, 0.5, 0.25))
    part((0, 0.76, 0), (0.42, 0.3, 0.3))
    if pendant:
        for p, size in (((0, 1.15, .15), (.10, .13, .035)),
                        ((-.07, 1.29, .14), (.025, .20, .025)),
                        ((.07, 1.29, .14), (.025, .20, .025))):
            boxes.append(Box(tuple(point(p)), size, color=(.87, .73, .31), emission=(.3, .2, .04)))
    limb((-0.1, 0.66, 0), (-0.16, 0.07, 0.03), 0.13)
    limb((0.1, 0.66, 0), (0.2, 0.07, -0.03), 0.13)
    for side in (-1, 1):
        shoulder = (0, 1.31, side * 0.2)
        if pose == "push":
            elbow, hand = (facing * 0.32, 1.3, side * 0.21), (facing * 0.65, 1.3, side * 0.19)
        elif pose == "argue":
            elbow, hand = (facing * 0.15, 1.03, side * 0.3), (facing * 0.4, 1.32, side * 0.27)
        elif pose == "fall":
            elbow, hand = (-0.23, 1.35, side * 0.38), (-0.35, 1.6, side * 0.49)
        else:
            elbow, hand = (0, 1.02, side * 0.23), (0.03, 0.8, side * 0.24)
        limb(shoulder, elbow)
        limb(elbow, hand)
    return tuple(boxes)


def make_audio():
    rate, rng = 44100, random.Random(30)
    folder = ROOT / "resources/audio/cctv"
    folder.mkdir(parents=True, exist_ok=True)

    def write(name, samples):
        gain = 0.48 * 32767 / max(0.00001, max(abs(v) for v in samples))
        with wave.open(str(folder / f"{name}.wav"), "wb") as out:
            out.setparams((1, 2, rate, len(samples), "NONE", "not compressed"))
            out.writeframes(array("h", (round(v * gain) for v in samples)).tobytes())

    def tone(notes, duration):
        return [math.sin(math.tau * notes[min(len(notes) - 1, int(i / rate / duration * len(notes)))] * i / rate)
                * math.sin(math.pi * (i % max(1, round(rate * duration / len(notes)))) / (rate * duration / len(notes))) ** 2
                for i in range(round(rate * duration))]

    write("button_click", tone([680], 0.045))
    write("correct", tone([620, 830, 1040], 0.45))
    write("incorrect", tone([230, 170], 0.32))
    write("static", [rng.uniform(-1, 1) * math.sin(math.pi * i / (rate * 0.55)) ** 2 for i in range(round(rate * 0.55))])
    write("impact", [(math.sin(math.tau * 72 * i / rate) + rng.uniform(-0.4, 0.4)) * math.exp(-i / (rate * 0.08))
                      * min(1, i / 150) for i in range(round(rate * 0.65))])


def capture():
    output = ROOT / "resources/puzzles/cctv"
    output.mkdir(parents=True, exist_ok=True)
    original_load, original_render, original_mode = Campaign.load_level, Renderer.render, pygame.display.set_mode
    staged = (
        figure(-8.5, 6.9, shade=0.34, pendant=True) + figure(-9.3, 6.9),
        figure(-9.4, 6.9, shade=0.34, pose="argue", pendant=True) + figure(-10.6, 6.9, facing=1),
        figure(-9.6, 6.9, shade=0.34, pose="push", pendant=True) + figure(-10.9, 6.9, pose="fall", lean=24),
        figure(-10.0, 6.9, shade=0.34) + (
            Box((-10.65, 4.83, 6.95), (.13, .035, .16), color=(.87, .73, .31), emission=(.5, .4, .08)),),
    )
    actors, frame = None, 0

    def load(campaign, name):
        nonlocal actors
        scene = original_load(campaign, name)
        actors = SceneObject("archive_staged_figures", {"default": ObjectState(staged[0], collidable=False)})
        level = replace(scene.level, objects=tuple(o for o in scene.level.objects if o.entity is None) + (actors,))
        return replace(scene, level=level)

    def render(renderer, window_size, *args, **kwargs):
        nonlocal frame
        actors.set_geometry(staged[frame])
        renderer._camera = Camera((-6.2, 8.6, 11.2), (-11.2, 5.35, 5.8), 58, 0.1, 150)
        kwargs.update(dialog=None, puzzle_view=None, inventory=None, hud_text="", aim_text=None,
                      player_transform=None, creator_help_text=None, camera_effect_strength=1, stress_strength=0)
        original_render(renderer, window_size, *args, **kwargs)
        raw = renderer.context.screen.read(components=3, alignment=1)
        image = pygame.transform.flip(pygame.image.fromstring(raw, window_size, "RGB"), False, True)
        crop = pygame.Rect(0, 0, window_size[0], round(window_size[0] * 9 / 16))
        crop.center = image.get_rect().center
        image = pygame.transform.scale(image.subsurface(crop), (512, 288))
        pygame.image.save(image, output / f"frame_{frame + 1:02}.png")
        frame += 1
        if frame == 4:
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    with patch.object(Campaign, "load_level", load), patch.object(Renderer, "render", render), \
            patch("pygame.display.set_mode", side_effect=lambda size, flags=0, **kw: original_mode(size, flags | pygame.HIDDEN, **kw)):
        run_session(level_name="start", creator_mode=True)


if __name__ == "__main__":
    make_audio()
    capture()
