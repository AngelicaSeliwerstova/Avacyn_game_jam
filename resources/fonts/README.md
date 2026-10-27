# Шрифты

- `SourceSans3-Regular.ttf` - основной текст интерфейса и диагностика F3.
- `SourceSans3-Semibold.ttf` - заголовок панели и подпись действия.
- `LICENSE-SourceSans3.md` - исходная лицензия SIL Open Font License 1.1.

Источник: [Adobe Source Sans 3](https://github.com/adobe-fonts/source-sans), версия файлов из коммита `87b37a2daaed80fcb8e8ccb0085c4d72ddade12e`. Файлы шрифтов сохранены без изменений; установка в Windows не требуется. Поддерживаются латиница и кириллица.

В `config/settings.py`:

- `HUD_FONT`, `HUD_HEADING_FONT`, `DEBUG_FONT` - имена файлов в этой папке.
- `HUD_FONT_SIZE`, `DEBUG_FONT_SIZE` - размеры во внутреннем кадре игры.
- `HUD_FONT_ANTIALIAS` - сглаживание краёв букв.

`game/ui.py` передаёт движку абсолютные пути к этим ресурсам. Размеры `pygame.font.Font(None, ...)` и TTF не совпадают визуально; для нового шрифта диагностика использует размер 12, игровой текст - 18.
