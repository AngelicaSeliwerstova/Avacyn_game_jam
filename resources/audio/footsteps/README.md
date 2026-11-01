# Шаги

В игре используются отдельные удары, а не зацикленные длинные записи.

- `player_step_01.wav` … `player_step_04.wav`: те же шаги классической обуви,
  что у врача. Мягкие шаги заменены по просьбе пользователя.
- `doctor_step_01.wav` … `doctor_step_04.wav`: обычные сухие шаги классической
  обуви. Добавленное эхо удалено; резкая высокочастотная атака приглушена,
  края нарезки плавные, пик ограничен 60% диапазона PCM.

Формат: mono PCM WAV, 44 100 Гц, 16 бит. Четыре варианта чередуются без
немедленного повтора, с небольшой случайной разницей громкости. Темп следует
реальному движению: бег чаще, присед тише. Неподвижный персонаж, прыжок,
диалог, инвентарь и Creator не порождают шаги.

Источники Freesound:

1. Ранее использованный вариант, теперь не звучит в игре:
   **sgcardinal — Footsteps - Soft Soled Shoes on Tile Floor.WAV**
   https://freesound.org/people/sgcardinal/sounds/395075/
   Публичное HQ-превью: https://cdn.freesound.org/previews/395/395075_4478793-hq.mp3
2. Текущий источник для героини и врача:
   **RaggedyAngst — Footsteps one person CLEAN.wav**
   https://freesound.org/people/RaggedyAngst/sounds/546270/
   Публичное HQ-превью: https://cdn.freesound.org/previews/546/546270_9188976-hq.mp3

Обе страницы указывают Creative Commons Zero (CC0 1.0):
https://creativecommons.org/publicdomain/zero/1.0/
Проверено 1 ноября 2026 г. Использованы публичные превью, не оригиналы за входом.
В игровые файлы вошли короткие фрагменты с обрезкой, плавными краями,
выравниванием уровня и смягчением резких высоких частот. Дополнительного эха нет.

Воспроизводимая нарезка: `python tools/prepare_footsteps.py`; входные превью
ожидается в `artifacts/doctor_steps_source.mp3`.

Настройки в `config/settings.py`: `AUDIO_ENABLED`, `FOOTSTEP_PLAYER_VOLUME`,
`FOOTSTEP_DOCTOR_VOLUME`, `FOOTSTEP_HEARING_RANGE`.
