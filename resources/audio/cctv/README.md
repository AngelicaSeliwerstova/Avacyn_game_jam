# Звуки видеорегистратора

`button_click.wav`, `correct.wav`, `incorrect.wav`, `static.wav` и `impact.wav`
процедурно созданы для проекта скриптом `tools/prepare_cctv_assets.py`.
Формат: моно, PCM 16 бит, 44100 Гц. Сторонних мелодий и записей в этих файлах нет.

Шаги в начале записи используют уже включённый CC0 файл больничных шагов;
его источник и обработка указаны в `../hospital/sources.json`.
Звуки и субтитры настраиваются в `resources/puzzles/cctv/archive.json`.
