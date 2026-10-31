# Avacyn Game Jam

Игра на Python, Pygame и ModernGL. Стартовая локация — `start`: трёхэтажная
больница 43×29 метров с кабинетами, коридорами, холлами и большой винтовой
лестницей, соединяющей все три этажа.

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
- `game/levels/hospital.py` — планировка и мебель первого этажа больницы.
- `game/levels/hospital_props.py` — диваны, растения, шкафы, тележки и детали рабочих мест.
- `game/levels/hospital_storeys.py` — этажи, перекрытия, проёмы и выходы с лестницы.
- `game/levels/spiral.py` — винтовой марш, ограждения и верхняя площадка.
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
