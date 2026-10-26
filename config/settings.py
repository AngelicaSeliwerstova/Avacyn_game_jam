"""Изменяемые параметры приложения, окна и отрисовки."""

# Размер окна в экранных пикселях: ширина, высота.
WINDOW_SIZE = (1280, 960)
WINDOW_TITLE = "gamek"

# Комфортный размер 3D-кадра. Для строгого PSX-режима: (320, 240).
# Он не меняется при изменении размера окна.
RENDER_SIZE = (640, 480)

# Максимальная частота кадров.
FPS_LIMIT = 60

# Версия OpenGL и синхронизация показа кадров с монитором.
OPENGL_VERSION = (3, 3)
VSYNC = True

# Цвет очистки кадра: красный, зелёный, синий (0–255).
BACKGROUND_COLOR = (18, 18, 24)

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
    "asphalt": ("floors/asphalt_{size}.png", 2.0),
    "dirty_tiles": ("floors/dirty_tiles_{size}.png", 2.0),
    "wood": ("floors/rotten_wood_{size}.png", 2.0),
    "concrete": ("walls/cracked_concrete_{size}.png", 2.0),
    "plaster": ("walls/dirty_plaster_128.png", 2.0),
    "hospital_tiles": ("walls/hospital_tiles_128.png", 2.0),
    "brick": ("walls/red_brick_128.png", 2.0),
    "rust": ("metals/rust_{size}.png", 2.0),
}
STAIRS_FLOOR_MATERIAL = "asphalt"
STAIRS_STEP_MATERIAL = "concrete"
STAIRS_LANDING_MATERIAL = "wood"
CORRIDOR_FLOOR_MATERIAL = "dirty_tiles"
CORRIDOR_WALL_MATERIALS = ("hospital_tiles", "plaster", "brick")  # От старта к повороту.
DEMO_FLOOR_MATERIAL = "wood"
DEMO_CUBE_MATERIAL = "rust"

# Спокойный снег в открытых проходах. Размер и высота — в мировых единицах.
SNOW_ENABLED = True
SNOW_COUNT = 600
SNOW_HEIGHT = 5.0
SNOW_FALL_SPEED = 0.65          # Мировых единиц в секунду.
SNOW_FLAKE_SIZE = 0.05
SNOW_COLOR = (210, 220, 235)
SNOW_SEED = 7                  # Одинаковое начальное расположение при запуске.

# Выбор сцены: "maze", "stairs", "corridor" или "demo".
LEVEL_NAME = "maze"
MAZE_LAYOUT = "maze.json"       # Разметка двух этажей и размеры лестничных клеток.
HUD_FONT_SIZE = 18
HUD_MARGIN = 8

# Высота игрока и параметры камеры.
PLAYER_EYE_HEIGHT = 1.6
PLAYER_HEIGHT = 1.8
PLAYER_STEP_HEIGHT = 0.3         # Максимальная высота автоматического подъёма.
GRAVITY = 18.0
JUMP_HEIGHT = 0.9              # Высота прыжка над текущей опорой.
PHYSICS_STEP = 1 / 120          # Фиксированный шаг физики в секундах.
STAIR_CAMERA_SMOOTHING = 12.0   # Больше значение - быстрее камера догоняет тело.

# Заготовка модели персонажа. Путь относительно resources/models, например "player/player.glb".
# Пока это описание ресурса; чтение GLB и отрисовка модели ещё не подключены.
PLAYER_MODEL = None
PLAYER_MODEL_OFFSET = (0.0, 0.0, 0.0)
PLAYER_MODEL_ROTATION = (0.0, 0.0, 0.0)
PLAYER_MODEL_SCALE = 1.0

# Старт кубовой сцены. Старт коридора хранится в TMX-карте.
CAMERA_POSITION = (3.0, PLAYER_EYE_HEIGHT, 4.0)
CAMERA_TARGET = (0.0, 1.0, 0.0)
CAMERA_FOV_DEGREES = 60.0  # Вертикальный угол обзора.
CAMERA_NEAR = 0.1         # Ближняя граница видимости.
CAMERA_FAR = 100.0        # Дальняя граница видимости.

# Управление от первого лица.
MOVE_SPEED = 2.5                  # Мировых единиц в секунду.
SPRINT_SPEED = 5.0                # При удержании Shift.
MOUSE_SENSITIVITY = 0.12          # Градусов на пиксель движения мыши.
PITCH_LIMIT_DEGREES = 80.0        # Предел обзора вверх и вниз.
MAX_DELTA_TIME = 0.1              # Ограничение шага после длительной задержки.
PLAYER_RADIUS = 0.25
COLLISION_MAX_STEP = 0.1          # Максимальная длина подшага в мировых единицах.

# Кубовая сцена. Координата модели задаёт её центр.
FLOOR_SIZE = (20.0, 20.0)
FLOOR_TILE_SIZE = 1.0
CUBE_SIZE = (2.0, 2.0, 2.0)
CUBE_POSITION = (0.0, CUBE_SIZE[1] / 2, 0.0)

# Тестовая лестница и верхняя площадка.
STAIRS_COUNT = 6
STAIRS_RISE = 0.25
STAIRS_RUN = 0.8
STAIRS_WIDTH = 3.0
STAIRS_START_Z = 2.0
STAIRS_LANDING_DEPTH = 3.0
STAIRS_LANDING_WIDTH = 5.0
STAIRS_SPAWN = (0.0, PLAYER_EYE_HEIGHT, 6.0)
