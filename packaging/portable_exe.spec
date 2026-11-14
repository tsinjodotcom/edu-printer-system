# -*- mode: python ; coding: utf-8 -*-
import os
import escpos
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Resolve everything from the project root so the build works from any cwd.
ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))
SRC = os.path.join(ROOT, 'src')

# pkg_resources.extern.<pkg> is synthesized at runtime by a VendorImporter and
# does not exist on disk, so static analysis cannot follow it. Collect the real
# pkg_resources._vendor.* modules the import ultimately resolves to.
pkg_resources_hiddenimports = collect_submodules('pkg_resources')

escpos_path = os.path.dirname(escpos.__file__)
escpos_data_files = []

capabilities_json = os.path.join(escpos_path, 'capabilities.json')
if os.path.exists(capabilities_json):
    escpos_data_files.append((capabilities_json, 'escpos'))

a = Analysis(
    [os.path.join(SRC, 'main.py')],
    pathex=[SRC],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'assets', 'logo.png'), '.'),
    ] + escpos_data_files,
    hiddenimports=[
        'pkg_resources',
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
        'usb.backend.libusb0',
        'usb.backend.libusb1',
        'usb.backend.openusb',
        'libusb_package',
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
    ] + pkg_resources_hiddenimports,
    hookspath=[os.path.join(SPECPATH, 'hooks')],
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

