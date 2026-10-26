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

# Спокойный снег в открытых проходах. Размер и высота — в мировых единицах.
SNOW_ENABLED = True
SNOW_COUNT = 600
SNOW_HEIGHT = 5.0
SNOW_FALL_SPEED = 0.65          # Мировых единиц в секунду.
SNOW_FLAKE_SIZE = 0.05
SNOW_COLOR = (210, 220, 235)
SNOW_SEED = 7                  # Одинаковое начальное расположение при запуске.

# Выбор тестовой сцены: "stairs", "corridor" или "demo".
LEVEL_NAME = "stairs"

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
