"""Hospital room tones, positional equipment and door sounds from editable data."""

import json
import math
from pathlib import Path
import random

import pygame

from config import settings
from game.audio_channels import ENVIRONMENT_CHANNELS, MIXER_CHANNELS, RESERVED_CHANNELS, STORY_LOOP_CHANNELS


AUDIO_ROOT = Path(__file__).resolve().parents[1] / "resources/audio"
CONFIG_PATH = AUDIO_ROOT / "hospital/ambience.json"


def load_audio_profile(name, path=CONFIG_PATH):
    data = json.loads(path.read_text(encoding="utf-8"))

    def check(ok, field, message):
        if not ok:
            raise ValueError(f"{path}:{field}: {message}")

    def volume(value, field):
        check(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1, field, "volume must be in 0..1")

    def interval(value, field):
        check(isinstance(value, list) and len(value) == 2
              and all(type(v) in (int, float) and math.isfinite(v) for v in value)
              and 0 < value[0] <= value[1], field, "expected a positive [min, max] interval")

    check(data.get("version") == 1, "version", "unsupported audio format")
    sounds = data.get("sounds")
    check(isinstance(sounds, dict) and sounds, "sounds", "expected named sound files")
    for sound_id, filename in sounds.items():
        check(isinstance(filename, str) and bool(filename), sound_id, "expected a filename")
        source = (AUDIO_ROOT / filename).resolve()
        check(source.is_relative_to(AUDIO_ROOT.resolve()), sound_id, "sound must stay inside resources/audio")
        check(source.is_file(), sound_id, f"missing sound file {filename}")
    check(isinstance(data.get("profiles"), dict) and name in data["profiles"], "profiles", f"unknown profile {name!r}")
    profile = data["profiles"][name]
    check(isinstance(profile, dict), name, "expected a profile object")
    loops = profile.get("loops")
    check(isinstance(loops, list) and len(loops) <= 3, name + ".loops", "at most three background loops are supported; channel 3 is for breathing")
    for i, loop in enumerate(loops):
        check(isinstance(loop, dict) and loop.get("sound") in sounds, f"{name}.loops[{i}]", "unknown loop sound")
        volume(loop.get("volume"), f"{name}.loops[{i}].volume")
    for field in ("door_volume", "random_volume", "breathing_volume"):
        volume(profile.get(field), name + "." + field)
    interval(profile.get("random_interval"), name + ".random_interval")
    check(isinstance(profile.get("random_sounds"), list)
          and all(sound in sounds for sound in profile["random_sounds"]), name + ".random_sounds", "unknown random sound")
    check("creak" in sounds, "sounds.creak", "door sound is required")
    check("breathing" in sounds, "sounds.breathing", "breathing sound is required")
    check(isinstance(profile.get("emitters"), list), name + ".emitters", "expected equipment emitters")
    for i, emitter in enumerate(profile["emitters"]):
        field = f"{name}.emitters[{i}]"
        check(isinstance(emitter, dict) and emitter.get("sound") in sounds, field, "unknown equipment sound")
        point = emitter.get("position")
        check(isinstance(point, list) and len(point) == 3
              and all(type(v) in (int, float) and math.isfinite(v) for v in point), field, "position needs three finite coordinates")
        check(type(emitter.get("radius")) in (int, float) and math.isfinite(emitter["radius"])
              and emitter["radius"] > 0, field, "radius must be positive")
        volume(emitter.get("volume"), field + ".volume")
        interval(emitter.get("interval"), field + ".interval")
    return sounds, profile


class HospitalSoundBank:
    """Reserve channels so footsteps never steal a long-running background loop."""

    def __init__(self, paths):
        self._paths = paths
        self._sounds, self._loops, self._effects = {}, {}, {}
        self._loop_sounds = {}
        self._ready = self._unavailable = False

    def _ensure(self):
        if self._unavailable or not pygame.get_init():
            return False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            if not self._ready:
                pygame.mixer.set_num_channels(max(MIXER_CHANNELS, pygame.mixer.get_num_channels()))
                pygame.mixer.set_reserved(RESERVED_CHANNELS)
                self._ready = True
            return True
        except pygame.error:
            self._unavailable = True
            return False

    def _sound(self, sound_id):
        if sound_id not in self._sounds:
            self._sounds[sound_id] = pygame.mixer.Sound(str(AUDIO_ROOT / self._paths[sound_id]))
        return self._sounds[sound_id]

    def loop(self, slot, sound_id, left, right):
        if not self._ensure():
            return
        try:
            channel = self._loops.setdefault(slot, pygame.mixer.Channel(slot))
            if not channel.get_busy() or self._loop_sounds.get(slot) != sound_id:
                channel.set_volume(left, right)
                channel.play(self._sound(sound_id), loops=-1, fade_ms=1200)
                self._loop_sounds[slot] = sound_id
            channel.set_volume(left, right)
        except (pygame.error, OSError):
            self._unavailable = True

    def play(self, sound_id, left, right):
        if max(left, right) < 0.005 or not self._ensure():
            return
        try:
            channel = next((pygame.mixer.Channel(i) for i in ENVIRONMENT_CHANNELS
                            if not pygame.mixer.Channel(i).get_busy()), None)
            if channel is None:
                return
            sound = self._sound(sound_id)
            channel.set_volume(left, right)
            channel.play(sound)
            channel.set_volume(left, right)
            self._effects[channel] = (left, right)
        except (pygame.error, OSError):
            self._unavailable = True

    def stop_loop(self, slot):
        channel = self._loops.pop(slot, None)
        self._loop_sounds.pop(slot, None)
        if channel is not None and pygame.mixer.get_init():
            channel.stop()

    def duck_effects(self, gain):
        if not self._ready or not pygame.mixer.get_init():
            return
        for channel, (left, right) in tuple(self._effects.items()):
            if channel.get_busy():
                channel.set_volume(left * gain, right * gain)
            else:
                del self._effects[channel]

    def stop_effects(self):
        if self._ready and pygame.mixer.get_init():
            for channel in self._effects:
                channel.stop()
        self._effects.clear()

    def stop(self):
        self.stop_effects()
        if self._ready and pygame.mixer.get_init():
            for channel in self._loops.values():
                channel.stop()
        self._loops.clear()
        self._loop_sounds.clear()
        self._sounds.clear()


class HospitalAudioSystem:
    def __init__(self, level, player, session, *, profile=None, sounds=None, rng=None):
        paths, self.profile = load_audio_profile(profile or level.audio_profile)
        self.player, self.session = player, session
        self._story_sources = []
        book = getattr(session, "book", None)
        if book is not None:
            for act in book.acts.values():
                if not book.enabled(act.id):
                    continue
                loop_slots = iter(STORY_LOOP_CHANNELS)
                for source in act.data.get("audio_sources", []):
                    sound = f"story:{act.id}:{source['id']}"
                    paths[sound] = source["file"]
                    self._story_sources.append({**source, "act": act.id, "sound": sound,
                                                "slot": next(loop_slots) if source["loop"] else None})
        self.sounds = sounds if sounds is not None else HospitalSoundBank(paths)
        self._rng = rng if rng is not None else random.Random()
        self._doors = tuple(obj for obj in level.objects if obj.rotation_pivot is not None and "open" in obj.states)
        self._door_states = {obj.name: obj.state_name for obj in self._doors}
        self._emitter_timers = [self._rng.uniform(*item["interval"]) for item in self.profile["emitters"]]
        self._random_timer = self._rng.uniform(*self.profile["random_interval"])
        self._paused = self._started = self._released = False
        self._pending_steps = []
        self._story_timers = {item["sound"]: 0.0 for item in self._story_sources}
        self._heard_events = set()

    def _source_active(self, source):
        return (getattr(self.session.act, "id", None) == source["act"]
                and self.session._conditions(source))

    def _gain(self):
        if not settings.AUDIO_ENABLED or self.player.creator_mode or self._released:
            return 0.0
        dialog = self.session.dialog
        if dialog is not None and dialog.presentation in ("title", "blackout", "ending"):
            return 0.0
        if dialog is not None and dialog.presentation == "interference":
            return settings.AMBIENCE_VOLUME * max(0, 1 - dialog.effect_time / 1.2)
        return settings.AMBIENCE_VOLUME * (settings.AMBIENCE_DIALOGUE_GAIN if self._paused else 1.0)

    def _loops(self):
        if not self._started:
            return
        gain = self._gain()
        for i, loop in enumerate(self.profile["loops"]):
            volume = loop["volume"] * gain
            self.sounds.loop(i, loop["sound"], volume, volume)
        stress = getattr(self.player, "stair_stress_strength", 0.0)
        breathing = stress * self.profile["breathing_volume"] * gain if not self._paused else 0.0
        if breathing > 0.001:
            self.sounds.loop(3, "breathing", breathing, breathing)
        else:
            self.sounds.stop_loop(3)
        used = set()
        for source in self._story_sources:
            if source["loop"] and self._source_active(source):
                slot = source["slot"]
                used.add(slot)
                self.sounds.loop(slot, source["sound"], *self._stereo(source["position"], source["volume"], source["radius"]))
        if self._story_sources:
            for slot in set(STORY_LOOP_CHANNELS) - used:
                self.sounds.stop_loop(slot)

    def _story_tick(self, delta_time):
        events = getattr(self.player, "story_events", set())
        self._heard_events.intersection_update(events)
        for source in self._story_sources:
            if source["loop"] or not self._source_active(source):
                continue
            event = source.get("event")
            if event is not None:
                if event not in events or event in self._heard_events:
                    continue
                self._heard_events.add(event)
            else:
                self._story_timers[source["sound"]] -= delta_time
                if self._story_timers[source["sound"]] > 0:
                    continue
                self._story_timers[source["sound"]] = self._rng.uniform(*source["interval"])
            self.sounds.play(source["sound"], *self._stereo(source["position"], source["volume"], source["radius"]))

    def _stereo(self, source, volume, radius):
        listener = self.player.body.position
        dx, dy, dz = (source[i] - listener[i] for i in range(3))
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
        gain = max(0, 1 - distance / radius) ** 1.5
        if abs(dy) > 2.4:
            gain *= 0.12
        forward = self.player.camera.target - self.player.camera.position
        length = math.hypot(forward.x, forward.z)
        pan = (-forward.z * dx + forward.x * dz) / (length * max(distance, 0.001)) if length else 0
        pan = max(-1, min(1, pan))
        gain *= volume * self._gain()
        return gain * math.sqrt((1 - pan) / 2), gain * math.sqrt((1 + pan) / 2)

    def update(self, delta_time):
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Hospital audio delta time must be finite and nonnegative")
        if self._released:
            return
        for door in self._doors:
            if door.state_name != self._door_states[door.name]:
                self._door_states[door.name] = door.state_name
                if settings.AUDIO_ENABLED and not self.player.creator_mode and not self._paused:
                    position = door.states["default"].boxes[0].position
                    self.sounds.play("creak", *self._stereo(position, self.profile["door_volume"], 14))
        if not settings.AUDIO_ENABLED or self.player.creator_mode or self._paused:
            self._loops()
            return
        self._started = True
        self._loops()
        self._story_tick(delta_time)
        pending = []
        for remaining, position in self._pending_steps:
            remaining -= delta_time
            if remaining <= 0:
                self.sounds.play("distant_step", *self._stereo(position, self.profile["random_volume"], 28))
            else:
                pending.append((remaining, position))
        self._pending_steps = pending
        for i, emitter in enumerate(self.profile["emitters"]):
            self._emitter_timers[i] -= delta_time
            if self._emitter_timers[i] <= 0:
                self._emitter_timers[i] = self._rng.uniform(*emitter["interval"])
                self.sounds.play(emitter["sound"], *self._stereo(emitter["position"], emitter["volume"], emitter["radius"]))
        self._random_timer -= delta_time
        if self._random_timer <= 0:
            self._random_timer = self._rng.uniform(*self.profile["random_interval"])
            listener = self.player.body.position
            candidates = [door for door in self._doors if abs(door.rotation_pivot[1] - listener.y) < 1
                          and 6 < math.hypot(door.rotation_pivot[0] - listener.x, door.rotation_pivot[2] - listener.z) < 22]
            if candidates and self.profile["random_sounds"]:
                door = self._rng.choice(candidates)
                sound = self._rng.choice(self.profile["random_sounds"])
                position = door.states["default"].boxes[0].position
                self.sounds.play(sound, *self._stereo(position,
                                                     self.profile["random_volume"], 28))
                if sound == "distant_step":
                    self._pending_steps = [(0.5, position), (1.05, position)]

    def set_paused(self, paused):
        if self._released:
            return
        if paused:
            self._pending_steps.clear()
        self._paused = paused
        if self.player.creator_mode or not settings.AUDIO_ENABLED:
            self.sounds.stop_effects()
        else:
            self.sounds.duck_effects(self._gain() / max(0.001, settings.AMBIENCE_VOLUME))
        self._loops()

    def release(self):
        self._released = True
        self.sounds.stop()
