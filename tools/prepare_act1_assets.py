"""Create original music-box/foley audio and simple painted story textures."""
from array import array
import math
from pathlib import Path
import random
import wave
import pygame

ROOT = Path(__file__).resolve().parents[1]
RATE = 44100


def write_audio(name, samples):
    path = ROOT / "resources/audio/story" / f"{name}.wav"
    path.parent.mkdir(parents=True, exist_ok=True)
    gain = 0.58 * 32767 / max(1e-6, max(abs(value) for value in samples))
    pcm = array("h", (round(value * gain) for value in samples))
    with wave.open(str(path), "wb") as file:
        file.setparams((1, 2, RATE, len(pcm), "NONE", "not compressed"))
        file.writeframes(pcm.tobytes())


def main():
    notes = (76, 71, 74, 79, 76, 71, 72, 67, 69, 76, 74, 71,
             76, 71, 74, 79, 81, 79, 76, 74, 72, 71, 69, 64)
    music = [0.0] * (RATE * 16)
    for index, note in enumerate(notes):
        start = round(index * 0.60 * RATE)
        frequency = 440 * 2 ** ((note - 69) / 12)
        for i in range(round(RATE * 1.45)):
            if start + i >= len(music):
                break
            t = i / RATE
            attack = min(1, t / 0.004)
            value = (math.sin(math.tau * frequency * t) * math.exp(-t * 3.2)
                     + 0.22 * math.sin(math.tau * frequency * 2.01 * t) * math.exp(-t * 5.0)
                     + 0.08 * math.sin(math.tau * frequency * 3.97 * t) * math.exp(-t * 8.0))
            music[start + i] += attack * value
    for i in range(len(music)):
        music[i] *= min(1, i / 80, (len(music) - 1 - i) / (RATE * 0.3))
    write_audio("music_box", music)
    rng = random.Random(313)
    write_audio("clock_tick", [rng.uniform(-1, 1) * math.exp(-i / (RATE * 0.011))
        * min(1, i / 20) for i in range(round(RATE * 0.18))])
    write_audio("tv_static", [rng.uniform(-1, 1) * min(1, i / 300, (RATE - i - 1) / 300)
        for i in range(RATE)])
    write_audio("lock_click", [math.sin(i * 0.74) * math.exp(-i / (RATE * 0.016))
        * min(1, i / 15) for i in range(round(RATE * 0.2))])
    folder = ROOT / "resources/textures/story"
    folder.mkdir(parents=True, exist_ok=True)
    for suffix in ("a", "b"):
        image = pygame.Surface((256, 144))
        for y in range(144):
            for x in range(256):
                v = rng.randrange(35, 160) if y % 3 else rng.randrange(10, 50)
                image.set_at((x, y), (v, v, max(0, v - 10)))
        pygame.image.save(image, str(folder / f"tv_static_{suffix}.png"))
    memory = pygame.Surface((256, 144))
    memory.fill((127, 111, 81))
    pygame.draw.rect(memory, (77, 66, 52), (0, 105, 256, 39))
    pygame.draw.rect(memory, (167, 153, 111), (12, 18, 54, 60))
    pygame.draw.line(memory, (70, 64, 45), (39, 18), (39, 78), 3)
    pygame.draw.line(memory, (70, 64, 45), (12, 48), (66, 48), 3)
    pygame.draw.rect(memory, (81, 71, 55), (195, 30, 40, 80))
    pygame.draw.circle(memory, (48, 41, 32), (112, 43), 13)
    pygame.draw.polygon(memory, (48, 41, 32), ((105, 54), (119, 54), (131, 107), (92, 107)))
    pygame.draw.circle(memory, (67, 51, 35), (155, 76), 8)
    pygame.draw.polygon(memory, (67, 51, 35), ((150, 83), (160, 83), (167, 112), (143, 112)))
    pygame.draw.line(memory, (48, 41, 32), (122, 65), (149, 91), 5)
    for y in range(0, 144, 3):
        pygame.draw.line(memory, (56, 49, 36), (0, y), (256, y))
    pygame.image.save(memory, str(folder / "tv_memory.png"))
    drawing = pygame.Surface((256, 192))
    drawing.fill((214, 199, 158))
    pygame.draw.rect(drawing, (95, 123, 142), (28, 80, 87, 83), 4)
    pygame.draw.lines(drawing, (153, 66, 53), False, ((17, 80), (71, 30), (126, 80)), 5)
    pygame.draw.rect(drawing, (105, 83, 69), (58, 119, 26, 44), 4)
    for x, y, radius, height in ((158, 92, 12, 62), (211, 118, 8, 37)):
        color = (91, 71, 68)
        pygame.draw.circle(drawing, color, (x, y), radius, 3)
        pygame.draw.line(drawing, color, (x, y + radius), (x, y + height), 3)
        pygame.draw.line(drawing, color, (x - 14, y + 28), (x + 14, y + 28), 3)
        pygame.draw.line(drawing, color, (x, y + height), (x - 12, y + height + 17), 3)
        pygame.draw.line(drawing, color, (x, y + height), (x + 12, y + height + 17), 3)
    pygame.image.save(drawing, str(folder / "drawing.png"))
    clock = pygame.Surface((192, 192))
    clock.fill((52, 56, 49))
    pygame.draw.circle(clock, (205, 198, 169), (96, 96), 87)
    for i in range(12):
        a = math.tau * i / 12
        pygame.draw.line(clock, (55, 58, 49), (96 + math.sin(a) * 74, 96 - math.cos(a) * 74),
                         (96 + math.sin(a) * 81, 96 - math.cos(a) * 81), 3)
    pygame.draw.line(clock, (55, 58, 49), (96, 96), (125, 76), 7)
    pygame.draw.line(clock, (55, 58, 49), (96, 96), (137, 127), 4)
    pygame.image.save(clock, str(folder / "clock.png"))
    print("Act 1 audio and story textures prepared")


if __name__ == "__main__":
    main()
