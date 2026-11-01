# Акт 1 «Под софитами» (технический ID `act0`)

Эти WAV включены в игру: сеть и установленный синтезатор речи для запуска не нужны.

| Файлы | Автор и источник | Лицензия / происхождение |
| --- | --- | --- |
| `baby_cry.wav`, `baby_cry_short.wav` | eguaus, [baby crying](https://freesound.org/people/eguaus/sounds/321712/) | CC0 1.0 |
| `monster_growl.wav` | john129pats, [Hybrid Monster Growl](https://freesound.org/people/john129pats/sounds/146558/) | CC0 1.0 |
| `rust_scratch.wav`, `lock_click.wav`, `corridor_unknown.wav` | Процедурные звуки проекта | CC0 1.0 |
| `cradle_memory_01.wav` – `04.wav`, `memory_outro_first_01.wav`, `memory_outro_second_01.wav` | Текст окончательного сценария; синтез Microsoft Irina Desktop (ru-RU), Windows System.Speech | Синтезированные голоса, не запись актёров |

[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) разрешает изменение
и использование, включая коммерческое. Проверка лицензий — 1 ноября 2026 года.
Файлы Freesound получены из общедоступных HQ MP3-превью, обрезаны, сглажены,
нормализованы и сохранены в mono PCM 44,1 кГц/16 бит. У петли плача перекрёстный
переход; точные исходные URL, обработка и SHA-256 — в `sources.json`.

Голоса дочери и матери различаются высотой и темпом, героиня говорит медленнее.
Текст, настройки, длительности и SHA-256 — в `voices.json`. Субтитры автоматически
меняются по измеренной длительности WAV; короткие обычные диалоги сохраняют пикания.
Синтезированная речь отключена по просьбе пользователя (`audio: false`).
Воспоминание и заключительные реплики идут как обычный диалог с пиканиями
и ручным продолжением на E / Enter, без речевой озвучки.
Не включать синтезированную озвучку без прямой просьбы пользователя.

Воспроизведение ассетов:

```powershell
.\.venv\Scripts\python.exe tools/prepare_spotlights_audio.py
powershell -NoProfile -ExecutionPolicy Bypass -File tools/synthesize_spotlights_voices.ps1
```

Вторая команда нужна только при изменении текста озвучки и требует установленного
русского голоса Microsoft Irina Desktop. Можно заменить WAV актёрской записью
и обновить длительности через `tools/time_spotlights_voices.py`.
