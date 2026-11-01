"""Editable CCTV chronology puzzle and optional durable progress store."""
from dataclasses import dataclass
import json
import math
from pathlib import Path

from engine.scene.archive import ArchiveFrame, ArchiveView
from game.dialogue_voice import DialogueTyper, DialogueVoice, DialogueVoiceProfile
from game.hospital_audio import HospitalSoundBank
from config import settings

PUZZLES_ROOT = Path(__file__).resolve().parents[2] / "resources/puzzles"
AUDIO_ROOT = PUZZLES_ROOT.parent / "audio"


def load_cctv_definition(filename, characters):
    path = (PUZZLES_ROOT / filename).resolve()

    def check(ok, message):
        if not ok:
            raise ValueError(f"{path}: {message}")

    check(path.is_relative_to(PUZZLES_ROOT.resolve()), "puzzle path must stay inside resources/puzzles")
    data = json.loads(path.read_text(encoding="utf-8"))
    check(isinstance(data, dict) and data.get("version") == 1, "unsupported CCTV format")
    check(type(data.get("speech_enabled", False)) is bool, "speech_enabled must be true or false")
    for key in ("title", "instruction", "incorrect", "correct", "hint", "solved_flag", "watched_flag", "report_flag"):
        check(isinstance(data.get(key), str) and bool(data[key].strip()), f"missing text {key}")
    frames = data.get("frames")
    check(isinstance(frames, list) and len(frames) == 4, "exactly four frames are required")
    ids = []
    for frame in frames:
        check(isinstance(frame, dict), "invalid frame")
        for key in ("id", "image", "time", "title", "description"):
            check(isinstance(frame.get(key), str) and bool(frame[key]), f"frame needs {key}")
        image = (path.parent / frame["image"]).resolve()
        check(image.is_relative_to(path.parent) and image.is_file(), "missing or unsafe frame image")
        frame["image"] = str(image)
        ids.append(frame["id"])
    check(len(set(ids)) == 4, "duplicate frame ID")
    for key in ("correct_order", "initial_order"):
        order = data.get(key)
        check(isinstance(order, list) and len(order) == 4 and set(order) == set(ids), f"invalid {key}")
    check(data["correct_order"] != data["initial_order"], "initial order is already solved")
    sounds = data.get("sounds")
    check(isinstance(sounds, dict) and all(name in sounds for name in ("click", "incorrect", "correct", "static", "impact", "footsteps")), "missing sound cues")
    for value in sounds.values():
        check(isinstance(value, str), "invalid sound filename")
        audio = (AUDIO_ROOT / value).resolve()
        check(audio.is_relative_to(AUDIO_ROOT.resolve()) and audio.is_file(), "missing or unsafe sound")
    timeline = data.get("recording")
    check(isinstance(timeline, list) and bool(timeline), "recording needs a timeline")
    for step in timeline:
        check(isinstance(step, dict) and step.get("frame") in ids, "unknown recording frame")
        seconds = step.get("seconds")
        check(type(seconds) in (int, float) and math.isfinite(seconds) and seconds > 0, "invalid recording duration")
        if "speaker" in step:
            check(step["speaker"] in characters and isinstance(step.get("text"), str), "invalid recording speaker/text")
        if "sound" in step:
            check(step["sound"] in sounds, "unknown recording sound")
        if "audio" in step:
            audio = (AUDIO_ROOT / step["audio"]).resolve()
            check(audio.is_relative_to(AUDIO_ROOT.resolve()) and audio.is_file(), "missing recorded voice")
    return data


@dataclass
class CCTVProgress:
    order: list[str]
    solved: bool = False
    watched: bool = False
    report_read: bool = False
    aftermath_done: bool = False
    attempts: int = 0


class CCTVProgressStore:
    """Campaign memory plus an optional atomic JSON checkpoint for the recorder."""
    def __init__(self, path=None, *, resume=True):
        self.path = Path(path) if path is not None else None
        self._data = {}
        self.warning = ""
        if resume and self.path is not None and self.path.exists():
            try:
                saved = json.loads(self.path.read_text(encoding="utf-8"))
                if saved.get("version") != 1 or not isinstance(saved.get("puzzles"), dict):
                    raise ValueError("unknown checkpoint format")
                self._data = saved["puzzles"]
            except (OSError, ValueError, AttributeError):
                self.warning = "Сохранение архива повреждено. Загружено начальное состояние."

    def get(self, puzzle_id, definition):
        raw = self._data.get(puzzle_id, {})
        initial = list(definition["initial_order"])
        if not isinstance(raw, dict):
            return CCTVProgress(initial)
        order = raw.get("order", initial)
        if (not isinstance(order, list) or len(order) != 4 or not all(isinstance(k, str) for k in order)
                or set(order) != set(initial)):
            order = initial
        solved = raw.get("solved") is True and order == definition["correct_order"]
        watched = solved and raw.get("watched") is True
        attempts = raw.get("attempts", 0)
        return CCTVProgress(list(order), solved, watched, watched and raw.get("report_read") is True,
                            watched and raw.get("aftermath_done") is True,
                            attempts if type(attempts) is int and attempts >= 0 else 0)

    def save(self, puzzle_id, progress):
        from dataclasses import asdict
        self._data[puzzle_id] = asdict(progress)
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps({"version": 1, "puzzles": self._data}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.path)
            self.warning = ""
        except OSError:
            self.warning = "Не удалось записать сохранение архива; прогресс сохранён в текущей игре."


class CCTVPuzzle:
    def __init__(self, puzzle_id, definition, store, characters):
        self.id, self.data, self.store, self.characters = puzzle_id, definition, store, characters
        self.progress = store.get(puzzle_id, definition)
        self.selected = None
        self.message = definition["correct"] if self.progress.solved else ""
        self.playing = False
        self._step = 0
        self._elapsed = 0.0
        self._typer = None
        self._voice = DialogueVoice()
        self._sounds = HospitalSoundBank(definition["sounds"])

    def save(self):
        self.store.save(self.id, self.progress)

    def _cue(self, name):
        if settings.AUDIO_ENABLED:
            self._sounds.play(name, 0.38, 0.38)

    def click(self, index):
        if self.progress.solved or self.playing or not 0 <= index < 4:
            return
        if self.selected is None:
            self.selected = index
        elif self.selected == index:
            self.selected = None
        else:
            a = self.selected
            self.progress.order[a], self.progress.order[index] = self.progress.order[index], self.progress.order[a]
            self.selected = None
            self.message = ""
            self.save()
        self._cue("click")

    def swap(self, first, second):
        if self.progress.solved or self.playing or not (0 <= first < 4 and 0 <= second < 4):
            return False
        self.progress.order[first], self.progress.order[second] = self.progress.order[second], self.progress.order[first]
        self.selected = None
        self.message = ""
        self.save()
        self._cue("click")
        return True

    def check(self):
        if self.progress.solved or self.playing:
            return self.progress.solved
        self.selected = None
        self.progress.attempts += 1
        self.progress.solved = self.progress.order == self.data["correct_order"]
        self.message = self.data["correct"] if self.progress.solved else self.data["incorrect"]
        self._cue("correct" if self.progress.solved else "incorrect")
        self.save()
        return self.progress.solved

    def reset(self):
        if not self.progress.solved and not self.playing:
            self.progress.order = list(self.data["initial_order"])
            self.selected = None
            self.message = ""
            self._cue("click")
            self.save()

    def hint(self):
        if self.progress.attempts >= 2 and not self.progress.solved and not self.playing:
            self.message = self.characters["doctor"]["name"] + ": " + self.data["hint"]
            self._voice.stop()
            self._typer = DialogueTyper(self.data["hint"], DialogueVoiceProfile.from_data(self.characters["doctor"].get("voice")))

    def play(self):
        if not self.progress.solved:
            return
        self.selected = None
        self.playing = True
        self._step, self._elapsed = 0, 0.0
        self._begin_step()

    def _begin_step(self):
        self._voice.stop()
        step = self.data["recording"][self._step]
        self._typer = None
        if "speaker" in step:
            profile = DialogueVoiceProfile.from_data(self.characters[step["speaker"]].get("voice"))
            self._typer = DialogueTyper(step["text"], profile)
        if "sound" in step:
            self._cue(step["sound"])

    def tick(self, delta_time):
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("CCTV delta time must be finite and nonnegative")
        if self._typer is not None:
            cue = self._typer.update(delta_time)
            if cue and settings.AUDIO_ENABLED and settings.DIALOGUE_BEEPS_ENABLED:
                self._voice.play(self._typer.profile, *cue)
        if not settings.AUDIO_ENABLED:
            self._sounds.stop()
        if not settings.AUDIO_ENABLED or not settings.DIALOGUE_BEEPS_ENABLED:
            self._voice.stop()
        if not self.playing:
            return False
        self._elapsed += min(delta_time, 0.25)
        if self._elapsed < self.data["recording"][self._step]["seconds"]:
            return False
        self._elapsed = 0.0
        self._step += 1
        if self._step < len(self.data["recording"]):
            self._begin_step()
            return False
        self.playing = False
        self.progress.watched = True
        self.save()
        self.stop()
        return True

    def view(self):
        frames = {f["id"]: ArchiveFrame(**f) for f in self.data["frames"]}
        step = self.data["recording"][min(self._step, len(self.data["recording"]) - 1)]
        order = self.data["correct_order"] if self.playing else self.progress.order
        return ArchiveView(self.data["title"], self.data["instruction"], tuple(frames[k] for k in order),
                           self.selected, self.progress.solved, self.progress.attempts >= 2,
                           self.message or self.store.warning, self.playing,
                           order.index(step["frame"]) if self.playing else 0,
                           self.characters.get(step.get("speaker"), {}).get("name", ""),
                           step.get("text", "") if self.playing else "", step.get("interference", False) if self.playing else False)

    def stop(self):
        self.playing = False
        self._voice.stop()
        self._typer = None
        self._sounds.stop()

    def release(self):
        self.stop()
        self._voice.release()
