# Avacyn Game Jam

Игра на Python, Pygame и ModernGL. Начинаем в `peaceful`: мирной версии больницы
с общей для обоих миров геометрией трёх этажей. После разговора с человеком в кабинете врача загружается
`start` — трёхэтажная версия больницы с винтовой лестницей. Инвентарь переносится между мирами.

## Запуск

Проверенное окружение — Python 3.12. Из PowerShell в папке проекта:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Для создания окружения команда `python` должна указывать на Python 3.12.
Если `.venv` уже подготовлена, достаточно последней команды; активация не нужна.

Для проверки союзника сразу в трёхэтажной больнице, с отображением маршрута:

```powershell
.\.venv\Scripts\python.exe main.py --level start --debug
```

F3 переключает панель диагностики и линии маршрутов. Союзник следует за игроком;
двери нужно открывать на E. Обычный запуск начинает с `peaceful`: поговорите
с человеком в дальнем кабинете врача на E и завершите диалог для перехода в `start`.

Для запуска сразу в редакторе:

```powershell
.\.venv\Scripts\python.exe main.py --creator
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
- `resources/levels/start.json` — трёхэтажная больница после перехода.
- `resources/levels/peaceful.json` — мирная больница с сюжетным ограничением подъёма и переходом после разговора.
- `resources/` — модели, текстуры и шрифты.
- `tests/` — проверки движка и игровых систем; вспомогательная геометрия
  для физики создаётся только внутри тестов и недоступна в игре.

Старые игровые и отладочные карты удалены. Для новой локации создайте отдельный
JSON-файл в `resources/levels/`. Выбор стартовой карты — `--level <имя>`;
по умолчанию используется `LEVEL_NAME` в `config/settings.py`.

[Карты и переходы](docs/LEVELS.md) · [Управление и Creator](docs/CONTROLS.md)

## Проверки

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Только навигация и сопровождение:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_navigation.py"
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_companions.py"
```
