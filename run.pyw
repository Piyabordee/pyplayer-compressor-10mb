"""Backward-compatible entry point - delegates to pyplayer package."""
from __future__ import annotations

import sys
import os

# Set VLC path for development mode (not needed when compiled - hook.py handles it)
# This allows running from source without needing VLC in PATH
CWD = os.path.dirname(os.path.abspath(__file__))
VLC_PATH = os.path.join(CWD, 'executable', 'include', 'vlc-windows')
LIB_PATH = os.path.join(VLC_PATH, 'libvlc.dll')
MODULE_PATH = os.path.join(VLC_PATH, 'plugins')
if 'PYTHON_VLC_LIB_PATH' not in os.environ and os.path.exists(LIB_PATH):
    os.environ['PYTHON_VLC_LIB_PATH'] = LIB_PATH
if 'PYTHON_VLC_MODULE_PATH' not in os.environ and os.path.exists(MODULE_PATH):
    os.environ['PYTHON_VLC_MODULE_PATH'] = MODULE_PATH

# Add src/ to path so the package can be found without pip install
sys.path.insert(0, os.path.join(CWD, 'src'))

from pyplayer.app import main
sys.exit(main())
