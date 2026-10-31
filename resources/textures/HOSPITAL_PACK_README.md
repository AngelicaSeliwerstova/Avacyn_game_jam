# Avacyn — Abandoned Hospital Texture Pack

Полный набор из **32 оригинальных бесшовных цветовых текстур** для вашей заброшенной больницы.
В каждой папке лежат две версии каждого рисунка: **128×128** и **256×256**, формат RGB PNG (без прозрачности).
Всего **64 PNG-файлов**. Отдельно приложены общая палитра/предпросмотр и манифест.
Все текстуры сгенерированы для этого проекта процедурно, без сторонних фотографий или ассетов. Можно использовать, переделывать и распространять в своей игре.

## Как подключить

1. Скопируйте папки из `resources/textures/` архива в одноимённую папку репозитория Avacyn. Не удаляйте уже существующие текстуры.
2. Откройте `config/settings.py`. Скопируйте блок `MATERIAL_TEXTURES_ADD` из файла `ADD_TO_SETTINGS.py`, включая строчку `MATERIAL_TEXTURES.update(MATERIAL_TEXTURES_ADD)`, **после** существующего словаря `MATERIAL_TEXTURES`.
3. В настройках у вас уже используется `TEXTURE_RESOLUTION = 128`; для версий 256 задайте `TEXTURE_RESOLUTION = 256`. Имена материалов останутся прежними.
4. Назначайте текстуры геометрии как `Box(..., material="stair_diamond_burgundy")` и т. п.
5. Для F8 в Creator добавьте выбранные названия к `self._creator_materials` в `game/entities/player.py`; иначе они есть в движке, но не будут переключаться в Creator.
6. Перед проверкой нового уровня сделайте резервную копию текущего `maze.json`; конфигурация старых комнат и лестниц автоматически не меняется.

## Важное ограничение

Это **цветовые диффузные текстуры** (albedo): без карт нормалей, прозрачности, освещения и 3D-геометрии. Текстуры полностью повторяемы по обеим осям, но эффектный вид лестницы дополнительно требует блоков ступеней, перил, лестничной площадки и источников света. На больших стенах желательно смешивать несколько материалов / детали, чтобы рисунок не выглядел одинаково.

## Рекомендации по материалам

- Центральная лестница: `stair_diamond_burgundy`, `plaster_peeling_ivory`, `floor_mosaic_red`, `rust_iron_heavy`.
- Коридоры: `plaster_water_damage`, `hospital_tile_cream`, `linoleum_blue_gray`.
- Палаты: `plaster_peeling_green`, `linoleum_green`, `ceiling_stained`.
- Операционная: `hospital_tile_mint`, `hospital_checker`, `metal_scratched_dark`.
- Подвал: `concrete_damp`, `plaster_black_mold`, `metal_grate`, `rust_iron_heavy`.
- Двери: `door_painted_teal`, `door_aged_wood`, `metal_chipped_white`.

## Каталог

| Папка | Материал | Описание |
|---|---|---|
| `walls` | `stair_diamond_burgundy` | Бордовая плитка ромбами |
| `walls` | `stair_diamond_cold` | Холодная плитка ромбами |
| `walls` | `hospital_tile_cream` | Больничная кремовая плитка |
| `walls` | `hospital_tile_mint` | Мятная плитка процедурной |
| `walls` | `hospital_tile_ruined` | Разбитая грязная плитка |
| `walls` | `plaster_peeling_ivory` | Облупившаяся светлая штукатурка |
| `walls` | `plaster_peeling_green` | Облупившаяся зелёная краска |
| `walls` | `plaster_water_damage` | Штукатурка с подтёками |
| `walls` | `plaster_black_mold` | Стена с плесенью |
| `walls` | `concrete_cracked` | Растрескавшийся бетон |
| `walls` | `brick_gray` | Старый серый кирпич |
| `walls` | `wallpaper_aged` | Выцветшие обои |
| `floors` | `linoleum_green` | Потёртый зелёный линолеум |
| `floors` | `linoleum_blue_gray` | Сине-серый линолеум |
| `floors` | `hospital_checker` | Шахматный пол больницы |
| `floors` | `floor_tile_dirty` | Грязная напольная плитка |
| `floors` | `floor_mosaic_red` | Мелкая бордовая мозаика |
| `floors` | `terrazzo_gray` | Серое терраццо |
| `floors` | `terrazzo_brown` | Терраццо с бурой крошкой |
| `floors` | `wood_rotten` | Старые гнилые доски |
| `floors` | `concrete_damp` | Сырой бетонный пол |
| `ceilings` | `ceiling_stained` | Потолок с разводами |
| `ceilings` | `ceiling_acoustic_panels` | Пятнистые потолочные панели |
| `ceilings` | `ceiling_mold` | Потолок с плесенью |
| `ceilings` | `ceiling_concrete` | Тёмный бетонный потолок |
| `metals` | `rust_iron_heavy` | Сильная ржавчина |
| `metals` | `metal_chipped_olive` | Сколотая оливковая краска |
| `metals` | `metal_chipped_white` | Сколотая белая краска |
| `metals` | `metal_scratched_dark` | Тёмный поцарапанный металл |
| `metals` | `metal_grate` | Решётка / перфорированный металл |
| `doors` | `door_painted_teal` | Крашеный металл двери |
| `doors` | `door_aged_wood` | Деревянное дверное полотно |

## Размер повторения

В `ADD_TO_SETTINGS.py` все материалы получают повторение через 2 мировые единицы — подходящий стартовый вариант. Если ромбы или плитка выглядят слишком крупно, уменьшите второй параметр до `1.0`; если слишком мелко — увеличьте до `3.0`.
