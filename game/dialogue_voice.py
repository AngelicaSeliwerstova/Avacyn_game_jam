"""Original short synthesized talk blips and a character-synchronous typewriter."""

from array import array
from dataclasses import dataclass
import math

import pygame

from config import settings
from game.audio_channels import DIALOGUE_CHANNEL, MIXER_CHANNELS, RESERVED_CHANNELS


@dataclass(frozen=True)
class DialogueVoiceProfile:
    pitch_hz: float = 700
    pitch_variation: float = 0.07
    volume: float = 0.7
    chars_per_second: float = 36
    enabled: bool = True

    @classmethod
    def from_data(cls, data=None):
        if data is False:
            return cls(enabled=False)
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("voice must be an object or false")
        if data.keys() - {"pitch_hz", "pitch_variation", "volume", "chars_per_second"}:
            raise ValueError("unknown voice setting")
        profile = cls(**data)
        for field, low, high in (("pitch_hz", 150, 2000), ("pitch_variation", 0, 0.3),
                                 ("volume", 0, 1), ("chars_per_second", 5, 120)):
            value = getattr(profile, field)
            if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"voice.{field} must be in {low}..{high}")
        return profile


def synthesize_blip(frequency, sample_rate, channels=2):
    """40 ms voiced chirp with soft edges, a little pitch bend and harmonics."""
    frames = round(sample_rate * 0.04)
    pcm, phase = array("h"), 0.0
    for i in range(frames):
        t = i / sample_rate
        phase += math.tau * frequency * (1.035 - 0.07 * i / max(1, frames - 1)) / sample_rate
        envelope = min(1, t / 0.005, (frames - 1 - i) / (sample_rate * 0.012))
        voiced = math.sin(phase) * 0.73 + math.sin(phase * 2) * 0.18 + math.sin(phase * 3) * 0.09
        value = round(voiced * envelope * 0.28 * 32767)
        pcm.extend([value] * channels)
    return pcm.tobytes()


class DialogueVoice:
    def __init__(self):
        self._sounds = {}
        self._channel = None
        self._unavailable = False

    def play(self, profile, character, index):
        if (not settings.AUDIO_ENABLED or not settings.DIALOGUE_BEEPS_ENABLED
                or not profile.enabled or profile.volume <= 0):
            self.stop()
            return
        if self._unavailable or not pygame.get_init():
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            if pygame.mixer.get_num_channels() < MIXER_CHANNELS:
                pygame.mixer.set_num_channels(MIXER_CHANNELS)
            pygame.mixer.set_reserved(RESERVED_CHANNELS)
            rate, size, channels = pygame.mixer.get_init()
            if size != -16:
                return
            variant = (ord(character) + index * 3) % 7
            pitch = profile.pitch_hz * (1 + profile.pitch_variation * (variant - 3) / 3)
            key = (profile.pitch_hz, profile.pitch_variation, variant, rate, channels)
            if key not in self._sounds:
                self._sounds[key] = pygame.mixer.Sound(buffer=synthesize_blip(pitch, rate, channels))
            if self._channel is None:
                self._channel = pygame.mixer.Channel(DIALOGUE_CHANNEL)
            self._channel.play(self._sounds[key])
            self._channel.set_volume(settings.DIALOGUE_BEEP_VOLUME * profile.volume)
        except (pygame.error, OSError):
            self._unavailable = True

    def stop(self):
        if self._channel is not None and pygame.mixer.get_init():
            self._channel.stop()

    def release(self):
        self.stop()
        self._sounds.clear()


class DialogueTyper:
    def __init__(self, text, profile):
        self.text, self.profile = text, profile
        self.visible = 0
        self._wait = 0.0
        self._since_blip = 1.0
        self._letters = 0

    @property
    def finished(self):
        return self.visible >= len(self.text)

    def reveal(self):
        self.visible = len(self.text)

    def update(self, delta_time):
        """Return at most one sound cue per frame, with no backlog on slow frames."""
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Dialogue delta time must be finite and nonnegative")
        if self.finished or delta_time == 0:
            return None
        delta_time = min(delta_time, 0.25)
        self._since_blip += delta_time
        self._wait -= delta_time
        cue = None
        while self._wait <= 0 and not self.finished:
            character = self.text[self.visible]
            index = self.visible
            self.visible += 1
            self._wait += 1 / self.profile.chars_per_second
            if character in ",;:":
                self._wait += 0.12
            elif character in ".!?…":
                self._wait += 0.24
            if character.isalnum():
                self._letters += 1
                if self._letters >= 2 and self._since_blip >= 0.065:
                    cue = character, index
                    self._letters = 0
                    self._since_blip = 0.0
        return cue
