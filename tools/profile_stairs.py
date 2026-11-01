"""Profile CPU updates near the reported second-floor stair landing (no renderer).

Run: .venv/Scripts/python.exe tools/profile_stairs.py --frames 90
The fixed 30 Hz replay includes the player, moving companion, interactions and
camera selection. Its CPU times are not an estimate of rendered frame rate.
"""
import argparse
import cProfile
from pathlib import Path
import pstats
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import glm
from config import settings
from engine.input.state import InputState
from game.campaign import Campaign


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames',type=int,default=90)
    args=parser.parse_args()
    if args.frames<=0: parser.error('--frames must be positive')
    settings.AUDIO_ENABLED=False
    scene=Campaign().load_level('start')
    session=scene.session
    session.dialog=None
    session.stop_dialogue_voice()
    session._queue.clear()
    session._flags.update(('act0:transformed','act0:reception'))
    scene.player.body._position=glm.vec3(-10.64,4.8,7.97)
    session.companions[0].body._position=glm.vec3(-11.3,4.8,7.5)
    def replay():
        for _ in range(args.frames):
            for obj in scene.level.objects: obj.update(1/30)
            scene.player.update(1/30,InputState(forward=1))
            for system in scene.systems: system.update(1/30)
    profile=cProfile.Profile()
    started=time.perf_counter()
    try:
        profile.runcall(replay)
        print(f'{args.frames} CPU updates with profiler: {(time.perf_counter()-started)*1000/args.frames:.2f} ms/update')
        pstats.Stats(profile).strip_dirs().sort_stats('cumtime').print_stats(25)
    finally:
        session.release()

if __name__=='__main__': main()
