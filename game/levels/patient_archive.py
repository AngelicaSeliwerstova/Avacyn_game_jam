"""Reception filing cabinet, dated drawers and the physical 1981 case file."""

from dataclasses import replace

from engine.scene.box import Box
from engine.scene.interaction import Interaction
from engine.scene.object import ObjectState, SceneObject
from game.levels.story_props import StoryProp


ARCHIVE_YEARS = (1975, 1978, 1981, 1985, 1990)
ARCHIVE_LABEL_SIZE = (0.80, 0.22)
ARCHIVE_HEADING_SIZE = (2.9, 0.30)
ARCHIVE_OFFICE_SIZE = (1.1, 0.28)
ARCHIVE_DRAWER_ID = "patient_archive_1981"
ARCHIVE_OPEN_FLAG = "act0:archive_1981_open"
ARCHIVE_LETTER_POSITION = (9.78, 1.58, 1.81)
DRAWER_TRAVEL = 0.74


def build_patient_archive():
    x, z = 10.6, 0.8
    metal = (0.24, 0.29, 0.26)

    def part(dx, y, dz, size, *, color=metal, material="metal_scratched_dark"):
        return Box((x + dx, y, z + dz), size, material=material, color=color, local_texture=True)

    shell = (
        part(0, 1.48, -0.49, (3.4, 2.96, 0.10)),
        part(0, 0.17, 0, (3.4, 0.34, 1.08)),
        part(0, 2.80, 0, (3.4, 0.32, 1.08)),
        part(0, 2.80, 0.547, (*ARCHIVE_HEADING_SIZE, 0.012), material="archive_heading", color=None),
    )
    shell += tuple(part(dx, 1.48, 0, (0.08, 2.96, 1.08)) for dx in (-1.66, 0, 1.66))
    shell += tuple(part(0, y, 0, (3.3, 0.04, 1.06)) for y in (0.20, 1.00, 1.81, 2.61))
    objects = [SceneObject("patient_archive", {"default": ObjectState(shell,
        interaction=Interaction("Шкаф медицинских дел", "Архив больницы за разные годы.",
                                "Открыть архив", "story", "patient_archive"), selection_box=shell[3])},
        entity=StoryProp(name="patient_archive"))]

    for index, year in enumerate(ARCHIVE_YEARS):
        dx = -0.82 if index % 2 == 0 else 0.82
        y = 2.20 - (index // 2) * 0.81
        front = (
            part(dx, y, 0.55, (1.54, 0.74, 0.08)),
            part(dx, y + 0.075, 0.598, (*ARCHIVE_LABEL_SIZE, 0.014),
                 material=f"archive_year_{year}", color=None),
            part(dx, y - 0.10, 0.65, (0.34, 0.045, 0.08), color=(0.60, 0.56, 0.40)),
        )
        name = ARCHIVE_DRAWER_ID if year == 1981 else f"patient_archive_{year}"
        title = f"Архив — {year} год"
        if year != 1981:
            objects.append(SceneObject(name, {"default": ObjectState(front,
                interaction=Interaction(title, f"Медицинские документы за {year} год.", "Открыть архив", "story", name),
                selection_box=front[0])}, entity=StoryProp(name=name)))
            continue
        # The tray, files, label and handle all slide together. The letter is
        # revealed by the story only after this physical animation finishes.
        tray = (
            part(dx, y - 0.33, 0.04, (1.48, 0.04, 0.94)),
            part(dx - 0.72, y - 0.08, 0.04, (0.04, 0.45, 0.94)),
            part(dx + 0.72, y - 0.08, 0.04, (0.04, 0.45, 0.94)),
            part(dx, y - 0.08, -0.41, (1.48, 0.45, 0.04)),
        )
        files = tuple(part(dx + shift, y + 0.11 + i * 0.022, 0.25 - i * 0.13,
                           (0.77, 0.045, 0.42), color=color, material="wood")
                      for i, (shift, color) in enumerate(((0, (0.48, 0.37, 0.22)),
                                                         (0.02, (0.58, 0.49, 0.31)),
                                                         (-0.02, (0.68, 0.57, 0.38)))))
        tag = part(dx + 0.27, y + 0.19, 0.27, (0.10, 0.012, 0.34), color=(0.64, 0.09, 0.06), material="wood")
        closed = front + tray + files + (tag,)
        opened = tuple(replace(b, position=(b.position[0], b.position[1], b.position[2] + DRAWER_TRAVEL))
                       for b in closed)
        objects.append(SceneObject(name, {
            "default": ObjectState(closed, interaction=Interaction(title, "Ящик 1981 года.", "Открыть ящик 1981", "story", name),
                                   selection_box=front[0]),
            "open": ObjectState(opened, interaction=Interaction(title, "Внутри дело с красной архивной меткой.", "Открыть архив", "story", name),
                                selection_box=opened[0]),
        }, transition_seconds={"open": 0.8},
            entity=StoryProp(name=name, reveal_after_open="archive_case_081"), static_shadows=False))
    # The tagged key is exposed only when the folder is closed, then collected
    # automatically after the discovery dialogue.
    kx, ky, kz = ARCHIVE_LETTER_POSITION
    key_parts = tuple(Box((kx + dx, ky - .06, kz + dz), size, material="metal_scratched_dark")
                      for dx, dz, size in ((-.15, 0, (.03,.025,.18)),
                                           (-.05, 0, (.03,.025,.18)),
                                           (-.10, -.09, (.13,.025,.025)),
                                           (-.10, .09, (.13,.025,.025)),
                                           (.10, 0, (.28,.025,.03)),
                                           (.20, .04, (.03,.025,.10)),
                                           (.28, -.06, (.20,.018,.12))))
    objects.append(SceneObject("archive_second_floor_key", {
        "default": ObjectState(key_parts, collidable=False), "hidden": ObjectState()}, initial="hidden"))
    return tuple(objects)


def restore_patient_archive(level, flags):
    if ARCHIVE_OPEN_FLAG not in flags and "act0:letter_read" not in flags:
        return
    for obj in level.objects:
        if obj.name == ARCHIVE_DRAWER_ID:
            obj.set_state("open")
            obj.update(1)
        elif obj.name == "archive_case_081":
            obj.set_state("removed" if "act0:key_taken" in flags else "default")
