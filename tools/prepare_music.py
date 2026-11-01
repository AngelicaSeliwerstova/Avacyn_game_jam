"""Download openly licensed music and a piano discovery cue; prepare offline PCM assets."""

from array import array
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import wave

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from prepare_hospital_audio import fetch


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "artifacts/music-sources"
OUTPUT = ROOT / "resources/audio/music"
RATE = 44100
SOURCES = (
    {"id": "hospital_theme", "cache": "theme", "author": "Tarush Singhal",
     "title": "PS2 horror / mystery ambient theme",
     "url": "https://opengameart.org/content/ps2-horror-mystery-ambient-theme",
     "download_url": "https://opengameart.org/sites/default/files/amb.mp3",
     "license": "CC0-1.0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
     "crossfade": 4.0},
    {"id": "blood_sting", "cache": "piano", "author": "MouthlessGames",
     "title": "Creepy Piano Sfx — bam.mp3",
     "url": "https://opengameart.org/content/creepy-piano-sfx",
     "download_url": "https://opengameart.org/sites/default/files/bam_0.mp3",
     "license": "CC-BY-3.0", "license_url": "https://creativecommons.org/licenses/by/3.0/",
     "seconds": 3.6, "crossfade": 0.0},
)


def prepare(source):
    page_path = CACHE / f"{source['cache']}.html"
    path = CACHE / f"{source['cache']}.mp3"
    if not page_path.exists():
        page_path.write_bytes(fetch(source["url"]))
    if source["license_url"].removeprefix("https://") not in page_path.read_text(encoding="utf-8"):
        raise ValueError(f"License not confirmed: {source['url']}")
    if not path.exists():
        path.write_bytes(fetch(source["download_url"]))
    samples = array("h", pygame.mixer.Sound(str(path)).get_raw())
    if "seconds" in source:
        samples = samples[:round(source["seconds"] * RATE)]
    mean = sum(samples) / len(samples)
    clip = [value - mean for value in samples]
    overlap = round(source["crossfade"] * RATE)
    if overlap:
        seam = [a * math.cos(i / (overlap - 1) * math.pi / 2)
                + b * math.sin(i / (overlap - 1) * math.pi / 2)
                for i, (a, b) in enumerate(zip(clip[-overlap:], clip[:overlap]))]
        clip = clip[overlap:-overlap] + seam
    else:
        # Keep the attack immediate and let this single piano hit decay gently.
        for i in range(len(clip)):
            clip[i] *= min(1, i / (RATE * 0.004), (len(clip) - 1 - i) / RATE)
    rms = math.sqrt(sum(value * value for value in clip) / len(clip))
    gain = min(0.12 * 32767 / max(1, rms), 0.62 * 32767 / max(1, max(abs(v) for v in clip)))
    pcm = array("h", (round(value * gain) for value in clip))
    output = OUTPUT / f"{source['id']}.wav"
    with wave.open(str(output), "wb") as target:
        target.setparams((1, 2, RATE, len(pcm), "NONE", "not compressed"))
        target.writeframes(pcm.tobytes())
    print(f"{output.name}: {len(pcm) / RATE:.3f}s", flush=True)
    return {**{key: value for key, value in source.items() if key != "cache"},
            "verified_date": "2026-11-01", "file": output.name,
            "duration": len(pcm) / RATE, "source_sha256": sha256(path.read_bytes()).hexdigest(),
            "sha256": sha256(output.read_bytes()).hexdigest(),
            "processing": "MP3 decoded to mono 44100 Hz/16-bit PCM; DC removal, RMS/peak leveling; "
                          "4-second equal-power loop crossfade for music; 3.6-second excerpt and 1-second tail fade for cue."}


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    pygame.mixer.init(frequency=RATE, size=-16, channels=1)
    try:
        manifest = [prepare(source) for source in SOURCES]
        (OUTPUT / "sources.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    finally:
        pygame.mixer.quit()


if __name__ == "__main__":
    main()
