"""Buffered diagnostics for slow frames. Created only in explicit debug mode."""

from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter


class SlowFrameLog:
    def __init__(self, directory: Path, threshold_fps: float = 45):
        self.threshold_fps = threshold_fps
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        self.path = directory / f"performance-{stamp}.jsonl"
        self._file = self.path.open("x", encoding="utf-8", buffering=65536)
        self._started = self._last_flush = perf_counter()
        self._frame = 0
        self._pending = False
        self._write({"event": "session_start", "threshold_fps": threshold_fps,
                     "timings": "CPU wall time; GPU waits may appear in draw/present"})
        self._file.flush()
        self._pending = False

    def _write(self, record):
        record["time"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._pending = True

    def record(self, frame_seconds: float, timings: dict[str, float], details):
        self._frame += 1
        if self._pending and perf_counter() - self._last_flush >= 1:
            self._file.flush()
            self._last_flush = perf_counter()
            self._pending = False
        if frame_seconds <= 0 or frame_seconds <= 1 / self.threshold_fps:
            return
        now = perf_counter()
        # Details are gathered only for slow frames, never every normal frame.
        self._write({"event": "slow_frame", "frame": self._frame,
                     "elapsed_s": round(now - self._started, 3),
                     "fps": round(1 / frame_seconds, 2),
                     "frame_ms": round(frame_seconds * 1000, 3),
                     "timings_ms": {key: round(value * 1000, 3) for key, value in timings.items()},
                     "largest_stage": max(timings, key=timings.get) if timings else None,
                     **details()})

    def close(self):
        if not self._file.closed:
            self._write({"event": "session_end", "frames": self._frame})
            self._file.close()
