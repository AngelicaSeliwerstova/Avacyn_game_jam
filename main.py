import argparse
from pathlib import Path

from config import controls, settings
from engine.core.application import Application
from engine.rendering.options import RenderOptions
from game.effects import create_postprocess_presets
from game.materials import create_texture_settings
from game.ui import create_debug_settings, create_hud_style
from game.campaign import Campaign
from game.puzzles.cctv_puzzle import CCTVProgressStore


def run_session(creator_mode: bool = False, debug_mode: bool = False, level_name: str | None = None):
    campaign = Campaign(creator_mode=creator_mode, puzzle_store=CCTVProgressStore(
        Path(__file__).resolve().parent / "saves/hospital_archives.json"))
    scene = campaign.load_level(settings.LEVEL_NAME if level_name is None else level_name)
    app = Application(
        window_size=settings.WINDOW_SIZE,
        render_size=settings.RENDER_SIZE,
        window_title=settings.WINDOW_TITLE,
        fps_limit=settings.FPS_LIMIT,
        background_color=settings.BACKGROUND_COLOR,
        opengl_version=settings.OPENGL_VERSION,
        vsync=settings.VSYNC,
        controlled_entity=scene.player,
        level=scene.level,
        snow=scene.snow,
        input_bindings=controls.INPUT_BINDINGS,
        textures=create_texture_settings(),
        hud_style=create_hud_style(),
        postprocess=scene.postprocess,
        postprocess_presets=create_postprocess_presets(),
        fog=scene.fog,
        dynamic_lights=scene.player.dynamic_lights,
        dynamic_shadow_resolution=settings.DYNAMIC_SHADOW_RESOLUTION,
        systems=scene.systems,  # Includes companion following, enemies, and story/dialog updates.
        session=scene.session,
        debug=create_debug_settings(),
        debug_mode=debug_mode,
        debug_paths=scene.debug_paths,
        scene_loader=campaign.load_level,
        render_options=RenderOptions(settings.FRUSTUM_CULLING, settings.DEPTH_PREPASS,
                                     settings.LOCAL_LIGHTS, settings.LIGHT_GRID_CELL_SIZE,
                                     light_flicker=settings.LIGHT_FLICKER_ENABLED),
    )
    # Application and Campaign now own the scene; do not retain the first location.
    del scene
    return app.run()


def main():
    parser = argparse.ArgumentParser(description="Run the game or its level creator.")
    parser.add_argument(
        "--creator", action="store_true",
        help="start directly in the free-fly level creator",
    )
    parser.add_argument("--debug", action="store_true",
                        help="enable developer panel and log frames slower than 45 FPS")
    parser.add_argument("--level", default=settings.LEVEL_NAME,
                        help="starting map name from resources/levels (e.g. start or peaceful)")
    args = parser.parse_args()
    while run_session(creator_mode=args.creator, debug_mode=args.debug, level_name=args.level) == "restart":
        pass


if __name__ == "__main__":
    main()
