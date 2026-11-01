"""Measure exported voices and synchronize automatic subtitles with each WAV."""
from hashlib import sha256
import json
from pathlib import Path
import wave

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'resources/story/hospital/acts/act0/dialogue.json'
data=json.loads(path.read_text(encoding='utf-8'))
manifest=[]
for group in ('cradle_memory','memory_outro_first','memory_outro_second'):
    for index,line in enumerate(data[group],1):
        name=f'{group}_{index:02}.wav'
        audio=ROOT/'resources/audio/act0'/name
        with wave.open(str(audio),'rb') as wav:
            duration=wav.getnframes()/wav.getframerate()
        line.update(audio='act0/'+name,seconds=round(duration+.25,4))
        manifest.append(dict(file=name,seconds=duration,speaker=line['speaker'],text=line['text'],
            voice='Microsoft Irina Desktop (ru-RU), Windows System.Speech',
            processing='Offline synthesized voice; daughter +18% pitch/+7% rate; mother -10%/-4%; hero -3%/-14%.',
            sha256=sha256(audio.read_bytes()).hexdigest()))
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'resources/audio/act0/voices.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Voice timings updated.')
