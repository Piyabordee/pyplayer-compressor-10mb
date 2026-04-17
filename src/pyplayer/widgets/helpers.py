"""Runtime aliases and constants for widget modules.

These are set by app.py after MainWindow creation.
Until then, all aliases are None.
"""
from __future__ import annotations

# Runtime aliases — populated by set_aliases()
gui = None
app = None
cfg = None
settings = None

# Zoom constants (from widgets.py lines 48-51)
ZOOM_DYNAMIC_FIT = 0
ZOOM_NO_SCALING  = 1
ZOOM_FIT         = 2
ZOOM_FILL        = 3


def set_aliases(gui_instance, app_instance, cfg_instance, settings_instance):
    """Populate runtime aliases. Called from app.py after MainWindow creation."""
    global gui, app, cfg, settings
    gui = gui_instance
    app = app_instance
    cfg = cfg_instance
    settings = settings_instance
