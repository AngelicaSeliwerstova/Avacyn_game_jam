from dataclasses import replace

from config import settings
from engine.rendering.postprocess import PostProcessSettings
from engine.rendering.fog import FogSettings


def create_fog_settings() -> FogSettings | None:
    if not settings.FOG_ENABLED:
        return None
    return FogSettings(settings.FOG_COLOR, settings.FOG_START, settings.FOG_END)


def create_postprocess_settings(preset: str = "cold") -> PostProcessSettings | None:
    if not settings.POSTPROCESS_ENABLED:
        return None
    base = PostProcessSettings(
        tint=settings.COLD_TINT, strength=settings.COLD_STRENGTH, saturation=settings.COLD_SATURATION,
        shadow_color=settings.COLD_SHADOW_COLOR, bloom_color=settings.BLOOM_COLOR,
        bloom_threshold=settings.BLOOM_THRESHOLD, bloom_strength=settings.BLOOM_STRENGTH,
        bloom_radius=settings.BLOOM_RADIUS, downsample=settings.BLOOM_DOWNSAMPLE,
        contrast=settings.POSTPROCESS_CONTRAST, vignette=settings.POSTPROCESS_VIGNETTE,
    )
    return replace(base, **settings.COLOR_PRESETS[preset])


def create_postprocess_presets() -> tuple[tuple[str, PostProcessSettings], ...]:
    if not settings.POSTPROCESS_ENABLED:
        return ()
    return tuple((name, create_postprocess_settings(name)) for name in settings.COLOR_PRESETS)
