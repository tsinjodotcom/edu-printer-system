# -*- mode: python ; coding: utf-8 -*-
import os
import escpos

block_cipher = None

escpos_path = os.path.dirname(escpos.__file__)
escpos_data_files = []

capabilities_json = os.path.join(escpos_path, 'capabilities.json')
if os.path.exists(capabilities_json):
    escpos_data_files.append((capabilities_json, 'escpos'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('logo.png', '.'),
    ] + escpos_data_files,
    hiddenimports=[
        'flask',
        'flask_cors',
        'dotenv',
        'escpos',
        'escpos.printer',
        'escpos.escpos',
        'escpos.capabilities',
        'PIL',
        'PIL.Image',
        'usb',
        'usb.core',
        'usb.util',
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
    ],
    hookspath=['hooks'],
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
    name='EduPrinterSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='x86_64',
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

