"""Locations for writable data in source runs and portable Windows releases."""
from pathlib import Path
import sys


def data_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]
