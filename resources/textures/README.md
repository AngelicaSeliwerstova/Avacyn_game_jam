# Текстуры окружения

В каталоге сохранены исходные материалы проекта и подключён пользовательский
`Avacyn_Hospital_Texture_Pack.zip`: 32 материала, каждый в вариантах 128×128
и 256×256, всего 64 новых PNG. Исходные изображения пакета не изменены.

Все материалы зарегистрированы в `MATERIAL_TEXTURES` в `config/settings.py`
и доступны через F8 в Creator. `TEXTURE_RESOLUTION` выбирает 128 или 256;
старые `brick`, `plaster`, `hospital_tiles`, `hospital_floor` используют свои
фиксированные исходники 128×128.

Мирный первый этаж использует `hospital_tile_cream`, `linoleum_blue_gray`,
`ceiling_acoustic_panels`, обычную окраску стен и дверей. Трёхэтажная больница
использует `hospital_tile_ruined`, `floor_tile_dirty`, `plaster_water_damage`,
`concrete_cracked`, `wood_rotten` и `door_aged_wood`.

`Box.material` задаёт материал блока, `Level.floor_material` — пола.
Второе значение в `MATERIAL_TEXTURES` задаёт размер повторения в метрах.
PNG повторяются в мировых координатах; двери и деревянная мебель могут
использовать локальные координаты, чтобы рисунок двигался вместе с объектом.
Вблизи применяется nearest, вдали — mipmaps и анизотропная фильтрация.

[Исходное описание пакета и условия использования](HOSPITAL_PACK_README.md) ·
[Манифест материалов](hospital_pack_manifest.json) ·
[Карты и переходы](../../docs/LEVELS.md)
