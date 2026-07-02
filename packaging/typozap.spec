# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

root = Path(SPECPATH).parent
runtime_files = [path for path in (root / "runtime").glob("*") if path.is_file()]
binaries = [(str(path), "runtime") for path in runtime_files]
hiddenimports = []
if sys.platform == "win32":
    hiddenimports += ["pynput.keyboard._win32", "pynput.mouse._win32"]
elif sys.platform == "darwin":
    hiddenimports += ["pynput.keyboard._darwin", "pynput.mouse._darwin"]

a = Analysis(
    [str(root / "src" / "typozap" / "__main__.py")],
    pathex=[str(root / "src")],
    binaries=binaries,
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="TypoZap",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
    )
    collected = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="TypoZap")
    app = BUNDLE(
        collected,
        name="TypoZap.app",
        icon=str(root / "icon.icns") if (root / "icon.icns").exists() else None,
        bundle_identifier="app.typozap.desktop",
        info_plist={"LSUIElement": True, "NSHighResolutionCapable": True},
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="TypoZap",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=sys.platform == "win32",
        console=False,
        icon=str(root / "icon.ico") if sys.platform == "win32" else None,
    )
