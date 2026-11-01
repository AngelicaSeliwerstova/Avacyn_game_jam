# Музыка и акцент при обнаружении крови

| Игровой файл | Источник и автор | Лицензия и изменения |
| --- | --- | --- |
| `hospital_theme.wav` | [PS2 horror / mystery ambient theme — Tarush Singhal](https://opengameart.org/content/ps2-horror-mystery-ambient-theme) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). MP3 переведён в mono PCM WAV, выровнен уровень, удалена постоянная составляющая, сделана петля 94,177 с с перекрёстным затуханием 4 с. Mono уравновешивает исходную панораму. |
| `blood_sting.wav` | [Creepy Piano Sfx — MouthlessGames, файл bam.mp3](https://opengameart.org/content/creepy-piano-sfx) | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). Использованы первые 3,6 с, добавлено затухание хвоста 1 с; mono PCM WAV, выровнен уровень, удалена постоянная составляющая. |

**Атрибуция:** “Creepy Piano Sfx” by MouthlessGames,
https://opengameart.org/content/creepy-piano-sfx,
licensed under Creative Commons Attribution 3.0 Unported,
https://creativecommons.org/licenses/by/3.0/.
Adapted: excerpt from bam.mp3, mono conversion, level adjustment and fade-out.
При распространении игры сохраняйте это указание авторства вместе с ресурсами
или переносите его в титры / файл благодарностей.

Лицензии проверены на страницах OpenGameArt 1 ноября 2026 г.
`sources.json` содержит URL оригиналов, параметры обработки и SHA-256.
Это загруженные произведения авторов, не синтезированные для проекта звуки.
Формат: 44 100 Гц, 16 бит, mono PCM WAV. Интернет при игре не нужен.

В заброшенной больнице музыка играет негромко на отдельном канале, приглушается
в диалогах и выключается при чёрном экране и в Creator вместе с остальным фоном.
В мирной больнице сохраняется существующий рабочий фон.

При первом попадании одной из крупных луж у подножия лестницы в кадр звучит
короткий тревожный фортепианный удар. Проверяются реальная камера, расстояние
до 18 м и отсутствие стен, перекрытий и закрытых дверей на линии взгляда.
Во время паузы и в Creator обнаружение не срабатывает. Флаг
`hospital:stair_blood_seen` хранится в прогрессе кампании: повторный взгляд и
возвращение на карту не повторяют акцент; новая игра сбрасывает его.
На время акцента музыка приглушается и за 3 с возвращается к обычному уровню.

Громкости задаются полями `music.volume` и `blood_cue.volume` профиля
`abandoned` в [../hospital/ambience.json](../hospital/ambience.json).
На них также действует общая `AMBIENCE_VOLUME` в `config/settings.py`.
Каналы музыки и акцента зарезервированы отдельно от шагов, речи и приборов.

Повторная подготовка из корня проекта:

```powershell
.\.venv\Scripts\python.exe tools/prepare_music.py
```

Кэш оригинальных MP3 и HTML со сведениями о лицензиях:
`artifacts/music-sources/`.
