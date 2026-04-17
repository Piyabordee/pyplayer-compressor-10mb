# -*- mode: python ; coding: utf-8 -*-
# PyPlayer Compressor - OneFile Build Spec
# ใช้สำหรับสร้าง .exe ไฟล์เดียว (รวมทุกอย่าง)

import os
import sys
block_cipher = None

CWD = os.path.dirname(os.path.realpath(sys.argv[1]))
ROOT_DIR = os.path.dirname(CWD)
ICON = os.path.join(ROOT_DIR, 'themes', 'resources', 'logo.ico')

a = Analysis([os.path.join(ROOT_DIR, 'src', 'pyplayer', '__main__.py')],
             pathex=[os.path.join(ROOT_DIR, 'src')],
             binaries=[],
             datas=[(os.path.join(ROOT_DIR, 'themes'), 'themes'),
                    (os.path.join(CWD, 'include'), 'plugins')],
             hiddenimports=[
                 'PyQt5.QtCore',
                 'PyQt5.QtGui',
                 'PyQt5.QtWidgets',
                 'vlc',
                 'certifi',
                 'colour',
                 'filetype',
                 'music_tag',
                 'tinytag',
                 'Send2Trash',
             ],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[os.path.join(CWD, 'hook.py')],
             excludes=[
                 'tkinter',
                 'matplotlib',
                 'numpy',
                 'pandas',
             ],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='PyPlayerCompressor',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,  # ไม่แสดง console window
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          icon=ICON if os.path.exists(ICON) else None)
