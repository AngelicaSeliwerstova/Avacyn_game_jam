from dataclasses import dataclass
import math


@dataclass(frozen=True)
class FrameMetrics:
    fps: float
    frame_ms: float
    update_ms: float
    render_ms: float


class FrameProfiler:
    """Средние за интервал. Время кадра включает VSync и ограничитель FPS."""

    def __init__(self, interval: float):
        if not math.isfinite(interval) or interval <= 0:
            raise ValueError("Profiler interval must be finite and positive")
        self.interval = interval
        self.reset()

    def reset(self):
        self.metrics = None
        self._frames = 0
        self._elapsed = self._update = self._render = 0.0

    def record(self, frame_seconds: float, update_seconds: float, render_seconds: float) -> bool:
        if any(not math.isfinite(t) or t < 0 for t in (frame_seconds, update_seconds, render_seconds)):
            raise ValueError("Frame timings must be finite and nonnegative")
        if frame_seconds == 0:
            return False
        self._frames += 1
        self._elapsed += frame_seconds
        self._update += update_seconds
        self._render += render_seconds
        if self._elapsed + 1e-10 < self.interval:
            return False
        self.metrics = FrameMetrics(
            self._frames / self._elapsed, self._elapsed * 1000 / self._frames,
            self._update * 1000 / self._frames, self._render * 1000 / self._frames,
        )
        self._frames = 0
        self._elapsed = self._update = self._render = 0.0
        return True
