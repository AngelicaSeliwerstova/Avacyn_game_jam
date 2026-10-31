import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pygame

from config import controls
from engine.core.application import Application
from game.inventory import Inventory


class InventoryTests(unittest.TestCase):
    def test_items_quantities_and_keys_share_one_inventory(self):
        inventory = Inventory()
        inventory.add_item("bandage", "Бинт", 2)
        inventory.add_item("bandage", "Бинт", 1)
        inventory.add_key("ward", "Ключ от палаты")
        inventory.add_key("ward", "Ключ от палаты")
        self.assertEqual(len(inventory.items), 2)
        self.assertEqual(inventory.items[0].quantity, 3)
        self.assertEqual(inventory.items[1].quantity, 1)
        self.assertEqual(inventory.key_names, ("Ключ от палаты",))
        self.assertTrue(inventory.has_key("ward"))
        self.assertFalse(inventory.has_key("bandage"))
        with self.assertRaises(ValueError):
            inventory.add_item("ward", "Other item")

    def test_invalid_quantities_are_rejected(self):
        for value in (0, -1, 1.5, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Inventory().add_item("item", "Предмет", value)

    def app(self):
        player = SimpleNamespace(inventory=Inventory())
        return Application((640, 480), (640, 480), "test", 60, (0, 0, 0), (3, 3), False,
                           player, controls.INPUT_BINDINGS, Mock())

    def send(self, app, device, *events):
        with patch("pygame.event.get", return_value=events):
            app._handle_events(device, Mock())

    def test_tab_toggles_without_repeats_and_escape_returns_to_game(self):
        app, device = self.app(), Mock()
        tab = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB)
        self.send(app, device, tab)
        self.assertTrue(app._simulation_paused)
        self.assertEqual(app._inventory_view().items, ())
        device.begin_modal.assert_called_once()
        self.send(app, device, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, repeat=True))
        self.assertTrue(app._inventory_open)
        self.send(app, device, tab)
        self.assertFalse(app._simulation_paused)
        device.end_modal.assert_called_once()
        self.send(app, device, tab, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertFalse(app._inventory_open)

    def test_gameplay_events_are_swallowed_and_pages_remain_in_bounds(self):
        app, device = self.app(), Mock()
        for index in range(15):
            app._controlled_entity.inventory.add_key(str(index), f"Key {index}")
        self.send(app, device, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
        self.send(app, device, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e),
                  pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1),
                  pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F6))
        device.handle_event.assert_not_called()
        self.send(app, device, pygame.event.Event(pygame.MOUSEWHEEL, y=-99))
        self.assertEqual(app._inventory_view().page, 2)
        self.send(app, device, pygame.event.Event(pygame.MOUSEWHEEL, y=99))
        self.assertEqual(app._inventory_view().page, 0)

    def test_inventory_does_not_intercept_end_of_game_dialog(self):
        from engine.scene.session import Dialog, DialogButton
        app, device = self.app(), Mock()
        app._session.dialog = Dialog("End", "", (DialogButton("Quit", "quit", ("escape",)),))
        self.send(app, device, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
        self.assertFalse(app._inventory_open)
        device.begin_modal.assert_not_called()
        self.send(app, device, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(app._result, "quit")
