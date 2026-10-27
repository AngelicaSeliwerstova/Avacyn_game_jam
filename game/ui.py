from pathlib import Path

from config import settings
from engine.debug.panel import DebugSettings
from engine.rendering.hud import HudStyle


FONT_ROOT = Path(__file__).resolve().parents[1] / "resources" / "fonts"


def create_hud_style() -> HudStyle:
    return HudStyle(
        font_size=settings.HUD_FONT_SIZE, margin=settings.HUD_MARGIN,
        font_path=FONT_ROOT / settings.HUD_FONT,
        heading_font_path=FONT_ROOT / settings.HUD_HEADING_FONT,
        antialias=settings.HUD_FONT_ANTIALIAS,
    )


def create_debug_settings() -> DebugSettings:
    return DebugSettings(
        enabled=settings.DEBUG_ENABLED, refresh_interval=settings.DEBUG_REFRESH_INTERVAL,
        font_size=settings.DEBUG_FONT_SIZE, margin=settings.DEBUG_MARGIN,
        font_path=FONT_ROOT / settings.DEBUG_FONT, antialias=settings.HUD_FONT_ANTIALIAS,
    )
