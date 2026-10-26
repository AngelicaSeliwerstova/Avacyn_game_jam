from dataclasses import dataclass
from typing import Callable

from engine.debug.profiler import FrameProfiler


@dataclass(frozen=True)
class DebugSettings:
    enabled: bool = False
    refresh_interval: float = 0.25
    font_size: int = 16
    margin: int = 8

    def __post_init__(self):
        if self.font_size <= 0 or self.margin < 0:
            raise ValueError("Debug font size must be positive and margin nonnegative")
        FrameProfiler(self.refresh_interval)


class DeveloperPanel:
    """Диагностика только читает сцену. Скрытая панель не собирает данные."""

    def __init__(self, settings: DebugSettings):
        self.enabled = settings.enabled
        self._profiler = FrameProfiler(settings.refresh_interval)
        self._text = ""

    @property
    def text(self) -> str:
        return self._text if self.enabled else ""

    def toggle(self):
        self.enabled = not self.enabled
        self._profiler.reset()
        self._text = ""

    def update(self, frame_seconds: float, update_seconds: float, render_seconds: float,
               details: Callable[[], tuple[str, ...]]):
        if not self.enabled:
            return
        refreshed = self._profiler.record(frame_seconds, update_seconds, render_seconds)
        if self._text and not refreshed:
            return
        metrics = self._profiler.metrics
        performance = ("FPS: ... | FRAME: ...", "CPU UPDATE: ... | DRAW: ...") if metrics is None else (
            f"FPS: {metrics.fps:.1f} | FRAME: {metrics.frame_ms:.2f} ms",
            f"CPU UPDATE: {metrics.update_ms:.2f} | DRAW: {metrics.render_ms:.2f} ms",
        )
        self._text = "\n".join(("DEVELOPER", *performance, *details()))
