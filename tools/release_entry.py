"""Windowed release entry point, retaining diagnostics without a console."""
from pathlib import Path
import sys

# Also allow running this entry point from source for build troubleshooting.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.paths import data_directory


if __name__ == "__main__":
    log_directory = data_directory() / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    with (log_directory / "Avacyn.log").open("w", encoding="utf-8", buffering=1) as log:
        sys.stdout = sys.stderr = log
        try:
            if sys.argv[1:] == ["--smoke-test"]:
                from release_smoke import verify
                verify()
            else:
                from main import main
                main()
        except Exception:
            import traceback
            traceback.print_exc()
            if sys.argv[1:] == ["--smoke-test"]:
                raise SystemExit(1)
            raise
