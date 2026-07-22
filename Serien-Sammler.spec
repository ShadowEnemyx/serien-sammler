# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path


version_values = {}
exec((Path(SPECPATH) / "series_collector" / "__init__.py").read_text(encoding="utf-8"), version_values)
app_version = version_values["__version__"]


analysis = Analysis(
    ["series_collector/gui.py"],
    pathex=[SPECPATH],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
python_archive = PYZ(analysis.pure)

if sys.platform == "darwin":
    executable = EXE(
        python_archive,
        analysis.scripts,
        [],
        exclude_binaries=True,
        name="Serien-Sammler",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    collected = COLLECT(
        executable,
        analysis.binaries,
        analysis.datas,
        strip=False,
        upx=True,
        name="Serien-Sammler",
    )
    app = BUNDLE(
        collected,
        name="Serien-Sammler.app",
        bundle_identifier="com.shadowenemy.seriensammler",
        info_plist={
            "CFBundleDisplayName": "Serien-Sammler",
            "CFBundleShortVersionString": app_version,
            "NSHighResolutionCapable": True,
        },
    )
else:
    executable = EXE(
        python_archive,
        analysis.scripts,
        analysis.binaries,
        analysis.datas,
        [],
        name="Serien-Sammler",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
    )
