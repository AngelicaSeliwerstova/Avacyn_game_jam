"""Prepare verified CC0 cries/growls and original Act 1 foley, with provenance."""
from array import array
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import math
from pathlib import Path
import random
import wave

import prepare_hospital_audio as pack

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'resources/audio/act0'
SOURCES = (
 dict(id='baby_cry', author='eguaus', title='baby crying',
      url='https://freesound.org/people/eguaus/sounds/321712/', start=8,seconds=14,crossfade=.7,lowpass=6000),
 dict(id='monster_growl', author='john129pats', title='Hybrid Monster Growl',
      url='https://freesound.org/people/john129pats/sounds/146558/',start=0,seconds=3.05,crossfade=0,lowpass=6500))

def write(name, samples):
    gain = .60 * 32767 / max(1e-6,max(abs(v) for v in samples))
    with wave.open(str(OUTPUT / (name+'.wav')), 'wb') as target:
        target.setparams((1,2,pack.RATE,len(samples),'NONE','not compressed'))
        target.writeframes(array('h',(round(v*gain) for v in samples)).tobytes())

def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    pack.CACHE = ROOT / 'artifacts/spotlights-audio-sources'
    pack.CACHE.mkdir(parents=True,exist_ok=True)
    pack.OUTPUT = OUTPUT
    with ThreadPoolExecutor(max_workers=2) as pool:
        downloads = list(pool.map(pack.download,SOURCES))
    pack.pygame.mixer.init(frequency=pack.RATE,size=-16,channels=1)
    try:
        manifest = [pack.prepare(*item) for item in downloads]
        source, preview, path = downloads[0]
        manifest.append(pack.prepare({**source,'id':'baby_cry_short','start':8,'seconds':2.7,'crossfade':0},preview,path))
    finally:
        pack.pygame.mixer.quit()
    rng = random.Random(1981)
    rate = pack.RATE
    write('rust_scratch',[(rng.uniform(-1,1)*.65+math.sin(math.tau*(1600*t+700*t*t))*.35)
          * min(1,i/90) * math.exp(-t*9) for i in range(round(rate*.55)) for t in (i/rate,)])
    write('lock_click',[rng.uniform(-1,1)*sum(math.exp(-max(0,t-p)*100)*(t>=p) for p in (0,.12))
          for i in range(round(rate*.32)) for t in (i/rate,)])
    write('corridor_unknown',[(math.sin(math.tau*(92*t-7*t*t))*.6+math.sin(math.tau*147*t)*.2+rng.uniform(-1,1)*.2)
          * min(1,t/.12)*math.exp(-t*2) for i in range(round(rate*2.5)) for t in (i/rate,)])
    for name in ('rust_scratch','lock_click','corridor_unknown'):
        path=OUTPUT/(name+'.wav')
        manifest.append(dict(file=path.name,author='Avacyn game project',license='CC0-1.0',
                             processing='Original procedural foley; fixed seed; mono PCM 44.1 kHz/16-bit.',sha256=sha256(path.read_bytes()).hexdigest()))
    (OUTPUT/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Act 1 audio prepared.',flush=True)

if __name__=='__main__': main()
