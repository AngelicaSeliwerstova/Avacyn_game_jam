"""Scenario interpreter: scene triggers and reusable actions, independent of acts."""

from collections import deque
from dataclasses import replace
import math

from engine.scene.session import Dialog, DialogButton
from game.session import GameSession
from game.levels.story_props import StoryDocument, StoryProp
from game.story_loader import StoryFormatError
from game.story_map import floor_plan
from game.story_text import text_pages
from game.dialogue_voice import DialogueVoiceProfile


class StorySession(GameSession):
    def __init__(self, level, player, flags, book, level_name, *, puzzle_store=None):
        self.level, self.book, self.level_name = level, book, level_name
        self._active_prefix = f"story:{book.id}:active:"
        active = next((name for name in book.acts if self._active_prefix + name in flags), None)
        if active is None:
            entry = book.data["entries"].get(level_name, {"act": book.data["start_act"]})
            active = entry["act"]
            flags.update(entry.get("set_flags", []))
            flags.add(self._active_prefix + active)
        self.act = book.acts[active]
        super().__init__(level, player, flags)
        from game.puzzles.cctv_puzzle import CCTVPuzzle, CCTVProgressStore, load_cctv_definition
        store = CCTVProgressStore() if puzzle_store is None else puzzle_store
        self._puzzles = {name: CCTVPuzzle(name, load_cctv_definition(filename, book.data["characters"]), store,
                                         book.data["characters"])
                         for name, filename in book.data.get("puzzles", {}).items()}
        self._puzzle = None
        self._sync_puzzle_flags()
        for act in book.acts.values():
            for document_id, document in act.documents.items():
                if document["read_flag"] in flags and not player.inventory.has_item(document_id):
                    player.inventory.add_item(document_id, document["title"])
        self.actors = {name: next((ally for ally in self.companions if ally.name == item.get("entity")), None)
                       for name, item in book.data["characters"].items()}
        for name, actor in self.actors.items():
            if actor:
                actor.display_name = book.data["characters"][name]["name"]
                if actor.scene_object.interaction is not None:
                    actor.scene_object.set_interaction(replace(actor.scene_object.interaction, name=actor.display_name))
        for obj in level.objects:
            if isinstance(obj.entity, StoryDocument) and obj.interaction is not None:
                _, document = book.document(obj.name)
                obj.set_interaction(replace(obj.interaction, name=document["title"], message=document["title"]))
        self._queue = deque()
        self._node = self._node_act = None
        self._timed = None
        self._elapsed = self._idle = self._subtitle_time = self._clock = 0.0
        self._last_position = tuple(player.body.position)
        self._previous_zones, self._visited_zones = set(), set()
        self._cooldowns = {}
        self._document_id = None
        self._document_page = self._map_floor = 0
        self._map_visits = set()
        self._wait_seconds = 0.0
        self._wait_object = None
        self._voice_remaining = None
        self._voiceover_elapsed = 0.0
        self._ambience_tween = None
        if "act0:key_taken" in flags and not player.inventory.has_key("second_floor_key"):
            player.inventory.add_key("second_floor_key", "Ключ от второго этажа — номер стёрт")
        from game.puzzles.patient_files import PatientFiles
        self._files = PatientFiles(self)
        self.preserve_scene_on_transition = False
        self._dispatch({"load": True, "talk": set(), "interact": set(), "zones": set(), "entered": set(), "revisited": set()})
        self._update_hint()

    def _conditions(self, data):
        return (set(data.get("requires", ())) <= self._flags
                and not set(data.get("unless", ())) & self._flags
                and ("levels" not in data or self.level_name in data["levels"]))

    def _update_hint(self):
        self.player.act_title = self.act.data["title"]
        self.player.objective_status = ""
        for objective in self.act.data["objectives"]:
            if self._conditions(objective):
                self.player.objective_status = objective["title"] + "\n" + objective["description"]
                break
        self.player.story_controls = "\n".join(
            doc["shortcut_label"] for act in self.book.acts.values() for doc in act.documents.values()
            if doc["read_flag"] in self._flags and "shortcut_label" in doc)

    def _prepend(self, act, steps):
        self._queue.extendleft((act, step) for step in reversed(steps))

    def _dialogue_nodes(self, act, nodes, presentation="conversation"):
        steps = []
        for node in nodes:
            is_choice = "choice" in node
            pages = text_pages(node["prompt"] if is_choice else node["text"], "conversation")
            if presentation == "voiceover":
                total = max(1, sum(len(page) for page in pages))
                for index, page in enumerate(pages):
                    steps.append({"type": "_voice_line", "node": {
                        "speaker": node["speaker"], "text": page,
                        "audio": node["audio"] if index == 0 else None,
                        "seconds": node["seconds"] * len(page) / total}})
                continue
            for page in pages[:-1]:
                steps.append({"type": "_line", "node": {"speaker": node["speaker"], "text": page}, "presentation": presentation})
            steps.append({"type": "_choice" if is_choice else "_line",
                          "node": {**node, "prompt" if is_choice else "text": pages[-1]}, "presentation": presentation})
        self._prepend(act, steps)

    def _advance(self):
        self.stop_dialogue_voice()
        self.dialog = None
        self._node = None
        while self._queue and self.next_level is None:
            act, step = self._queue.popleft()
            kind = step["type"]
            if kind == "dialogue":
                self._dialogue_nodes(act, act.dialogues[step["id"]], step.get("presentation", "conversation"))
            elif kind == "voiceover":
                self._voiceover_elapsed = 0.0
                self._dialogue_nodes(act, act.dialogues[step["id"]], "voiceover")
            elif kind == "_voice_line":
                node = step["node"]
                self._voice_remaining = node["seconds"]
                self.dialog = Dialog(self.book.data["characters"][node["speaker"]]["name"], node["text"], (),
                                     presentation="voiceover", effect_time=self._voiceover_elapsed)
                if node["audio"]:
                    self._play_audio(node["audio"], 0.78, voice=True)
                break
            elif kind == "focus_camera":
                self.player.story_camera = (tuple(step["position"]), tuple(step["target"]))
                self.player.story_distortion = 0.12
                self.player._sync_fixed_camera()
            elif kind == "ambience":
                self._ambience_tween = (self.player.story_audio_gain, step["gain"], step["seconds"], 0.0)
            elif kind == "grant_key":
                self.player.inventory.add_key(step["id"], step["name"])
            elif kind in ("_line", "_choice"):
                node = step["node"]
                self._node, self._node_act = node, act
                speaker = self.book.data["characters"][node["speaker"]]["name"]
                if kind == "_choice":
                    buttons = tuple(DialogButton(f"{i + 1}. {option['label']}", f"story_choice:{i}", (str(i + 1),))
                                    for i, option in enumerate(node["options"]))
                    self.dialog = Dialog(speaker, node["prompt"], buttons, presentation="conversation")
                else:
                    voice = DialogueVoiceProfile.from_data(self.book.data["characters"][node["speaker"]].get("voice"))
                    self.show_spoken_line(speaker, node["text"], (DialogButton("Далее   E / Enter", "story_next",
                                          ("e", "return", "keypad enter")),), voice, step.get("presentation", "conversation"))
                break
            elif kind == "flags":
                self._flags.difference_update(step.get("remove", []))
                self._flags.update(step.get("add", []))
            elif kind == "follow":
                actor = self.actors[step["actor"]]
                if actor is None:
                    raise StoryFormatError(f"{act.path}: actor {step['actor']!r} has no entity on {self.level_name}")
                actor.following = step["enabled"]
            elif kind in ("title", "effect"):
                self._timed, self._elapsed = step, 0.0
                presentation = "title" if kind == "title" else step["effect"]
                self.dialog = Dialog(step.get("title", ""), step.get("text", ""), (),
                                     presentation="blackout" if presentation == "fade_to_black" else presentation,
                                     opacity=0 if presentation == "fade_to_black" else 1)
                break
            elif kind == "object_state":
                obj = self._object(step["object"])
                obj.set_state(step["state"])
                if isinstance(obj.entity, StoryDocument) and obj.interaction is not None:
                    _, document = self.book.document(obj.name)
                    obj.set_interaction(replace(obj.interaction, name=document["title"], message=document["title"]))
            elif kind == "puzzle":
                self.stop_dialogue_voice()
                self._puzzle = self._puzzles[step["id"]]
                if self._puzzle.progress.solved:
                    self._puzzle.play()
                self.puzzle_view = self._puzzle.view()
                break
            elif kind == "puzzle_checkpoint":
                puzzle = self._puzzles[step["id"]]
                puzzle.progress.aftermath_done = True
                puzzle.save()
                self._sync_puzzle_flags()
            elif kind == "archive":
                self._files.show(case=step.get("case", False))
                break
            elif kind == "wait":
                self._wait_seconds = step["seconds"]
                self.controls_locked = True
                break
            elif kind == "wait_object":
                self._wait_object = self._object(step["object"]), step["state"]
                self.controls_locked = True
                break
            elif kind == "end":
                buttons = self._buttons()
                target = act.data.get("next_act")
                if target and self.book.enabled(target):
                    buttons = (DialogButton("Продолжить   E / Enter", "story_continue", ("e", "return")),
                               DialogButton("Выйти   Esc", "quit", ("escape",)))
                self.dialog = Dialog(step["title"], step["text"], buttons, presentation="ending")
                break
            elif kind == "level":
                self.preserve_scene_on_transition = step.get("preserve_scene", False)
                self.next_level = step["level"]
                self.dialog = Dialog("", "", (), presentation="blackout")
                break
            elif kind in ("document", "map"):
                self.open_document(step["id"])
                break
            elif kind == "say":
                speaker = self.book.data["characters"][step["speaker"]]["name"]
                self.player.story_status = f"{speaker}: {step['text']}"
                self._subtitle_time = step.get("seconds", 5.5)
            elif kind == "sound":
                from config import settings
                if settings.AUDIO_ENABLED:
                    from game.footsteps import FootstepSounds
                    if not hasattr(self, "_sounds"):
                        self._sounds = FootstepSounds()
                    self._sounds.play(step["profile"], *step["volume"], voice="story")
            elif kind == "audio":
                self._play_audio(step["file"], step.get("volume", 1))
            elif kind == "complete_act":
                self._flags.add(act.data["complete_flag"])
                self.player.story_events.add(f"act_complete:{act.id}")
            elif kind == "next_act":
                target = act.data.get("next_act")
                if target and self.book.enabled(target):
                    if act.data["complete_flag"] not in self._flags:
                        raise StoryFormatError(f"{act.path}: complete the act before advancing to {target}")
                    self._flags.difference_update(flag for flag in tuple(self._flags) if flag.startswith(self._active_prefix))
                    self._flags.add(self._active_prefix + target)
                    self.act = self.book.acts[target]
                    self._sync_puzzle_flags()
                    self._previous_zones.clear()
                    self._visited_zones.clear()
                    self._dispatch({"load": True, "talk": set(), "interact": set(), "zones": set(), "entered": set(), "revisited": set()}, advance=False)
            else:
                raise StoryFormatError(f"{act.path}: unsupported action {kind!r}")
        self._update_hint()

    def _object(self, name):
        obj = next((obj for obj in self.level.objects if obj.name == name), None)
        if obj is None:
            raise StoryFormatError(f"{self.act.path}: object {name!r} not found on {self.level_name}")
        return obj

    def _play_audio(self, filename, volume, *, voice=False):
        from config import settings
        if not settings.AUDIO_ENABLED:
            return
        from game.hospital_audio import HospitalSoundBank
        if not hasattr(self, "_cue_sounds"):
            self._cue_sounds = HospitalSoundBank({})
        self._cue_sounds._paths[filename] = filename
        if voice:
            self._cue_sounds.play_voice(filename, volume)
        else:
            self._cue_sounds.play_discovery(filename, volume)

    def tick_presentation(self, delta_time):
        if not math.isfinite(delta_time) or delta_time < 0:
            raise ValueError("Story delta time must be finite and nonnegative")
        super().tick_presentation(delta_time)
        from config import settings
        if hasattr(self, "_cue_sounds") and not settings.AUDIO_ENABLED:
            self._cue_sounds.stop_effects()
        if self._ambience_tween is not None:
            start, target, seconds, elapsed = self._ambience_tween
            elapsed = min(seconds, elapsed + delta_time)
            self.player.story_audio_gain = start + (target - start) * elapsed / seconds
            self._ambience_tween = None if elapsed >= seconds else (start, target, seconds, elapsed)
        if self._voice_remaining is not None:
            self._voiceover_elapsed += delta_time
            self._voice_remaining -= delta_time
            if self._voice_remaining <= 0:
                self._voice_remaining = None
                self._advance()
            else:
                self.dialog = replace(self.dialog, effect_time=self._voiceover_elapsed)
            return
        if self._puzzle is not None:
            if self._puzzle.tick(delta_time):
                puzzle = self._puzzle
                self._sync_puzzle_flags()
                if not puzzle.progress.aftermath_done:
                    self.player.story_events.add(f"watched:{puzzle.id}")
                self._close_puzzle()
            else:
                self.puzzle_view = self._puzzle.view()
            return
        if self._timed is None:
            return
        self._elapsed += delta_time
        step = self._timed
        opacity = min(1, max(0, (step["seconds"] - self._elapsed) / step.get("fade_seconds", 1))) if step["type"] == "title" else 1
        if step.get("effect") == "fade_to_black":
            opacity = min(1, self._elapsed / step["seconds"])
        if step.get("effect") == "distortion":
            self.player.story_distortion = 0.12 + 0.45 * max(0, 1 - self._elapsed / step["seconds"])
        self.dialog = replace(self.dialog, opacity=opacity, effect_time=self._elapsed)
        if self._elapsed >= step["seconds"]:
            self._timed = None
            self._advance()

    def _triggered(self, trigger, events):
        if "any" in trigger:
            return any(self._triggered(child, events) for child in trigger["any"])
        kind = trigger["type"]
        if kind == "load":
            return events["load"]
        if events["load"]:
            return False
        if kind == "talk":
            return trigger["actor"] in events["talk"]
        if kind == "interact":
            return trigger["object"] in events["interact"]
        if kind == "event":
            return trigger["name"] in self.player.story_events
        if kind == "idle":
            return self._idle >= trigger["seconds"] and not self.player.story_status
        if kind == "revisit":
            return bool(set(trigger["zones"]) & events["revisited"]) and not self.player.story_status
        return trigger["zone"] in events[{"zone": "zones", "zone_enter": "entered", "outside_zone": "outside"}[kind]]

    def _dispatch(self, events, advance=True):
        for scene in self.act.data["scenes"]:
            flag = f"story:{self.book.id}:scene:{self.act.id}:{scene['id']}"
            if (not self._conditions(scene) or (scene.get("once", True) and flag in self._flags)
                    or self._clock < self._cooldowns.get((self.act.id, scene["id"]), 0)
                    or not self._triggered(scene["trigger"], events)):
                continue
            if scene.get("once", True):
                self._flags.add(flag)
            self._consume_events(scene["trigger"])
            self._cooldowns[self.act.id, scene["id"]] = self._clock + scene.get("cooldown", 0)
            self._prepend(self.act, scene["steps"])
            if advance:
                self._advance()
            return True
        return False

    def _consume_events(self, trigger):
        if "any" in trigger:
            for child in trigger["any"]:
                self._consume_events(child)
        elif trigger["type"] == "event":
            self.player.story_events.discard(trigger["name"])

    def update(self, delta_time):
        if self.dialog is not None or self.puzzle_active or self.next_level is not None or self.player.creator_mode:
            return
        if self._wait_seconds > 0:
            self._wait_seconds = max(0, self._wait_seconds - delta_time)
            if self._wait_seconds == 0:
                self.controls_locked = False
                self._advance()
            return
        if self._wait_object is not None:
            obj, state = self._wait_object
            if obj.state_name == state and not obj.transitioning:
                self._wait_object = None
                self.controls_locked = False
                self._advance()
            return
        self._clock += delta_time
        self._subtitle_time = max(0, self._subtitle_time - delta_time)
        if not self._subtitle_time:
            self.player.story_status = ""
        position = tuple(self.player.body.position)
        self._idle = self._idle + delta_time if math.dist(position, self._last_position) < 0.02 else 0
        self._last_position = position
        zones = {name for name, zone in self.act.data["zones"].items()
                 if all(low < value < high for low, value, high in zip(zone["min"], position, zone["max"]))}
        entered = zones - self._previous_zones
        events = {"load": False, "zones": zones, "entered": entered,
                  "outside": set(self.act.data["zones"]) - zones,
                  "revisited": entered & self._visited_zones, "talk": set(), "interact": set()}
        self._previous_zones = zones
        self._visited_zones.update(zones)
        for name, actor in self.actors.items():
            if actor and actor.talk_requested:
                events["talk"].add(name)
                actor.talk_requested = False
        for obj in self.level.objects:
            if isinstance(obj.entity, StoryProp) and obj.entity.requested:
                events["interact"].add(obj.name)
                obj.entity.requested = False
        self._dispatch(events)
        self._update_hint()

    def open_document(self, document_id, page=0):
        self.stop_dialogue_voice()
        self._document_id = document_id
        _, doc = self.book.document(document_id)
        if doc["type"] == "map":
            self._map_visits.clear()
            self._show_map(page)
        else:
            self._document_pages = [part for authored_page in doc["pages"] for part in text_pages(authored_page, "document")]
            self._show_document(page)

    def _show_map(self, floor):
        _, doc = self.book.document(self._document_id)
        if len(doc["floors"]) != len(self.level.floor_heights):
            raise StoryFormatError(f"{self.book.path}: map {self._document_id} floors do not match level {self.level_name}")
        first = doc["read_flag"] not in self._flags
        self._map_floor = floor % len(self.level.floor_heights)
        self._map_visits.add(self._map_floor)
        walls = floor_plan(self.level, self._map_floor)
        buttons = [DialogButton("← Этаж", "map_prev", ("left",)), DialogButton("Этаж →", "map_next", ("right",))]
        if not first or not doc.get("require_all_floors", False) or len(self._map_visits) == len(doc["floors"]):
            buttons.append(DialogButton("Закрыть   Esc", "map_close", ("escape", "e", "return", doc.get("shortcut", "escape"))))
        pos = self.player.body.position
        here = abs(pos.y - self.level.floor_heights[self._map_floor]) < 2.4
        self.dialog = Dialog(f"{doc['title']} · {self._map_floor + 1} этаж", doc["first_hint"] if first else doc["hint"],
                             tuple(buttons), presentation="plan", plan_walls=walls,
                             plan_labels=tuple(tuple(label) for label in doc["floors"][self._map_floor]),
                             plan_player=(pos.x, pos.z) if here else None,
                             plan_stair=tuple(doc["stair"]) if "stair" in doc else None,
                             plan_highlights=tuple(doc.get("highlights", [])))

    def _show_document(self, page):
        _, doc = self.book.document(self._document_id)
        self._document_page = page
        last_flag = doc.get("last_page_flag", doc["read_flag"] + ":last_page")
        if page == len(self._document_pages) - 1:
            self._flags.add(last_flag)
        buttons = []
        if page:
            buttons.append(DialogButton("← Назад", "document_prev", ("left",)))
        if page < len(self._document_pages) - 1:
            buttons.append(DialogButton("Далее →", "document_next", ("right", "e", "return")))
        if not doc.get("require_last_page", False) or last_flag in self._flags:
            buttons.append(DialogButton("Закрыть", "document_close", ("escape",) if page < len(self._document_pages) - 1
                                        else ("escape", "e", "return")))
        self.dialog = Dialog(f"{doc['title']} · {page + 1} / {len(self._document_pages)}", self._document_pages[page],
                             tuple(buttons), presentation="document")

    def _close_document(self):
        act, doc = self.book.document(self._document_id)
        document_id, self._document_id = self._document_id, None
        if doc["read_flag"] not in self._flags:
            self._flags.add(doc["read_flag"])
            self.player.inventory.add_item(document_id, doc["title"])
            self._prepend(act, doc.get("on_first_read", []))
        for puzzle in self._puzzles.values():
            if doc["read_flag"] == puzzle.data["report_flag"]:
                puzzle.progress.report_read = True
                puzzle.save()
        self._advance()

    def handle_gameplay_key(self, key):
        if self.dialog is not None or self.puzzle_active or self.controls_locked:
            return False
        for act in self.book.acts.values():
            for document_id, doc in act.documents.items():
                if key == doc.get("shortcut") and doc["read_flag"] in self._flags:
                    floor = min(range(len(self.level.floor_heights)), key=lambda i: abs(self.player.body.position.y - self.level.floor_heights[i]))
                    self.open_document(document_id, floor if doc["type"] == "map" else 0)
                    return True
        return False

    def handle_action(self, action):
        if self.dialog is None or action not in {button.action for button in self.dialog.buttons}:
            return False
        if action.startswith("files_"):
            return self._files.handle(action)
        if action == "story_continue":
            if self.act.data["complete_flag"] not in self._flags:
                return False
            self._prepend(self.act, [{"type": "next_act"}])
            self._advance()
        elif action == "story_next" and self._node:
            if not self.reveal_dialogue():
                self._advance()
        elif action.startswith("story_choice:") and self._node and "choice" in self._node:
            index = int(action.split(":")[1])
            option = self._node["options"][index]
            self._flags.add(f"{self._node_act.id}:choice:{self._node['choice']}:{index}")
            self._flags.update(option.get("set_flags", []))
            self._dialogue_nodes(self._node_act, option["lines"])
            self._advance()
        elif action in ("map_prev", "map_next") and self._document_id:
            self._show_map(self._map_floor + (1 if action == "map_next" else -1))
        elif action in ("document_prev", "document_next") and self._document_id:
            self._show_document(self._document_page + (1 if action == "document_next" else -1))
        elif action in ("map_close", "document_close") and self._document_id:
            self._close_document()
        else:
            return super().handle_action(action)
        return True

    def _sync_puzzle_flags(self):
        active = {step["id"] for scene in self.act.data["scenes"] for step in scene["steps"]
                  if step["type"] == "puzzle"}
        for puzzle in self._puzzles.values():
            if puzzle.id not in active:
                continue
            for field, flag in (("solved", puzzle.data["solved_flag"]), ("watched", puzzle.data["watched_flag"]),
                                ("report_read", puzzle.data["report_flag"]), ("aftermath_done", f"{puzzle.id}:aftermath_done")):
                if getattr(puzzle.progress, field):
                    self._flags.add(flag)
        for document_id, document in self.act.documents.items():
            if document["read_flag"] in self._flags and not self.player.inventory.has_item(document_id):
                self.player.inventory.add_item(document_id, document["title"])

    def _close_puzzle(self):
        self._puzzle.save()
        self._puzzle.stop()
        self._puzzle = None
        self.puzzle_view = None
        self._advance()

    def handle_puzzle_action(self, action):
        if self._puzzle is None:
            return False
        puzzle = self._puzzle
        if action == "archive_close":
            self._close_puzzle()
            return True
        if puzzle.playing:
            return False
        if action.startswith("archive_frame:"):
            value = action.partition(":")[2]
            if value not in ("0", "1", "2", "3"):
                return False
            puzzle.click(int(value))
        elif action == "archive_check":
            puzzle.check()
        elif action == "archive_reset":
            puzzle.reset()
        elif action == "archive_hint":
            puzzle.hint()
        elif action == "archive_play":
            puzzle.play()
        else:
            return False
        self._sync_puzzle_flags()
        self.puzzle_view = puzzle.view()
        return True

    def release(self):
        super().release()
        for puzzle in self._puzzles.values():
            puzzle.release()
        if hasattr(self, "_sounds"):
            self._sounds.stop()
        if hasattr(self, "_cue_sounds"):
            self._cue_sounds.stop()
