# Avacyn Game Jam

Основа игры на Python, Pygame и ModernGL. Стартовая локация — `start`:
пустая комната 24×24 метра без врагов, предметов и сюжетных задач.

## Запуск

```powershell
python -m pip install -r requirements.txt
python main.py
```

Для запуска сразу в редакторе:

```powershell
python main.py --creator
```

## Структура

- `config/` — настройки графики, персонажа и клавиш.
- `engine/` — рендер, физика, камеры, объекты и навигация.
- `game/campaign.py` — переходы между локациями и прогресс прохождения.
- `game/levels/location.py` — загрузка самостоятельных JSON-карт.
- `game/levels/objects.py` — ключи, двери, враги и области выхода.
- `game/levels/cameras.py`, `creator.py`, `creator_lights.py` — данные редактора.
- `resources/levels/start.json` — стартовая карта геймджема.
- `resources/` — модели, текстуры и шрифты.
- `tests/` — проверки движка и игровых систем; вспомогательная геометрия
  для физики создаётся только внутри тестов и недоступна в игре.

Старые игровые и отладочные карты удалены. Для новой локации создайте отдельный
JSON-файл в `resources/levels/`. Выбор стартовой карты — `LEVEL_NAME` в
`config/settings.py`.

[Карты и переходы](docs/LEVELS.md) · [Управление и Creator](docs/CONTROLS.md)

## Проверки

```powershell
python -m unittest discover -s tests
```
