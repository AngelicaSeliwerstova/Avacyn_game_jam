"""Silent typewriter text and backwards-compatible dialogue timing profiles."""

from dataclasses import dataclass
import math




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


class DialogueTyper:
    def __init__(self, text, profile):
        self.text, self.profile = text, profile
        self.visible = 0
        self._wait = 0.0

    @property
    def finished(self):
        return self.visible >= len(self.text)

    def reveal(self):
        self.visible = len(self.text)

    def update(self, delta_time):
        """Reveal text with punctuation pauses and no sound generation."""
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Dialogue delta time must be finite and nonnegative")
        if self.finished or delta_time == 0:
            return None
        delta_time = min(delta_time, 0.25)
        self._wait -= delta_time
        while self._wait <= 0 and not self.finished:
            character = self.text[self.visible]
            self.visible += 1
            self._wait += 1 / self.profile.chars_per_second
            if character in ",;:":
                self._wait += 0.12
            elif character in ".!?…":
                self._wait += 0.24
