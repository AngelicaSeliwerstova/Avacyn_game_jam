"""Build a portable Windows release and ZIP using the active Python environment."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true", help="use only after running the test suite separately")
    args = parser.parse_args()
    if sys.platform != "win32" or platform.machine().lower() not in ("amd64", "x86_64"):
        parser.error("Build this Windows x64 release on Windows x64.")
    if not args.skip_tests:
        subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ROOT, check=True)
    output = ROOT / "dist"
    build_environment = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(ROOT / "build/pyinstaller-cache"))
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--distpath", str(output), "--workpath", str(ROOT / "build"),
        str(ROOT / "Avacyn.spec")], cwd=ROOT, env=build_environment, check=True)
    bundle = output / "Avacyn"
    shutil.copyfile(ROOT / "docs/RELEASE_README.txt", bundle / "README.txt")
    metadata = {"name": "Avacyn", "platform": "Windows x64", "python": platform.python_version(),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "dependencies": {name: importlib.metadata.version(name) for name in
            ("pygame", "moderngl", "glcontext", "PyGLM", "PyTMX", "PyInstaller")}}
    (bundle / "build-info.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    archive = output / "Avacyn-Windows-x64.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                zipped.write(path, path.relative_to(output))
    with archive.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    print(f"Release: {archive} ({archive.stat().st_size / 1024**2:.1f} MiB)")


if __name__ == "__main__":
    main()
