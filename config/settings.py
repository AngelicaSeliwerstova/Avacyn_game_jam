"""Изменяемые параметры приложения, окна и отрисовки."""

# Размер окна в экранных пикселях: ширина, высота.
WINDOW_SIZE = (1280, 960)
WINDOW_TITLE = "Авацин"

# Комфортный размер 3D-кадра. Для строгого PSX-режима: (320, 240).
# Он не меняется при изменении размера окна.
RENDER_SIZE = (640, 480)

# Максимальная частота кадров.
FPS_LIMIT = 60

AUDIO_ENABLED = True
AMBIENCE_VOLUME = 0.65
AMBIENCE_DIALOGUE_GAIN = 0.30
FOOTSTEP_PLAYER_VOLUME = 0.28
FOOTSTEP_DOCTOR_VOLUME = 0.72
FOOTSTEP_HEARING_RANGE = 18.0

# --debug включает диагностику, F3 скрывает панель. Интервал указан в секундах.
DEBUG_REFRESH_INTERVAL = 0.25
DEBUG_FONT_SIZE = 12
DEBUG_FONT = "SourceSans3-Regular.ttf"
DEBUG_MARGIN = 8

# Отсечение за пределами камеры, проход глубины и локальные списки ламп.
FRUSTUM_CULLING = True
DEPTH_PREPASS = True
LOCAL_LIGHTS = True
LIGHT_GRID_CELL_SIZE = 4.0

# Версия OpenGL и синхронизация показа кадров с монитором.
OPENGL_VERSION = (3, 3)
VSYNC = True

# Цвет очистки кадра: красный, зелёный, синий (0–255).
BACKGROUND_COLOR = (18, 18, 24)

# Холодный синий оттенок и мягкое свечение ярких областей. RGB здесь от 0 до 1,
# у COLD_TINT значения выше 1 усиливают соответствующий цветовой канал.
POSTPROCESS_ENABLED = True
COLD_TINT = (0.65, 0.85, 1.25)
COLD_STRENGTH = 0.75
COLD_SATURATION = 0.65
COLD_SHADOW_COLOR = (0.02, 0.04, 0.08)
BLOOM_COLOR = (0.45, 0.65, 1.0)
BLOOM_THRESHOLD = 0.55
BLOOM_STRENGTH = 0.45
BLOOM_RADIUS = 1.0
BLOOM_DOWNSAMPLE = 4

# F5 перебирает цветовые пресеты. mist - начальный вид; cold использует COLD_* выше.
COLOR_PRESET = "mist"
POSTPROCESS_CONTRAST = 1.05
POSTPROCESS_VIGNETTE = 0.20
COLOR_PRESETS = {
    "mist": {"tint": (0.94, 1.0, 0.96), "strength": 0.65, "saturation": 0.45,
             "shadow_color": (0.018, 0.022, 0.020), "bloom_color": (0.80, 0.88, 0.85), "bloom_strength": 0.25},
    "cold": {},
    "rose": {"tint": (1.18, 0.72, 0.92), "strength": 0.80, "saturation": 0.55,
             "shadow_color": (0.045, 0.015, 0.035), "bloom_color": (1.0, 0.50, 0.72), "bloom_strength": 0.32},
    "red": {"tint": (1.30, 0.40, 0.30), "strength": 0.85, "saturation": 0.50,
            "shadow_color": (0.035, 0.007, 0.005), "bloom_color": (1.0, 0.30, 0.16),
            "bloom_strength": 0.28, "contrast": 1.10, "vignette": 0.28},
    "sickly": {"tint": (0.82, 1.08, 0.65), "strength": 0.75, "saturation": 0.45,
               "shadow_color": (0.018, 0.030, 0.010), "bloom_color": (0.70, 0.92, 0.45), "bloom_strength": 0.25},
    "sepia": {"tint": (1.14, 0.92, 0.65), "strength": 0.75, "saturation": 0.40,
              "shadow_color": (0.030, 0.020, 0.009), "bloom_color": (1.0, 0.76, 0.40), "bloom_strength": 0.25},
}

# Дальний туман: RGB от 0 до 1, расстояния в мировых единицах.
FOG_ENABLED = True
FOG_COLOR = (0.27, 0.28, 0.27)
FOG_START = 4.0
FOG_END = 28.0

# Мерцают только лампы с описанием flicker в данных уровня.
LIGHT_FLICKER_ENABLED = True

# Фонарик на F. Углы задают половину конуса, расстояния - в метрах.
FLASHLIGHT_STARTS_ON = False
FLASHLIGHT_COLOR = (1.0, 0.96, 0.85)
FLASHLIGHT_INTENSITY = 4.5
FLASHLIGHT_RANGE = 18.0
FLASHLIGHT_INNER_ANGLE = 12.0
FLASHLIGHT_OUTER_ANGLE = 24.0
FLASHLIGHT_OFFSET = (0.16, -0.16, 0.04)  # Вправо, вверх и вперёд относительно камеры.
FLASHLIGHT_AIM_DISTANCE = 8.0
FLASHLIGHT_SHADOWS = True
DYNAMIC_SHADOW_RESOLUTION = 512

# Одинаковые RGB-цвета дают однотонный пол, спокойный при движении.
# Для тестовой клетки можно задать разные цвета, например (43, 51, 59) и (59, 66, 74).
FLOOR_COLORS = ((48, 55, 62), (48, 55, 62))

# Текстуры относительно resources/textures. None оставляет цветную поверхность.
TEXTURES_ENABLED = True
FLOOR_TEXTURE = "floors/asphalt_{size}.png"
WALL_TEXTURE = "walls/dirty_plaster_128.png"
FLOOR_TEXTURE_WORLD_SIZE = 2.0  # Мировых единиц на одно повторение картинки.
WALL_TEXTURE_WORLD_SIZE = 2.0
TEXTURE_MIPMAPS = True         # Уменьшенные версии текстур для дальних поверхностей.
TEXTURE_ANISOTROPY = 4.0       # Для наклонных поверхностей; 1 отключает эффект.
TEXTURE_RESOLUTION = 128       # 128 или 256; материалы без второй версии остаются 128.

# Имя материала: (путь, размер повторения в мире). {size} заменяется разрешением выше.
MATERIAL_TEXTURES = {
    "dead_bark": ("nature/dead_bark_{size}.png", 1.2),
    "dead_wood": ("nature/dead_wood_{size}.png", 1.2),
    "asphalt": ("floors/asphalt_{size}.png", 2.0),
    "dirty_tiles": ("floors/dirty_tiles_{size}.png", 2.0),
    "wood": ("floors/rotten_wood_{size}.png", 2.0),
    "concrete": ("walls/cracked_concrete_{size}.png", 2.0),
    "plaster": ("walls/dirty_plaster_128.png", 2.0),
    "hospital_tiles": ("walls/hospital_tiles_128.png", 2.0),
    "hospital_floor": ("walls/hospital_tiles_128.png", 5.0),
    'stair_diamond_burgundy': ('walls/stair_diamond_burgundy_{size}.png', 2.0),
    'stair_diamond_cold': ('walls/stair_diamond_cold_{size}.png', 2.0),
    'hospital_tile_cream': ('walls/hospital_tile_cream_{size}.png', 2.0),
    'hospital_tile_mint': ('walls/hospital_tile_mint_{size}.png', 2.0),
    'hospital_tile_ruined': ('walls/hospital_tile_ruined_{size}.png', 2.0),
    'plaster_peeling_ivory': ('walls/plaster_peeling_ivory_{size}.png', 2.0),
    'plaster_peeling_green': ('walls/plaster_peeling_green_{size}.png', 2.0),
    'plaster_water_damage': ('walls/plaster_water_damage_{size}.png', 2.0),
    'plaster_black_mold': ('walls/plaster_black_mold_{size}.png', 2.0),
    'concrete_cracked': ('walls/concrete_cracked_{size}.png', 2.0),
    'brick_gray': ('walls/brick_gray_{size}.png', 2.0),
    'wallpaper_aged': ('walls/wallpaper_aged_{size}.png', 2.0),
    'linoleum_green': ('floors/linoleum_green_{size}.png', 2.0),
    'linoleum_blue_gray': ('floors/linoleum_blue_gray_{size}.png', 2.0),
    'hospital_checker': ('floors/hospital_checker_{size}.png', 2.0),
    'floor_tile_dirty': ('floors/floor_tile_dirty_{size}.png', 2.0),
    'floor_mosaic_red': ('floors/floor_mosaic_red_{size}.png', 2.0),
    'terrazzo_gray': ('floors/terrazzo_gray_{size}.png', 2.0),
    'terrazzo_brown': ('floors/terrazzo_brown_{size}.png', 2.0),
    'wood_rotten': ('floors/wood_rotten_{size}.png', 2.0),
    'concrete_damp': ('floors/concrete_damp_{size}.png', 2.0),
    'ceiling_stained': ('ceilings/ceiling_stained_{size}.png', 2.0),
    'ceiling_acoustic_panels': ('ceilings/ceiling_acoustic_panels_{size}.png', 2.0),
    'ceiling_mold': ('ceilings/ceiling_mold_{size}.png', 2.0),
    'ceiling_concrete': ('ceilings/ceiling_concrete_{size}.png', 2.0),
    'rust_iron_heavy': ('metals/rust_iron_heavy_{size}.png', 2.0),
    'metal_chipped_olive': ('metals/metal_chipped_olive_{size}.png', 2.0),
    'metal_chipped_white': ('metals/metal_chipped_white_{size}.png', 2.0),
    'metal_scratched_dark': ('metals/metal_scratched_dark_{size}.png', 2.0),
    'metal_grate': ('metals/metal_grate_{size}.png', 2.0),
    'door_painted_teal': ('doors/door_painted_teal_{size}.png', 2.0),
    'door_aged_wood': ('doors/door_aged_wood_{size}.png', 2.0),
    "brick": ("walls/red_brick_128.png", 2.0),
    "rust": ("metals/rust_{size}.png", 2.0),
}

# Dedicated hospital finishes: subtle painted surfaces, upholstery and textiles.
MATERIAL_TEXTURES.update({
    name: (f"surfaces/{name}_{{size}}.png", repeat)
    for name, repeat in {
        "paint_ivory": 2.0, "paint_sage": 2.0, "paint_mint": 2.0,
        "enamel_white": 1.0, "ceramic_white": 0.8, "brushed_steel": 0.7,
        "oak_veneer": 1.4, "vinyl_burgundy": 0.6, "vinyl_sage": 0.6,
        "linen_ivory": 0.5, "blanket_sage": 0.5, "curtain_sage": 0.9,
        "linoleum_sage": 3.5, "ceiling_clean": 1.2, "tile_mint_clean": 1.2,
        "linen_worn": 0.5, "blanket_worn": 0.5, "curtain_worn": 0.9,
        "tile_cream_clean": 1.2, "linoleum_blue_clean": 3.5,
        "vinyl_burgundy_worn": 0.6, "vinyl_sage_worn": 0.6,
    }.items()
})
# Four tiles across the wall images; keep ceramics close to a 30 cm tile.
for _hospital_name in ("hospital_tile_cream", "hospital_tile_mint", "hospital_tile_ruined",
                       "stair_diamond_burgundy", "stair_diamond_cold"):
    MATERIAL_TEXTURES[_hospital_name] = (MATERIAL_TEXTURES[_hospital_name][0], 1.2)
MATERIAL_TEXTURES["floor_tile_dirty"] = ("floors/floor_tile_dirty_{size}.png", 1.6)
MATERIAL_TEXTURES["hospital_checker"] = ("floors/hospital_checker_{size}.png", 2.4)
MATERIAL_TEXTURES["ceiling_acoustic_panels"] = ("ceilings/ceiling_acoustic_panels_{size}.png", 1.2)

# Спокойный снег в открытых проходах. Размер и высота — в мировых единицах.
SNOW_ENABLED = True
SNOW_COUNT = 600
SNOW_HEIGHT = 5.0
SNOW_FALL_SPEED = 0.65          # Мировых единиц в секунду.
SNOW_FLAKE_SIZE = 0.05
SNOW_COLOR = (210, 220, 235)
SNOW_SEED = 7                  # Одинаковое начальное расположение при запуске.

# Стартовая карта из resources/levels/<имя>.json.
LEVEL_NAME = "peaceful"
HUD_FONT_SIZE = 18
HUD_MARGIN = 8
HUD_FONT = "SourceSans3-Regular.ttf"  # Файлы относительно resources/fonts.
HUD_HEADING_FONT = "SourceSans3-Semibold.ttf"
HUD_FONT_ANTIALIAS = True

# Высота игрока и параметры камеры.
PLAYER_EYE_HEIGHT = 1.6
PLAYER_HEIGHT = 1.8
PLAYER_CROUCH_HEIGHT = 1.0
PLAYER_CROUCH_EYE_HEIGHT = 0.85
PLAYER_STANCE_SPEED = 5.0       # Скорость изменения высоты тела при приседе, м/с.
PLAYER_STEP_HEIGHT = 0.3         # Максимальная высота автоматического подъёма.
GRAVITY = 18.0
JUMP_HEIGHT = 0.9              # Высота прыжка над текущей опорой.
PHYSICS_STEP = 1 / 120          # Фиксированный шаг физики в секундах.
STAIR_CAMERA_SMOOTHING = 8.0    # Больше значение - быстрее камера догоняет тело.

# Тревожная тряска при ходьбе по ступеням; углы: тангаж, поворот, крен.
STAIR_SHAKE_ENABLED = True
STAIR_SHAKE_ROTATION_DEGREES = (0.35, 0.25, 0.28)
STAIR_SHAKE_FREQUENCY = 4.2
STAIR_SHAKE_FADE_IN = 0.45
STAIR_SHAKE_FADE_OUT = 0.60
STAIR_STRESS_FADE_IN = 1.4
STAIR_STRESS_FADE_OUT = 2.4
STAIR_COMMENT_MIN_WALK_SECONDS = 1.0
STAIR_COMMENT_REST_SECONDS = 0.65

# Модель игрока в GLB 2.0; путь относительно resources/models.
PLAYER_MODEL = "player/girl_chestnut_black_stockings.glb"
PLAYER_MODEL_OFFSET = (0.0, -0.04, 0.0)
PLAYER_MODEL_ROTATION = (0.0, 180.0, 0.0)
PLAYER_MODEL_SCALE = 1.14
DOCTOR_MODEL = "doctor/girl_white.glb"
DOCTOR_MODEL_OFFSET = (0.0, -0.04, 0.0)
DOCTOR_MODEL_ROTATION = (0.0, 180.0, 0.0)
DOCTOR_MODEL_SCALE = 1.14
PLAYER_CAMERA_DISTANCE = 3.5
PLAYER_CAMERA_HEIGHT = 0.1
PLAYER_CAMERA_WALL_MARGIN = 0.2
PLAYER_CAMERA_SHOULDER_OFFSET = 0.4
PLAYER_TURN_SPEED_DEGREES = 180.0  # Танковое управление: скорость поворота A/D, градусы/с.

CAMERA_FOV_DEGREES = 60.0  # Вертикальный угол обзора.
CAMERA_ZOOM_FOV_DEGREES = 35.0  # Меньше угол - сильнее приближение на ПКМ.
CAMERA_ZOOM_SPEED = 12.0       # Скорость плавного перехода, 1/с.
CAMERA_NEAR = 0.1         # Ближняя граница видимости.
CAMERA_FAR = 100.0        # Дальняя граница видимости.

# Управление от первого лица.
MOVE_SPEED = 3.5 / 1.5            # Мировых единиц в секунду; замедление в 1,5 раза.
SPRINT_SPEED = 6.5 / 1.5          # При удержании Shift.
CROUCH_SPEED = 1.7 / 1.5          # При удержании Ctrl; имеет приоритет над бегом.
INTERACTION_REACH = 2.5           # Расстояние от камеры до поверхности объекта, м.
INTERACTION_MESSAGE_SECONDS = 3.0

# Медленная улитка-преследователь. Значения можно переопределить в карте.
ENEMIES_ENABLED = True
ENEMY_SPEED = 2.95
ENEMY_REPATH_INTERVAL = 0.75
ENEMY_STOP_DISTANCE = 0.5
ENEMY_CATCH_MARGIN = 0.03       # Допуск касания у границы коллайдера игрока, м.
ENEMY_RADIUS = 0.32
ENEMY_HEIGHT = 0.45
ENEMY_STEP_HEIGHT = 0.26

MOUSE_SENSITIVITY = 0.12          # Градусов на пиксель движения мыши.
PITCH_LIMIT_DEGREES = 80.0        # Предел обзора вверх и вниз.
MAX_DELTA_TIME = 0.1              # Ограничение шага после длительной задержки.
PLAYER_RADIUS = 0.25
COLLISION_MAX_STEP = 0.1          # Максимальная длина подшага в мировых единицах.

# Размер плитки пола по умолчанию.
FLOOR_TILE_SIZE = 1.0
