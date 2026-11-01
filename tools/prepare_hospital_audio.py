"""Download verified CC0 public previews and prepare the hospital sound pack.

Run from any directory. Downloads and license evidence stay in artifacts;
processed PCM WAVs and the provenance manifest belong to resources/audio.
No additional packages beyond the game's pygame dependency are needed.
"""

from array import array
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import html
import json
import math
import os
from pathlib import Path
import re
import urllib.request
import wave

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "artifacts/hospital-audio-sources"
OUTPUT = ROOT / "resources/audio/hospital"
RATE = 44100
SOURCES = (
    {"id": "room_tone", "author": "Kinoton", "title": "Room Tone, Empty Hospital",
     "url": "https://freesound.org/people/Kinoton/sounds/670070/",
     "start": 22, "seconds": 34, "crossfade": 2, "lowpass": 4200},
    {"id": "hospital_activity", "author": "vovere", "title": "Evening in hospital.wav",
     "url": "https://freesound.org/people/vovere/sounds/388455/",
     "start": 12, "seconds": 44, "crossfade": 2, "lowpass": 1800},
    {"id": "fluorescent_buzz", "author": "kentspublicdomain",
     "title": "Flickering Fluorescent Light with Background Hum (Seamless Loop, 44100 Hz Mono)",
     "url": "https://freesound.org/people/kentspublicdomain/sounds/777053/",
     "start": 0, "seconds": 8.9, "crossfade": 0.35, "lowpass": 5000},
    {"id": "door_creak", "author": "JarredGibb", "title": "Door - Creak.wav",
     "url": "https://freesound.org/people/JarredGibb/sounds/219499/",
     "start": 0, "seconds": 0.95, "crossfade": 0, "lowpass": 3800},
    {"id": "monitor_beep", "author": "Sadiquecat", "title": "795hz monitor blip",
     "url": "https://freesound.org/people/Sadiquecat/sounds/843148/",
     "start": 0, "seconds": 0.148, "crossfade": 0, "lowpass": 5000},
    {"id": "breathing", "author": "Kuroseishin", "title": "breathing_female.wav",
     "url": "https://freesound.org/people/Kuroseishin/sounds/95567/",
     "start": 0, "seconds": 5.1, "crossfade": 0.3, "lowpass": 4500},
)


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "HospitalGameAudioPreparation/1.0"})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read(25 * 1024 * 1024 + 1)
    if len(data) > 25 * 1024 * 1024:
        raise ValueError(f"Download exceeds 25 MiB: {url}")
    return data


def download(source):
    name = source["id"]
    page_path = CACHE / f"{name}.html"
    if not page_path.exists():
        page_path.write_bytes(fetch(source["url"]))
    page = html.unescape(page_path.read_text(encoding="utf-8"))
    if "Creative Commons 0" not in page or "creativecommons.org/publicdomain/zero" not in page:
        raise ValueError(f"CC0 license not confirmed on {source['url']}")
    previews = sorted(set(re.findall(r'https://cdn\.freesound\.org/previews/[^\s"<>]+-hq\.mp3', page)))
    if len(previews) != 1:
        raise ValueError(f"Expected exactly one HQ preview on {source['url']}: {previews}")
    path = CACHE / f"{name}.mp3"
    if not path.exists():
        path.write_bytes(fetch(previews[0]))
    return source, previews[0], path


def prepare(source, preview, path):
    decoded = pygame.mixer.Sound(str(path))
    samples = array("h", decoded.get_raw())
    start = round(source["start"] * RATE)
    clip = [float(value) for value in samples[start:start + round(source["seconds"] * RATE)]]
    if len(clip) < round(source["seconds"] * RATE * 0.95):
        raise ValueError(f"Preview too short for selected excerpt: {source['id']}")
    mean = sum(clip) / len(clip)
    alpha = 1 - math.exp(-math.tau * source["lowpass"] / RATE)
    filtered = 0.0
    for i, sample in enumerate(clip):
        filtered += alpha * (sample - mean - filtered)
        clip[i] = filtered
    overlap = round(source["crossfade"] * RATE)
    if overlap:
        tail = clip[-overlap:]
        head = clip[:overlap]
        seam = [a * math.cos(i / (overlap - 1) * math.pi / 2)
                + b * math.sin(i / (overlap - 1) * math.pi / 2)
                for i, (a, b) in enumerate(zip(tail, head))]
        clip = clip[overlap:-overlap] + seam
    else:
        for i in range(len(clip)):
            clip[i] *= min(1, i / (RATE * 0.006), (len(clip) - 1 - i) / (RATE * 0.025))
    rms = math.sqrt(sum(value * value for value in clip) / len(clip))
    gain = min(0.12 * 32767 / max(1, rms), 0.62 * 32767 / max(1, max(abs(value) for value in clip)))
    pcm = array("h", (round(value * gain) for value in clip))
    output = OUTPUT / f"{source['id']}.wav"
    with wave.open(str(output), "wb") as target:
        target.setparams((1, 2, RATE, len(pcm), "NONE", "not compressed"))
        target.writeframes(pcm.tobytes())
    print(f"{output.name}: {len(pcm) / RATE:.3f}s, {output.stat().st_size} bytes", flush=True)
    return {**source, "license": "CC0-1.0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "verified_date": "2026-11-01", "preview_url": preview, "source_sha256": sha256(path.read_bytes()).hexdigest(),
            "file": output.name, "sha256": sha256(output.read_bytes()).hexdigest(), "duration": len(pcm) / RATE,
            "processing": "HQ MP3 preview decoded to mono PCM 44.1 kHz/16-bit; excerpt, DC removal, low-pass, RMS/peak leveling; equal-power loop crossfade or edge fades."}


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        downloads = list(pool.map(download, SOURCES))
    pygame.mixer.init(frequency=RATE, size=-16, channels=1)
    try:
        manifest = [prepare(*downloaded) for downloaded in downloads]
        (OUTPUT / "sources.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    finally:
        pygame.mixer.quit()


if __name__ == "__main__":
    main()
