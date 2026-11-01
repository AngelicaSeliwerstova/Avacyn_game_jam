"""Load and validate editable story resources. No Python is executed from them."""

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re


STORY_ROOT = Path(__file__).resolve().parents[1] / "resources/story"
AUDIO_ROOT = STORY_ROOT.parent / "audio"
_ID = re.compile(r"[a-zA-Z0-9_-]+\Z")


class StoryFormatError(ValueError):
    pass


def _check(ok, where, message):
    if not ok:
        raise StoryFormatError(f"{where}: {message}")


def _text(value, where):
    _check(isinstance(value, str) and bool(value.strip()), where, "expected nonempty text")


def _strings(value, where):
    _check(isinstance(value, list), where, "expected a list of strings")
    for i, item in enumerate(value):
        _text(item, f"{where}[{i}]")


def _number(value, where, minimum=0):
    _check(type(value) in (int, float) and math.isfinite(value) and value >= minimum,
           where, f"expected a finite number >= {minimum}")


def _fields(value, where, required=(), optional=()):
    _check(isinstance(value, dict), where, "expected an object")
    _check(not (set(required) - value.keys()), where, f"required fields: {', '.join(required)}")
    extra = value.keys() - set(required) - set(optional)
    _check(not extra, where, f"unknown fields: {', '.join(sorted(extra))}")


def _boolean(value, where):
    _check(type(value) is bool, where, "expected true or false")


def _read(path):
    def pairs(items):
        result = {}
        for key, value in items:
            _check(key not in result, path, f"duplicate key: {key}")
            result[key] = value
        return result

    try:
        result = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StoryFormatError(f"{path}: {error}") from error
    _check(isinstance(result, dict), path, "expected a JSON object")
    return result


def _file(directory, name):
    _text(name, directory)
    path = (directory / name).resolve()
    _check(path.is_relative_to(directory.resolve()), directory, "resource path must stay inside its folder")
    return path


@dataclass(frozen=True)
class StoryAct:
    data: dict
    dialogues: dict
    documents: dict
    path: Path

    @property
    def id(self):
        return self.data["id"]


@dataclass(frozen=True)
class StoryBook:
    data: dict
    acts: dict[str, StoryAct]
    path: Path

    @property
    def id(self):
        return self.data["id"]

    def enabled(self, act_id):
        return next(item.get("enabled", True) for item in self.data["acts"] if item["id"] == act_id)

    def document(self, document_id):
        _check(isinstance(document_id, str), self.path, "document ID must be text")
        for act in self.acts.values():
            if document_id in act.documents:
                return act, act.documents[document_id]
        raise StoryFormatError(f"{self.path}: unknown document {document_id!r}")


class _ActValidator:
    def __init__(self, book, act):
        self.book, self.act = book, act
        self.actors = book.data["characters"]

    def ref(self, value, entries, where):
        _check(isinstance(value, str) and value in entries, where, f"unknown reference: {value!r}")

    def document(self, document_id, where):
        ids = {name for act in self.book.acts.values() for name in act.documents}
        self.ref(document_id, ids, where)
        return self.book.document(document_id)

    def conditions(self, value, where):
        for field in ("requires", "unless", "levels"):
            if field in value:
                _strings(value[field], f"{where}.{field}")

    def lines(self, nodes, where, depth=0):
        _check(isinstance(nodes, list) and bool(nodes), where, "dialogue needs at least one line")
        _check(depth < 24, where, "dialogue branches are nested too deeply")
        for i, node in enumerate(nodes):
            loc = f"{where}[{i}]"
            _check(isinstance(node, dict), loc, "expected a dialogue line or choice")
            if "choice" in node:
                _fields(node, loc, ("choice", "speaker", "prompt", "options"))
                _text(node["choice"], loc + ".choice")
                _text(node["prompt"], loc + ".prompt")
                options = node["options"]
                _check(isinstance(options, list) and 1 <= len(options) <= 4, loc + ".options", "choice needs 1–4 options")
                for j, option in enumerate(options):
                    opt = f"{loc}.options[{j}]"
                    _fields(option, opt, ("label", "lines"), ("set_flags",))
                    _text(option["label"], opt + ".label")
                    if "set_flags" in option:
                        _strings(option["set_flags"], opt + ".set_flags")
                    self.lines(option["lines"], opt + ".lines", depth + 1)
            else:
                _fields(node, loc, ("speaker", "text"))
                _text(node["text"], loc + ".text")
            self.ref(node["speaker"], self.actors, loc + ".speaker")

    def steps(self, steps, where):
        _check(isinstance(steps, list), where, "expected a list of steps")
        specs = {
            "dialogue": (("id",), ("presentation",)), "flags": ((), ("add", "remove")),
            "title": (("title", "text", "seconds"), ("fade_seconds",)),
            "effect": (("effect", "seconds"), ()), "level": (("level",), ("preserve_scene",)),
            "follow": (("actor", "enabled"), ()), "say": (("speaker", "text"), ("seconds",)),
            "map": (("id",), ()), "document": (("id",), ()),
            "sound": (("profile", "volume"), ()), "complete_act": ((), ()), "next_act": ((), ()),
            "object_state": (("object", "state"), ()), "wait_object": (("object", "state"), ()),
            "wait": (("seconds",), ()), "end": (("title", "text"), ()),
        }
        for i, step in enumerate(steps):
            loc = f"{where}[{i}]"
            _check(isinstance(step, dict), loc, "expected a step object")
            kind = step.get("type")
            _check(isinstance(kind, str) and kind in specs, loc + ".type", f"unknown step {kind!r}")
            required, optional = specs[kind]
            _fields(step, loc, ("type", *required), optional)
            if kind == "dialogue":
                self.ref(step["id"], self.act.dialogues, loc + ".id")
                _check(step.get("presentation", "conversation") in ("conversation", "memory"), loc, "invalid dialogue presentation")
            elif kind in ("object_state", "wait_object"):
                _text(step["object"], loc + ".object")
                _text(step["state"], loc + ".state")
            elif kind == "wait":
                _number(step["seconds"], loc + ".seconds", 0.001)
            elif kind == "end":
                _text(step["title"], loc + ".title")
                _text(step["text"], loc + ".text")
            elif kind in ("map", "document"):
                _, doc = self.document(step["id"], loc + ".id")
                _check(doc.get("type") == kind, loc, f"expected a {kind} resource")
            elif kind == "flags":
                for key in ("add", "remove"):
                    if key in step:
                        _strings(step[key], loc + "." + key)
            elif kind in ("title", "effect"):
                _number(step["seconds"], loc + ".seconds", 0.001)
                if kind == "title":
                    _text(step["title"], loc + ".title")
                    _text(step["text"], loc + ".text")
                    _number(step.get("fade_seconds", 1), loc + ".fade_seconds", 0.001)
                else:
                    _check(step["effect"] in ("interference", "blackout", "fade_to_black"), loc, "unsupported visual effect")
            elif kind == "level":
                _check(isinstance(step["level"], str) and bool(_ID.fullmatch(step["level"])), loc, "invalid level ID")
                _boolean(step.get("preserve_scene", False), loc + ".preserve_scene")
                _check(i == len(steps) - 1, loc, "level transition must be the last step of the scene")
            elif kind in ("follow", "say"):
                self.ref(step["actor"] if kind == "follow" else step["speaker"], self.actors, loc)
                if kind == "follow":
                    _boolean(step["enabled"], loc + ".enabled")
                    _check("entity" in self.actors[step["actor"]], loc, "following actor needs an entity binding")
                else:
                    _text(step["text"], loc + ".text")
                    _number(step.get("seconds", 5.5), loc + ".seconds", 0.001)
            elif kind == "sound":
                _check(step["profile"] in ("doctor", "player"), loc, "unknown footstep sound profile")
                _check(isinstance(step["volume"], list) and len(step["volume"]) == 2, loc, "volume needs left and right values")
                for volume in step["volume"]:
                    _number(volume, loc + ".volume")
                    _check(volume <= 1, loc, "volume must be <= 1")

    def trigger(self, trigger, where, depth=0):
        _check(depth < 12, where, "triggers are nested too deeply")
        _check(isinstance(trigger, dict), where, "expected a trigger object")
        if "any" in trigger:
            _fields(trigger, where, ("any",))
            _check(isinstance(trigger["any"], list) and bool(trigger["any"]), where, "any needs triggers")
            for i, child in enumerate(trigger["any"]):
                self.trigger(child, f"{where}.any[{i}]", depth + 1)
            return
        kind = trigger.get("type")
        fields = {"load": (), "talk": ("actor",), "interact": ("object",),
                  "zone": ("zone",), "zone_enter": ("zone",), "outside_zone": ("zone",),
                  "idle": ("seconds",), "revisit": ("zones",), "event": ("name",)}
        _check(isinstance(kind, str) and kind in fields, where, f"unknown trigger {kind!r}")
        _fields(trigger, where, ("type", *fields[kind]))
        if "zone" in trigger:
            self.ref(trigger["zone"], self.act.data["zones"], where + ".zone")
        if kind == "revisit":
            _strings(trigger["zones"], where + ".zones")
            for zone in trigger["zones"]:
                self.ref(zone, self.act.data["zones"], where)
        elif kind == "talk":
            self.ref(trigger["actor"], self.actors, where + ".actor")
        elif kind == "interact":
            _text(trigger["object"], where + ".object")
        elif kind == "idle":
            _number(trigger["seconds"], where + ".seconds", 0.001)
        elif kind == "event":
            _text(trigger["name"], where + ".name")

    def validate(self):
        data, path = self.act.data, str(self.act.path)
        _fields(data, path, ("id", "title", "complete_flag", "dialogues_file", "documents_file", "zones", "objectives", "scenes"), ("next_act", "notes", "audio_sources"))
        _text(data["title"], path + ".title")
        _text(data["complete_flag"], path + ".complete_flag")
        if "next_act" in data:
            self.ref(data["next_act"], self.book.acts, path + ".next_act")
        sources = data.get("audio_sources", [])
        _check(isinstance(sources, list), path + ".audio_sources", "expected a list")
        _check(sum(bool(s.get("loop")) for s in sources if isinstance(s, dict)) <= 3,
               path + ".audio_sources", "at most three story loops per act")
        names = set()
        for i, source in enumerate(sources):
            loc = f"{path}.audio_sources[{i}]"
            _fields(source, loc, ("id", "file", "position", "radius", "volume", "loop"),
                    ("requires", "unless", "levels", "interval", "event"))
            _text(source["id"], loc + ".id")
            _check(source["id"] not in names, loc, "duplicate audio source ID")
            names.add(source["id"])
            audio_path = _file(AUDIO_ROOT, source["file"])
            _check(audio_path.is_file(), loc + ".file", "missing audio file")
            point = source["position"]
            _check(isinstance(point, list) and len(point) == 3
                   and all(type(v) in (int, float) and math.isfinite(v) for v in point), loc, "position needs three finite coordinates")
            _number(source["radius"], loc + ".radius", 0.001)
            _number(source["volume"], loc + ".volume")
            _check(source["volume"] <= 1, loc, "volume must be <= 1")
            _boolean(source["loop"], loc + ".loop")
            self.conditions(source, loc)
            if "event" in source:
                _text(source["event"], loc + ".event")
                _check(not source["loop"] and "interval" not in source, loc, "event sounds must be one-shot")
            elif not source["loop"]:
                interval = source.get("interval")
                _check(isinstance(interval, list) and len(interval) == 2, loc, "one-shot sound needs an interval")
                for value in interval:
                    _number(value, loc + ".interval", 0.001)
                _check(interval[0] <= interval[1], loc, "invalid interval order")
        _check(isinstance(data["zones"], dict), path + ".zones", "expected named zones")
        for name, zone in data["zones"].items():
            loc = path + ".zones." + name
            _fields(zone, loc, ("min", "max"))
            for field in ("min", "max"):
                _check(isinstance(zone[field], list) and len(zone[field]) == 3, loc, "zone needs 3D coordinates")
                for number in zone[field]:
                    _check(type(number) in (int, float) and math.isfinite(number), loc, "coordinates must be finite numbers")
            _check(all(a < b for a, b in zip(zone["min"], zone["max"])), loc, "zone min must be below max")
        for name, nodes in self.act.dialogues.items():
            self.lines(nodes, f"{self.act.path.parent / data['dialogues_file']}:{name}")
        for name, doc in self.act.documents.items():
            loc = f"{self.act.path.parent / data['documents_file']}:{name}"
            _fields(doc, loc, ("type", "title", "read_flag"), ("pages", "last_page_flag", "require_last_page", "shortcut", "shortcut_label", "require_all_floors", "first_hint", "hint", "stair", "floors", "highlights", "on_first_read"))
            _text(doc["title"], loc + ".title")
            _text(doc["read_flag"], loc + ".read_flag")
            _check(doc["type"] in ("map", "document"), loc, "unknown document type")
            if doc["type"] == "document":
                _strings(doc.get("pages"), loc + ".pages")
                _check(bool(doc["pages"]), loc, "document needs pages")
            else:
                floors = doc.get("floors")
                _check(isinstance(floors, list) and bool(floors), loc, "map needs floors")
                for labels in floors:
                    _check(isinstance(labels, list), loc, "floor needs a list of labels")
                    for label in labels:
                        _check(isinstance(label, list) and len(label) == 3, loc, "label needs x, z, text")
                        for number in label[:2]:
                            _check(type(number) in (int, float) and math.isfinite(number), loc, "label coordinates must be finite")
                        _text(label[2], loc + ".floors.label")
                for key in ("hint", "first_hint"):
                    _text(doc.get(key), loc + "." + key)
            for key in ("require_last_page", "require_all_floors"):
                if key in doc:
                    _boolean(doc[key], loc + "." + key)
            for key in ("shortcut", "shortcut_label", "last_page_flag"):
                if key in doc:
                    _text(doc[key], loc + "." + key)
            if "highlights" in doc:
                _strings(doc["highlights"], loc + ".highlights")
            if "stair" in doc:
                _check(isinstance(doc["stair"], list) and len(doc["stair"]) == 3, loc, "stair needs x, z, radius")
                for number in doc["stair"]:
                    _check(type(number) in (int, float) and math.isfinite(number), loc, "invalid stair coordinate")
                _number(doc["stair"][2], loc + ".stair.radius", 0.001)
            self.steps(doc.get("on_first_read", []), loc + ".on_first_read")
        _check(isinstance(data["objectives"], list), path, "objectives must be a list")
        for i, objective in enumerate(data["objectives"]):
            loc = f"{path}.objectives[{i}]"
            _fields(objective, loc, ("title", "description"), ("requires", "unless", "levels"))
            _text(objective["title"], loc + ".title")
            _text(objective["description"], loc + ".description")
            self.conditions(objective, loc)
        _check(isinstance(data["scenes"], list), path, "scenes must be a list")
        names = set()
        for i, scene in enumerate(data["scenes"]):
            loc = f"{path}.scenes[{i}]"
            _fields(scene, loc, ("id", "trigger", "steps"), ("requires", "unless", "levels", "once", "cooldown"))
            _text(scene["id"], loc + ".id")
            _check(scene["id"] not in names, loc, "duplicate scene ID")
            names.add(scene["id"])
            self.conditions(scene, loc)
            _boolean(scene.get("once", True), loc + ".once")
            _number(scene.get("cooldown", 0), loc + ".cooldown")
            self.trigger(scene["trigger"], loc + ".trigger")
            self.steps(scene["steps"], loc + ".steps")


def load_story(story_id, root=None):
    root = (STORY_ROOT if root is None else Path(root)).resolve()
    _check(isinstance(story_id, str) and bool(_ID.fullmatch(story_id)), root, "invalid story ID")
    path = root / story_id / "campaign.json"
    data = _read(path)
    _fields(data, str(path), ("version", "id", "start_act", "characters", "entries", "acts"))
    _check(type(data["version"]) is int and data["version"] == 1, path, "unsupported story format version")
    _check(data["id"] == story_id, path, "campaign ID does not match its folder")
    _check(isinstance(data["characters"], dict), path, "characters must be named objects")
    for name, character in data["characters"].items():
        _fields(character, str(path) + ".characters." + name, ("name",), ("entity", "voice"))
        _text(character["name"], path)
        if "entity" in character:
            _text(character["entity"], path)
        if "voice" in character:
            from game.dialogue_voice import DialogueVoiceProfile
            try:
                DialogueVoiceProfile.from_data(character["voice"])
            except ValueError as error:
                raise StoryFormatError(f"{path}:characters.{name}.voice: {error}") from error
    _check(isinstance(data["acts"], list) and bool(data["acts"]), path, "campaign needs acts")
    acts = {}
    for item in data["acts"]:
        _fields(item, str(path) + ".acts", ("id", "file"), ("enabled",))
        _text(item["id"], path)
        _check(item["id"] not in acts, path, "duplicate act ID")
        _boolean(item.get("enabled", True), path)
        act_path = _file(path.parent, item["file"])
        act = _read(act_path)
        _check(act.get("id") == item["id"], act_path, "act ID does not match campaign entry")
        dialogues = _read(_file(act_path.parent, act.get("dialogues_file")))
        documents = _read(_file(act_path.parent, act.get("documents_file")))
        acts[item["id"]] = StoryAct(act, dialogues, documents, act_path)
    book = StoryBook(data, acts, path)
    _check(isinstance(data["start_act"], str) and data["start_act"] in acts, path, "unknown start act")
    _check(book.enabled(data["start_act"]), path, "start act must be enabled")
    _check(isinstance(data["entries"], dict), path, "entries must be named levels")
    for name, entry in data["entries"].items():
        _fields(entry, str(path) + ".entries." + name, ("act",), ("set_flags",))
        _check(isinstance(entry["act"], str) and entry["act"] in acts and book.enabled(entry["act"]), path, "entry points to an unknown or disabled act")
        _strings(entry.get("set_flags", []), path)
    seen = set()
    for act in acts.values():
        for name in act.documents:
            _check(name not in seen, act.path, f"duplicate document ID across acts: {name}")
            seen.add(name)
        _ActValidator(book, act).validate()
    return book
