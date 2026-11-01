"""Attach measured, portable WAV timings to the recovered recording."""
import json
from pathlib import Path
import wave

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'resources/puzzles/cctv/archive.json'
definition = json.loads(path.read_text(encoding='utf-8'))
index = 0
for step in definition['recording']:
    if 'speaker' not in step:
        continue
    index += 1
    filename = f'cctv/voices/recording_{index:02}.wav'
    with wave.open(str(ROOT / 'resources/audio' / filename)) as audio:
        step['seconds'] = round(audio.getnframes() / audio.getframerate() + 0.6, 3)
    step['audio'] = filename
path.write_text(json.dumps(definition, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
