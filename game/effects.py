from config import settings
from engine.rendering.postprocess import PostProcessSettings


def create_postprocess_settings() -> PostProcessSettings | None:
    if not settings.POSTPROCESS_ENABLED:
        return None
    return PostProcessSettings(
        tint=settings.COLD_TINT, strength=settings.COLD_STRENGTH, saturation=settings.COLD_SATURATION,
        shadow_color=settings.COLD_SHADOW_COLOR, bloom_color=settings.BLOOM_COLOR,
        bloom_threshold=settings.BLOOM_THRESHOLD, bloom_strength=settings.BLOOM_STRENGTH,
        bloom_radius=settings.BLOOM_RADIUS, downsample=settings.BLOOM_DOWNSAMPLE,
    )
