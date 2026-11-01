from pathlib import Path
import unittest
from unittest.mock import patch

from config.paths import data_directory


class ReleasePathTests(unittest.TestCase):
    def test_source_uses_project_directory(self):
        with patch("sys.frozen", False, create=True):
            self.assertEqual(data_directory(), Path(__file__).resolve().parents[1])

    def test_frozen_uses_executable_directory(self):
        executable = Path("portable game/Avacyn.exe").resolve()
        with patch("sys.frozen", True, create=True), patch("sys.executable", str(executable)):
            self.assertEqual(data_directory(), executable.parent)
