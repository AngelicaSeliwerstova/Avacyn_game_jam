"""Validate all story files and their bindings to real game levels."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game.levels import create_level
from game.story_loader import STORY_ROOT, StoryFormatError, load_story


def check_bindings(book):
    names = set(book.data["entries"])
    for act in book.acts.values():
        if not book.enabled(act.id):
            continue
        for scene in act.data["scenes"]:
            names.update(scene.get("levels", []))
            names.update(step["level"] for step in scene["steps"] if step["type"] == "level")
        for doc in act.documents.values():
            names.update(step["level"] for step in doc.get("on_first_read", []) if step["type"] == "level")
    levels = {name: create_level(name) for name in sorted(names)}
    for name, level in levels.items():
        if level.story != book.id:
            raise StoryFormatError(f"{book.path}: level {name!r} must use story {book.id!r}")

    def triggers(trigger):
        if "any" in trigger:
            for child in trigger["any"]:
                yield from triggers(child)
        else:
            yield trigger

    for act in book.acts.values():
        if not book.enabled(act.id):
            continue
        for scene in act.data["scenes"]:
            candidates = [levels[name] for name in scene.get("levels", levels)]
            objects = {obj.name for level in candidates for obj in level.objects}
            for trigger in triggers(scene["trigger"]):
                entity_id = (trigger["object"] if trigger["type"] == "interact" else
                             book.data["characters"][trigger["actor"]].get("entity") if trigger["type"] == "talk" else None)
                if trigger["type"] in ("interact", "talk") and entity_id not in objects:
                    raise StoryFormatError(f"{act.path}: scene {scene['id']!r} refers to missing object {entity_id!r}")
            for step in scene["steps"]:
                if step["type"] in ("object_state", "wait_object"):
                    bound = [obj for level in candidates for obj in level.objects if obj.name == step["object"]]
                    if not bound or any(step["state"] not in obj.states for obj in bound):
                        raise StoryFormatError(f"{act.path}: scene {scene['id']!r}: missing object/state {step['object']}:{step['state']}")
    return len(levels)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--story", help="campaign folder name; default: check all campaigns")
    parser.add_argument("--root", type=Path, default=STORY_ROOT)
    parser.add_argument("--data-only", action="store_true", help="skip geometry and object binding checks")
    args = parser.parse_args()
    names = [args.story] if args.story else sorted(path.name for path in args.root.iterdir() if path.is_dir())
    try:
        if not names:
            raise StoryFormatError(f"{args.root}: no stories found")
        for name in names:
            book = load_story(name, args.root)
            count = check_bindings(book) if not args.data_only else 0
            enabled = sum(book.enabled(act_id) for act_id in book.acts)
            print(f"OK {book.id}: {enabled} enabled acts, {len(book.acts) - enabled} drafts, {count} checked levels")
    except (StoryFormatError, ValueError, OSError) as error:
        print(f"Story error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
