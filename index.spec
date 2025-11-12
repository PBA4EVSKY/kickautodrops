# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

a = Analysis(
    ['index.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='KickAutoDrops',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='app.ico'  # Раскомментируй если есть иконка
)

import shutil
from pathlib import Path

dist_dir = Path('dist')

# Копируем example_config.ini
if Path('example_config.ini').exists():
    shutil.copy2('example_config.ini', dist_dir / 'example_config.ini')
    print("Copied example_config.ini")

if Path('locales').exists():
    if (dist_dir / 'locales').exists():
        shutil.rmtree(dist_dir / 'locales')
    shutil.copytree('locales', dist_dir / 'locales')
    print("Copied locales folder")