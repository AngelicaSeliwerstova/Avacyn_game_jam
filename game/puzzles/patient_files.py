"""Archive drawers and the key concealed beneath the 1981 folder."""

from engine.scene.session import Dialog, DialogButton
from game.levels.patient_archive import ARCHIVE_DRAWER_ID, ARCHIVE_OPEN_FLAG, ARCHIVE_YEARS


REQUIRED_FLAGS = frozenset((ARCHIVE_OPEN_FLAG, "act0:case_081_open",
                            "act0:letter_read", "act0:archive_reviewed"))


class PatientFiles:
    def __init__(self, session):
        self.session = session
        self.year = None
        self.case = False

    def show(self, *, case=False):
        self.case = case
        if case:
            self.year = 1981
        else:
            self.year = None
        self.refresh()

    def refresh(self, message=""):
        flags = self.session._flags
        close = DialogButton("Закрыть архив · Esc", "files_close", ("escape",))
        back = DialogButton("К ящикам", "files_back", ("backspace",))
        if self.year is None:
            buttons = tuple(DialogButton(str(year), f"files_year:{year}") for year in ARCHIVE_YEARS) + (close,)
            text = "Документы хранятся по годам. Выберите ящик.\nВрач упоминал 1981 год."
            title = "Архив медицинских дел"
        elif self.case:
            title = "Медицинское дело №081"
            text = "Архив за 1981 год.\nВ старой папке лежит сложенное письмо «Новая жизнь»."
            buttons = (
                DialogButton(("✓ " if "act0:letter_read" in flags else "") + "Письмо «Новая жизнь»", "files_letter", ("1",)),
                *((DialogButton("Закрыть папку и осмотреть под ней", "files_take_key", ("e", "return")),)
                  if REQUIRED_FLAGS <= flags and "act0:key_taken" not in flags else ()),
                back, close)
        else:
            title = f"Ящик · {self.year} год"
            if self.year == 1981:
                text = "Среди старых папок выделяется красная архивная метка.\nМЕДИЦИНСКОЕ ДЕЛО №081 · ФИО: [УДАЛЕНО]"
                buttons = (DialogButton("Открыть дело №081", "files_case", ("1", "e", "return")), back, close)
            else:
                text = "Обычные больничные документы за этот год.\nМожно просмотреть записи или вернуться к ящикам."
                buttons = tuple(DialogButton(f"Медицинская запись №{index + 1:02}", f"files_misc:{index}", (str(index + 1),))
                                for index in range(3)) + (back, close)
        self.session.dialog = Dialog(title, message or text, buttons, presentation="filing_archive",
                                     filing_year=self.year, filing_case=self.case)

    def handle(self, action):
        session = self.session
        if action in ("files_close", "files_take_key"):
            ready = REQUIRED_FLAGS <= session._flags and "act0:key_taken" not in session._flags
            if action == "files_take_key" and not ready:
                return False
            if ready:
                session._flags.add("act0:archive_closed")
                session._prepend(session.act, [
                    {"type": "object_state", "object": "archive_case_081", "state": "removed"},
                    {"type": "object_state", "object": "archive_second_floor_key", "state": "default"},
                    {"type": "dialogue", "id": "key_found"},
                    {"type": "grant_key", "id": "second_floor_key", "name": "Ключ от второго этажа — номер стёрт"},
                    {"type": "object_state", "object": "archive_second_floor_key", "state": "hidden"},
                    {"type": "flags", "add": ["act0:key_taken"]},
                    {"type": "audio", "file": "act0/baby_cry_short.wav", "volume": 0.16},
                    {"type": "dialogue", "id": "cry_first"},
                    {"type": "audio", "file": "act0/baby_cry_short.wav", "volume": 0.35},
                    {"type": "dialogue", "id": "cry_second"},
                    {"type": "flags", "add": ["act0:cry_started"]}])
            session._advance()
        elif action == "files_back":
            self.show()
        elif action.startswith("files_year:"):
            try:
                year = int(action.partition(":")[2])
            except ValueError:
                return False
            if year not in ARCHIVE_YEARS:
                return False
            self.year, self.case = year, False
            if year == 1981:
                session._flags.add(ARCHIVE_OPEN_FLAG)
                session._object(ARCHIVE_DRAWER_ID).set_state("open")
            self.refresh()
        elif action == "files_case" and self.year == 1981:
            session._flags.add("act0:case_081_open")
            self.case = True
            self.refresh()
        elif action == "files_letter" and self.case:
            session._prepend(session.act, [{"type": "archive", "case": True}])
            session.open_document("mother_letter")
        elif action.startswith("files_misc:") and self.year in ARCHIVE_YEARS and self.year != 1981:
            index = action.partition(":")[2]
            notes = (
                "Плановый осмотр. Самочувствие стабильное. Назначен повторный приём.",
                "Контрольная консультация. Рекомендации выданы, наблюдение продолжено.",
                "Выписка из журнала приёма. Личное дело передано в архив отделения.")
            if index not in ("0", "1", "2"):
                return False
            session.dialog = Dialog(f"Запись №{int(index) + 1:02} · {self.year}",
                f"Архив за {self.year} год\nФИО: [СВЕДЕНИЯ УДАЛЕНЫ]\n\n{notes[int(index)]}",
                (DialogButton("Назад к ящику", "files_return", ("escape", "e", "return")),), presentation="document")
        elif action == "files_return":
            self.refresh()
        else:
            return False
        session._update_hint()
        return True
