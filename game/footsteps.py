"""Distance-triggered footsteps with lightweight stereo positioning."""

from pathlib import Path
import math
import random

import pygame

from config import settings
from game.audio_channels import FIRST_FOOTSTEP_CHANNEL, MIXER_CHANNELS
from game.entities.companion import Companion
from game.entities.enemy import Enemy


class FootstepSounds:
    def __init__(self):
        self._sounds = {}
        self._last = {}
        self._channels = []
        self._voices = {}
        self._unavailable = False
        self._rng = random.Random()

    def play(self, profile, left, right, *, voice=None):
        if self._unavailable or not pygame.get_init():
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            if pygame.mixer.get_num_channels() < MIXER_CHANNELS:
                pygame.mixer.set_num_channels(MIXER_CHANNELS)
            if profile not in self._sounds:
                root = Path(__file__).resolve().parents[1] / "resources/audio/footsteps"
                self._sounds[profile] = tuple(pygame.mixer.Sound(str(root / f"{profile}_step_{i:02}.wav"))
                                              for i in range(1, 5))
            choices = [i for i in range(4) if i != self._last.get(profile)]
            index = self._rng.choice(choices)
            self._last[profile] = index
            # A new step replaces this actor's previous tail instead of stacking
            # several full-volume impacts when the player moves quickly.
            previous = self._voices.get(voice)
            if voice is not None and previous is not None and previous.get_busy():
                previous.fadeout(20)
            # Leave ambience, breathing and dialogue channels untouched.
            channel = next((pygame.mixer.Channel(i) for i in range(FIRST_FOOTSTEP_CHANNEL, pygame.mixer.get_num_channels())
                            if not pygame.mixer.Channel(i).get_busy()), None)
            if channel is None:
                return
            variation = self._rng.uniform(0.88, 1.0)
            channel.play(self._sounds[profile][index])
            channel.set_volume(left * variation, right * variation)
            if voice is not None:
                for owner, owned_channel in tuple(self._voices.items()):
                    if owner != voice and owned_channel == channel:
                        del self._voices[owner]
                self._voices[voice] = channel
            self._channels = [c for c in self._channels if c.get_busy()]
            if channel not in self._channels:
                self._channels.append(channel)
        except (pygame.error, OSError):
            # A missing audio device must not prevent playing the game.
            self._unavailable = True

    def stop(self):
        if pygame.mixer.get_init():
            for channel in self._channels:
                channel.stop()
        self._channels.clear()
        self._voices.clear()


class FootstepSystem:
    def __init__(self, level, player, sounds=None):
        self.player = player
        self.sounds = sounds if sounds is not None else FootstepSounds()
        self._actors = [(player, "player")]
        self._actors.extend((obj.entity, "doctor") for obj in level.objects
                            if isinstance(obj.entity, (Companion, Enemy)))
        self._positions = {id(actor): tuple(actor.body.position) for actor, _ in self._actors if actor.body}
        self._travel = {}
        self._paused = False

    def set_paused(self, paused):
        if paused and not self._paused:
            self.sounds.stop()
            self._travel.clear()
        self._paused = paused

    def release(self):
        self.sounds.stop()

    def update(self, delta_time):
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Footstep delta time must be finite and nonnegative")
        muted = (not settings.AUDIO_ENABLED or self._paused or self.player.creator_mode)
        for actor, profile in self._actors:
            body = actor.body
            if body is None:
                continue
            key = id(actor)
            position = tuple(body.position)
            previous = self._positions.get(key, position)
            self._positions[key] = position
            distance = math.hypot(position[0] - previous[0], position[2] - previous[2])
            if (muted or not body.grounded or body.horizontal_speed < 0.15
                    or distance > max(2, body.horizontal_speed * delta_time * 3)):
                self._travel[key] = 0
                continue
            crouched = body.height < body.standing_height * 0.85
            stride = 1.05 if crouched else (2.5 if body.horizontal_speed > 4.8 else 1.85)
            if profile == "doctor":
                stride = 1.85
            travel = self._travel.get(key, stride * 0.6) + distance
            if travel >= stride:
                self._travel[key] = travel % stride
                volume = settings.FOOTSTEP_PLAYER_VOLUME if profile == "player" else settings.FOOTSTEP_DOCTOR_VOLUME
                if crouched:
                    volume *= 0.4
                left, right = self._stereo(actor, volume)
                if max(left, right) > 0.01:
                    self.sounds.play(profile, left, right, voice=key)
            else:
                self._travel[key] = travel

    def _stereo(self, actor, volume):
        if actor is self.player:
            # Match the centered positional mix used for the doctor's steps.
            return volume / math.sqrt(2), volume / math.sqrt(2)
        listener, source = self.player.body.position, actor.body.position
        dx, dy, dz = (source[i] - listener[i] for i in range(3))
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
        gain = max(0, 1 - distance / settings.FOOTSTEP_HEARING_RANGE) ** 1.5
        if abs(dy) > 2.4:
            gain *= 0.2
        forward = self.player.camera.target - self.player.camera.position
        length = math.hypot(forward.x, forward.z)
        pan = ((-forward.z * dx + forward.x * dz) / (length * max(distance, 0.001))) if length else 0
        pan = max(-1, min(1, pan))
        return (volume * gain * math.sqrt((1 - pan) / 2),
                volume * gain * math.sqrt((1 + pan) / 2))
