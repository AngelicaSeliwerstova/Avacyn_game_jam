from engine.scene.inventory import InventoryItem


class Inventory:
    """Предметы прохождения; ключи также используются для проверки замков."""

    def __init__(self):
        self._items: dict[str, InventoryItem] = {}

    def add_key(self, key_id: str, name: str):
        if not key_id.strip() or not name.strip():
            raise ValueError("Key ID and name must not be empty")
        self._items[key_id] = InventoryItem(name, kind="key")

    def add_item(self, item_id: str, name: str, quantity: int = 1):
        if (not item_id.strip() or not name.strip() or not isinstance(quantity, int)
                or isinstance(quantity, bool) or quantity <= 0):
            raise ValueError("Item needs an ID, name and positive integer quantity")
        previous = self._items.get(item_id)
        if previous is not None and previous.kind == "key":
            raise ValueError("This item ID belongs to a key")
        self._items[item_id] = InventoryItem(name, quantity + (previous.quantity if previous else 0))

    def has_key(self, key_id: str) -> bool:
        item = self._items.get(key_id)
        return item is not None and item.kind == "key"

    def has_item(self, item_id: str) -> bool:
        return item_id in self._items

    @property
    def key_names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self._items.values() if item.kind == "key")

    @property
    def items(self) -> tuple[InventoryItem, ...]:
        return tuple(self._items.values())
