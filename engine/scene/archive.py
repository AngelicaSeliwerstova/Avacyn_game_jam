"""Immutable presentation data for the security recorder overlay."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ArchiveFrame:
    id: str
    image: str
    time: str
    title: str
    description: str


@dataclass(frozen=True)
class ArchiveView:
    title: str
    instruction: str
    frames: tuple[ArchiveFrame, ...]
    selected: int | None = None
    solved: bool = False
    hint_available: bool = False
    message: str = ""
    playing: bool = False
    frame_index: int = 0
    speaker: str = ""
    caption: str = ""
    interference: bool = False
