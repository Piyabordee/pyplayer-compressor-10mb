# -*- mode: python ; coding: utf-8 -*-
#
# PyPlayer Compressor - PyInstaller Spec File
# Compatible with PyInstaller 6.x+
#

import os
import sys

block_cipher = None

# Get paths - PyInstaller 6.x runs spec from current directory
SPEC_DIR = os.path.abspath(os.getcwd())
CWD = SPEC_DIR
ROOT_DIR = os.path.dirname(SPEC_DIR)
VERSION_FILE = os.path.join(CWD, 'version_info_main.txt')
ICON = os.path.join(ROOT_DIR, 'themes', 'resources', 'logo.ico')


a = Analysis(
    [os.path.join(ROOT_DIR, 'src', 'pyplayer', '__main__.py')],
    pathex=[ROOT_DIR, os.path.join(ROOT_DIR, 'src')],
    binaries=[
        # VLC binaries
        (os.path.join(CWD, 'include', 'vlc-windows', 'libvlc.dll'), 'plugins/vlc'),
        (os.path.join(CWD, 'include', 'vlc-windows', 'libvlccore.dll'), 'plugins/vlc'),
        # FFmpeg binaries
        (os.path.join(CWD, 'include', 'ffmpeg-windows', 'ffmpeg.exe'), 'plugins/ffmpeg'),
        (os.path.join(CWD, 'include', 'ffmpeg-windows', 'ffprobe.exe'), 'plugins/ffmpeg'),
    ],
    datas=[
        (os.path.join(ROOT_DIR, 'themes'), 'themes'),
        (os.path.join(CWD, 'include', 'vlc-windows', 'plugins'), 'plugins/vlc/plugins'),
        (os.path.join(CWD, 'include', 'ffmpeg-windows'), 'plugins/ffmpeg'),
    ],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'vlc',
        'certifi',
        'certifi.core',
        'colour',
        'filetype',
        'music_tag',
        'tinytag',
        'Send2Trash',
        'win32com',
        'pywintypes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(CWD, 'hook.py')],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts, 
          [],
          exclude_binaries=True,
          name='pyplayer',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          version=VERSION_FILE if os.path.exists(VERSION_FILE) else None,
          icon=ICON if os.path.exists(ICON) else None)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas, 
               strip=False,
               upx=True,
               upx_exclude=[],
               name='release')
