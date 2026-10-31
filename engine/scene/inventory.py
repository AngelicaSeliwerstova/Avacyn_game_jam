from dataclasses import dataclass


ITEMS_PER_PAGE = 6


@dataclass(frozen=True)
class InventoryItem:
    name: str
    quantity: int = 1
    kind: str = "item"


@dataclass(frozen=True)
class InventoryView:
    items: tuple[InventoryItem, ...] = ()
    page: int = 0
    close_key: str = "Tab"

    @property
    def page_count(self):
        return max(1, (len(self.items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
