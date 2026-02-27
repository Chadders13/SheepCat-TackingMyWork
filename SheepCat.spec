# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for SheepCat – Tracking My Work
#
# Build command (run from the repo root):
#   pyinstaller SheepCat.spec
#
# Output is placed in  dist/SheepCat/  (directory mode, not a single file).
# Directory mode avoids the slow self-extraction that --onefile performs on
# every launch and produces a deployment folder ready for the Inno Setup
# installer script.

import os

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
src_dir = os.path.join(SPECPATH, 'src')

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [os.path.join(src_dir, 'MyWorkTracker.py')],
    pathex=[src_dir],
    binaries=[],
    datas=[
        # Bundle the default settings JSON so the app can find it on first run
        (os.path.join(src_dir, 'sheepcat_settings.json'), '.'),
    ],
    hiddenimports=[
        # Ensure all local modules are included even if not auto-detected
        'csv_data_repository',
        'data_repository',
        'review_log_page',
        'settings_manager',
        'settings_page',
        'todo_repository',
        'todo_page',
        'theme',
        'ollama_client',
        'onboarding',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# ---------------------------------------------------------------------------
# PYZ archive
# ---------------------------------------------------------------------------
pyz = PYZ(a.pure)

# ---------------------------------------------------------------------------
# EXE (inside the dist directory, not a self-contained single file)
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # required for COLLECT (directory mode)
    name='SheepCat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # no console window — pure GUI app
    icon=None,               # replace with path to .ico file when available
)

# ---------------------------------------------------------------------------
# COLLECT – assemble the final deployment directory
# ---------------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SheepCat',         # output folder: dist/SheepCat/
)
