# -*- mode: python ; coding: utf-8 -*-

import pathlib
import re

APP_NAME = "PDF Digitizer Web"
BUNDLE_ID = "com.westlakeu.pdfdigitizer.web"

_version_match = re.search(
    r'__version__\s*=\s*"([^"]+)"',
    pathlib.Path("pdf_digitizer/__init__.py").read_text(encoding="utf-8"),
)
VERSION = _version_match.group(1) if _version_match else "1.0.0"

a = Analysis(
    ["main_webview.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("pdf_digitizer/webview/web", "pdf_digitizer/webview/web"),
    ],
    hiddenimports=[
        "webview.platforms.cocoa",
        "objc",
        "Foundation",
        "AppKit",
        "WebKit",
        "Quartz",
        "UniformTypeIdentifiers",
        "Security",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "PySide6",
        "pytest",
        "numpy",
        "torch",
        "matplotlib",
        "scipy",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.icns",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

app = BUNDLE(
    coll,
    name=f"{APP_NAME}.app",
    icon="assets/icon.icns",
    bundle_identifier=BUNDLE_ID,
    version=VERSION,
    info_plist={
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "LSApplicationCategoryType": "public.app-category.productivity",
    },
)
