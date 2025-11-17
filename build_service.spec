# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['service.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('logo.png', '.'),
    ],
    hiddenimports=[
        'win32timezone',
        'win32service',
        'win32serviceutil',
        'servicemanager',
        'win32event',
        'win32api',
        'win32con',
        'win32pipe',
        'win32process',
    ],
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
    name='EduPrinterService',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='x86_64',
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

