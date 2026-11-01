"""Cut four single footsteps per profile from the downloaded CC0 previews.

Input: artifacts/doctor_steps_source.mp3. The player uses the same shoe sounds.
Uses SDL's decoder, without requiring ffmpeg or NumPy.
"""

from array import array
import math
import os
from pathlib import Path
import shutil
import wave

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

ROOT = Path(__file__).resolve().parents[1]
RATE = 44100


def prepare(profile):
    source = pygame.mixer.Sound(str(ROOT / "artifacts" / f"{profile}_steps_source.mp3"))
    samples = array("h", source.get_raw()[:35 * RATE * 2])
    block = RATE // 100
    energy = [sum(value * value for value in samples[start:start + block]) / block
              for start in range(0, len(samples) - block, block)]
    peaks = sorted((index for index in range(5, len(energy) - 30)
                    if energy[index] == max(energy[index - 4:index + 5])), key=energy.__getitem__, reverse=True)
    selected = []
    for peak in peaks:
        if all(abs(peak - other) > 48 for other in selected):
            selected.append(peak)
        if len(selected) == 4:
            break
    if len(selected) != 4:
        raise ValueError(f"Could not identify four steps in {profile}")
    output = ROOT / "resources/audio/footsteps"
    output.mkdir(parents=True, exist_ok=True)
    for index, peak in enumerate(sorted(selected), 1):
        start = max(0, peak * block - round(RATE * 0.045))
        length = round(RATE * (0.24 if profile == "player" else 0.28))
        clip = [float(v) for v in samples[start:start + length]]
        # Remove the sharp high-frequency heel tick, retaining the body of the
        # recorded step. Forward/backward filtering avoids a timing shift.
        alpha = 1 - math.exp(-2 * math.pi * 2600 / RATE)
        for reverse in (False, True):
            filtered = 0.0
            indices = range(len(clip) - 1, -1, -1) if reverse else range(len(clip))
            for i in indices:
                filtered += alpha * (clip[i] - filtered)
                clip[i] = filtered
        for i in range(len(clip)):
            clip[i] *= min(1, i / (RATE * 0.014), (len(clip) - 1 - i) / (RATE * 0.055))
        # Dry single steps: no delayed copies that sound like repeated clicks.
        gain = 0.60 * 32767 / max(1, max(abs(v) for v in clip))
        pcm = array("h", (round(v * gain) for v in clip))
        path = output / f"{profile}_step_{index:02}.wav"
        with wave.open(str(path), "wb") as target:
            target.setparams((1, 2, RATE, len(pcm), "NONE", "not compressed"))
            target.writeframes(pcm.tobytes())
        print(f"{path.name}: source {peak / 100:.2f}s, duration {len(pcm) / RATE:.2f}s")


if __name__ == "__main__":
    pygame.mixer.init(frequency=RATE, size=-16, channels=1)
    try:
        prepare("doctor")
        for index in range(1, 5):
            root = ROOT / "resources/audio/footsteps"
            shutil.copyfile(root / f"doctor_step_{index:02}.wav", root / f"player_step_{index:02}.wav")
    finally:
        pygame.mixer.quit()
