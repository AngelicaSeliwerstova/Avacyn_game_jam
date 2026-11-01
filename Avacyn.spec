# Build with: .venv\Scripts\python.exe -m PyInstaller Avacyn.spec
from pathlib import Path
import sys
from PyInstaller.utils.hooks import copy_metadata

root = Path(SPECPATH)
datas = [(str(root / "resources"), "resources"),
         (str(root / "engine/rendering/shaders"), "engine/rendering/shaders"),
         (str(Path(sys.base_prefix) / "LICENSE.txt"), "licenses/python")]
for distribution in ("pygame", "moderngl", "glcontext", "PyGLM", "PyTMX"):
    datas += copy_metadata(distribution)

a = Analysis([str(root / "tools/release_entry.py")], pathex=[str(root), str(root / "tools")],
    binaries=[], datas=datas, hiddenimports=["glcontext.wgl", "pygame._sdl2.video"],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=["unittest", "tkinter"],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Avacyn", debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=False,
    disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Avacyn")
