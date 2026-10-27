from config import settings
from engine.rendering.postprocess import PostProcessSettings
from engine.rendering.fog import FogSettings


def create_fog_settings() -> FogSettings | None:
    if not settings.FOG_ENABLED:
        return None
    return FogSettings(settings.FOG_COLOR, settings.FOG_START, settings.FOG_END)


def create_postprocess_settings() -> PostProcessSettings | None:
    if not settings.POSTPROCESS_ENABLED:
        return None
    return PostProcessSettings(
        tint=settings.COLD_TINT, strength=settings.COLD_STRENGTH, saturation=settings.COLD_SATURATION,
        shadow_color=settings.COLD_SHADOW_COLOR, bloom_color=settings.BLOOM_COLOR,
        bloom_threshold=settings.BLOOM_THRESHOLD, bloom_strength=settings.BLOOM_STRENGTH,
        bloom_radius=settings.BLOOM_RADIUS, downsample=settings.BLOOM_DOWNSAMPLE,
    )
