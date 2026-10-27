class Inventory:
    """Подобранные ключи по идентификатору; названия нужны только интерфейсу."""

    def __init__(self):
        self._keys: dict[str, str] = {}

    def add_key(self, key_id: str, name: str):
        if not key_id.strip() or not name.strip():
            raise ValueError("Key ID and name must not be empty")
        self._keys[key_id] = name

    def has_key(self, key_id: str) -> bool:
        return key_id in self._keys

    @property
    def key_names(self) -> tuple[str, ...]:
        return tuple(self._keys.values())
