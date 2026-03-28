# PyPlayer Repo Restructure — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the PyPlayer repository from a flat layout into a standard Python package with `src/` layout, decomposing the monolithic `main.pyw` (9,880 lines) and `widgets.py` (4,201 lines) into focused modules.

**Architecture:** Mixin pattern for MainWindow decomposition. `src/pyplayer/` package with `core/` (business logic), `gui/` (main window + mixins), `widgets/` (custom Qt widgets), `ui/` (generated UI). Each mixin has a single responsibility.

**Tech Stack:** Python 3.13+, PyQt5, python-vlc, FFmpeg/FFprobe, PyInstaller

**Spec:** `docs/superpowers/specs/2026-03-28-repo-restructure-design.md`

**Strategy:** Incremental migration — each phase produces a working application. Test after every phase. Rollback with `git revert` if anything breaks.

---

## Pre-flight: Create a feature branch

- [ ] **Step 1: Create branch**

```bash
git checkout -b refactor/repo-restructure
```

---

## Chunk 1: Package Scaffold (Phase 1)

### Task 1: Create directory structure

**Files:**
- Create: `src/pyplayer/__init__.py`
- Create: `src/pyplayer/__main__.py`
- Create: `src/pyplayer/core/__init__.py`
- Create: `src/pyplayer/gui/__init__.py`
- Create: `src/pyplayer/gui/mixins/__init__.py`
- Create: `src/pyplayer/widgets/__init__.py`
- Create: `src/pyplayer/ui/__init__.py`
- Create: `tests/__init__.py`
- Create: `pyproject.toml`

- [ ] **Step 1: Create directories**

```bash
mkdir -p src/pyplayer/core
mkdir -p src/pyplayer/gui/mixins
mkdir -p src/pyplayer/widgets
mkdir -p src/pyplayer/ui
mkdir -p tests
```

- [ ] **Step 2: Create `src/pyplayer/__init__.py`**

```python
"""PyPlayer — A powerful video player and editor built on VLC and PyQt5."""

__version__ = '0.6.0'
__author__ = 'thisismy-github'
```

- [ ] **Step 3: Create `src/pyplayer/__main__.py`**

```python
"""Entry point for `python -m pyplayer`."""
import sys
from pyplayer.app import main

if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 4: Create empty `__init__.py` files for all sub-packages**

```bash
touch src/pyplayer/core/__init__.py
touch src/pyplayer/gui/__init__.py
touch src/pyplayer/gui/mixins/__init__.py
touch src/pyplayer/widgets/__init__.py
touch src/pyplayer/ui/__init__.py
touch tests/__init__.py
```

- [ ] **Step 5: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project]
name = "pyplayer"
version = "0.6.0"
description = "Powerful video player and editor built on VLC and PyQt5"
requires-python = ">=3.13"
dependencies = [
    "PyQt5>=5.15.9",
    "python-vlc>=3.0.18122",
    "pillow==9.5.0",
    "requests>=2.31.0",
    "pywin32>=306;sys_platform=='win32'",
    "colour>=0.1.5",
    "filetype>=1.0.13",
    "tinytag>=1.9.0",
    "music-tag>=0.4.3",
    "Send2Trash>=1.8.2",
]

[project.gui-scripts]
pyplayer = "pyplayer.app:main"

[project.optional-dependencies]
build = ["pyinstaller>=5.13.0"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
pyplayer = ["py.typed"]
```

- [ ] **Step 6: Verify package structure**

```bash
# Should show all __init__.py files
find src/pyplayer -name "*.py" | sort
```

Expected: 8 `__init__.py` files listed.

- [ ] **Step 7: Install package in editable mode**

```bash
pip install -e .
```

Expected: "Successfully installed pyplayer-0.6.0" or similar.

- [ ] **Step 8: Verify import works**

```bash
python -c "import pyplayer; print(pyplayer.__version__)"
```

Expected: `0.6.0`

- [ ] **Step 9: Commit**

```bash
git add src/ pyproject.toml tests/
git commit -m "refactor: create package scaffold with src/ layout

Phase 1 of repo restructure. Creates src/pyplayer/ package structure
with empty sub-packages (core, gui, widgets, ui) and pyproject.toml.

Spec: docs/superpowers/specs/2026-03-28-repo-restructure-design.md"
```

---

## Chunk 2: Move Independent Modules (Phase 2)

These modules have minimal cross-dependencies and can be moved with simple import updates.

### Task 2: Move `constants.py`

**Files:**
- Modify: `src/pyplayer/constants.py` (new, copied from `constants.py`)
- Reference: `constants.py` (original, keep until Phase 7)

- [ ] **Step 1: Copy constants.py to package**

```bash
cp constants.py src/pyplayer/constants.py
```

- [ ] **Step 2: Update imports in `src/pyplayer/constants.py`**

Find and replace these imports:
```python
# OLD:
import util
import resource_helper

# NEW:
from pyplayer.core import ffmpeg as _ffmpeg_module  # lazy to avoid circular
from pyplayer import resource_helper
```

**IMPORTANT:** `constants.py` imports `qthelpers` at module level (for `getPopupOkCancel()` used in FFmpeg/FFprobe missing dialogs). This creates a circular dependency with `qthelpers.py` (which imports `constants`). The solution:
- Keep the `qthelpers` import as-is in the OLD `constants.py` (don't break existing code)
- In the NEW `src/pyplayer/constants.py`, defer the import:

```python
# At top of file, replace `import qthelpers` with:
def _get_qthelpers():
    """Lazy import to avoid circular dependency at module load."""
    from pyplayer.gui import helpers as qthelpers
    return qthelpers
```

Then replace all `qthelpers.getPopupOkCancel(` calls with `_get_qthelpers().getPopupOkCancel(`.

- [ ] **Step 3: Verify no syntax errors**

```bash
python -c "from pyplayer import constants; print(constants.VERSION)"
```

Expected: `pyplayer 0.6.0 beta` or similar version string.

### Task 3: Move `resource_helper.py`

- [ ] **Step 1: Copy to package**

```bash
cp resource_helper.py src/pyplayer/resource_helper.py
```

- [ ] **Step 2: Update any `import constants` to `from pyplayer import constants`**

- [ ] **Step 3: Verify import**

```bash
python -c "from pyplayer import resource_helper; print('OK')"
```

### Task 4: Move `update.py`

- [ ] **Step 1: Copy to package**

```bash
cp update.py src/pyplayer/update.py
```

- [ ] **Step 2: Update imports: `import constants` → `from pyplayer import constants`, `import util` → `from pyplayer.core import ffmpeg`, `import qtstart` → `from pyplayer import app as qtstart`**

**Note:** `update.py` line 6 imports `qtstart` to call `qtstart.exit()`. In the new structure, the `exit()` function lives in `pyplayer.gui.tray`. Update the reference accordingly:
```python
# OLD:
import qtstart
# ... later: qtstart.exit(gui)

# NEW:
from pyplayer.gui.tray import exit as app_exit
# ... later: app_exit(gui)
```

- [ ] **Step 3: Verify import**

```bash
python -c "from pyplayer import update; print('OK')"
```

### Task 5: Move `config.py`

**IMPORTANT:** `config.py` is NOT just a simple copy — it has significant import dependencies:
- `from bin.configparsebetter import ConfigParseBetterQt` → `from pyplayer.core.config_parser import ConfigParseBetterQt`
- `import constants` → `from pyplayer import constants`
- `import qthelpers` → `from pyplayer.gui import helpers as qthelpers`
- The module-level `cfg` singleton is imported by other modules at runtime

- [ ] **Step 1: Copy to package**

```bash
cp config.py src/pyplayer/config.py
```

- [ ] **Step 2: Update imports in `src/pyplayer/config.py`**

```python
# OLD:
from bin.configparsebetter import ConfigParseBetterQt
import constants
import qthelpers

# NEW:
from pyplayer.core.config_parser import ConfigParseBetterQt
from pyplayer import constants
from pyplayer.gui import helpers as qthelpers
```

- [ ] **Step 3: Verify import**

```bash
python -c "from pyplayer import config; print('OK')"
```

### Task 6: Move `bin/configparsebetter.py` → `core/config_parser.py`

- [ ] **Step 1: Copy to core package**

```bash
cp bin/configparsebetter.py src/pyplayer/core/config_parser.py
```

- [ ] **Step 2: No import changes needed — this is a standalone library**

- [ ] **Step 3: Verify import**

```bash
python -c "from pyplayer.core.config_parser import ConfigParseBetterQt; print('OK')"
```

### Task 7: Move `bin/window_*.py` → `ui/`

- [ ] **Step 1: Copy all generated UI files**

```bash
cp bin/window_pyplayer.py src/pyplayer/ui/window_pyplayer.py
cp bin/window_settings.py src/pyplayer/ui/window_settings.py
cp bin/window_about.py src/pyplayer/ui/window_about.py
cp bin/window_cat.py src/pyplayer/ui/window_cat.py
cp bin/window_text.py src/pyplayer/ui/window_text.py
cp bin/window_timestamp.py src/pyplayer/ui/window_timestamp.py
```

- [ ] **Step 2: Verify one import**

```bash
python -c "from pyplayer.ui.window_about import Ui_Dialog; print('OK')"
```

### Task 8: Move `compression.py` → `core/compression.py`

- [ ] **Step 1: Copy to core**

```bash
cp compression.py src/pyplayer/core/compression.py
```

- [ ] **Step 2: Update imports in compression.py: `import constants` → `from pyplayer import constants`**

- [ ] **Step 3: Verify import**

```bash
python -c "from pyplayer.core.compression import compress_video; print('OK')"
```

### Task 9: Commit Phase 2

- [ ] **Step 1: Stage and commit**

```bash
git add src/pyplayer/constants.py src/pyplayer/resource_helper.py src/pyplayer/update.py \
        src/pyplayer/config.py \
        src/pyplayer/core/config_parser.py src/pyplayer/core/compression.py \
        src/pyplayer/ui/window_*.py
git commit -m "refactor: move independent modules into package (Phase 2)

Moves constants, resource_helper, update, config, config_parser,
compression, and UI files into src/pyplayer/ without changing
existing entry point.

Spec: docs/superpowers/specs/2026-03-28-repo-restructure-design.md"
```

---

## Chunk 3: Split `util.py` (Phase 3)

### Task 9: Create `core/ffmpeg.py`

**Files:**
- Create: `src/pyplayer/core/ffmpeg.py`
- Reference: `util.py` lines 38-120, 498-590

- [ ] **Step 1: Create `src/pyplayer/core/ffmpeg.py`**

Extract these functions from `util.py`:
- `ffmpeg()` (line 38)
- `ffmpeg_async()` (line 51)
- `suspend_process()` (line 498)
- `kill_process()` (line 563)

```python
"""FFmpeg subprocess wrappers and process management."""
from __future__ import annotations
import os
import sys
import time
import logging
import subprocess
from traceback import format_exc

from pyplayer import constants

logger = logging.getLogger(__name__)

# [Copy ffmpeg(), ffmpeg_async(), suspend_process(), kill_process()
#  from util.py — paste verbatim, only change `constants.X` references
#  if they used bare `constants` import]
```

- [ ] **Step 2: Verify import**

```bash
python -c "from pyplayer.core.ffmpeg import ffmpeg, ffmpeg_async; print('OK')"
```

### Task 10: Create `core/file_ops.py`

**Files:**
- Create: `src/pyplayer/core/file_ops.py`
- Reference: `util.py` lines 18-36, 207-497

- [ ] **Step 1: Create file with these functions from `util.py`:**
- `sanitize()` (line 408)
- `get_unique_path()` (line 313)
- `add_path_suffix()` (line 29)
- `open_properties()` (line 369)
- `setctime()` (line 437)
- `get_from_PATH()` (line 194)
- `file_is_hidden` (lambda, line ~25)

- [ ] **Step 2: Verify import**

```bash
python -c "from pyplayer.core.file_ops import sanitize, get_unique_path; print(sanitize('test<>file.txt'))"
```

### Task 11: Create `core/media_utils.py`

**Files:**
- Create: `src/pyplayer/core/media_utils.py`
- Reference: `util.py` lines 207-312, 346-407

- [ ] **Step 1: Create file with these functions from `util.py`:**
- `get_hms()` (line 207)
- `get_PIL_Image()` (line 218)
- `get_ratio_string()` (line 303)
- `get_verbose_timestamp()` (line 346)
- `scale()` (line 429)
- `remove_dict_value()` (line 385)
- `remove_dict_values()` (line 398)

- [ ] **Step 2: Verify import**

```bash
python -c "from pyplayer.core.media_utils import get_hms; print(get_hms(3661.5))"
```

### Task 12: Commit Phase 3

```bash
git add src/pyplayer/core/ffmpeg.py src/pyplayer/core/file_ops.py src/pyplayer/core/media_utils.py
git commit -m "refactor: split util.py into core/ffmpeg, core/file_ops, core/media_utils (Phase 3)

Splits util.py (590 lines) into 3 focused modules by domain.
Original util.py preserved — imports will be updated in Phase 5.

Spec: docs/superpowers/specs/2026-03-28-repo-restructure-design.md"
```

---

## Chunk 4: Split `widgets.py` (Phase 4)

**NOTE:** `widgets.py` line 13 imports `qtstart` — used for `qtstart.exit()`. In the new structure, replace with `from pyplayer.gui.tray import exit as app_exit` or use the `helpers` module alias.

### Task 13: Create `widgets/player_backend.py`

**Files:**
- Create: `src/pyplayer/widgets/player_backend.py`
- Reference: `widgets.py` lines 57-1121

- [ ] **Step 1: Extract `PyPlayerBackend` (abstract), `PlayerVLC`, `PlayerQt`**

Copy lines 57-1121 from `widgets.py` into `src/pyplayer/widgets/player_backend.py`.

Update imports at top:
```python
"""Video player backends — VLC and Qt multimedia implementations."""
from __future__ import annotations
from pyplayer import constants
from pyplayer.core import ffmpeg
from pyplayer.core.media_utils import get_hms, get_PIL_Image, get_unique_path
# ... rest of imports from widgets.py
```

**CRITICAL:** The module-level aliases (`gui`, `app`, `cfg`, `settings`) used in `PlayerVLC` and `PlayerQt` must be handled. For now, import from `pyplayer.widgets.helpers`:

```python
from pyplayer.widgets.helpers import gui, app, cfg, settings
```

### Task 14: Create `widgets/player_widget.py`

- [ ] **Extract `QVideoPlayer` class** (lines 1363-2048 from widgets.py) → `src/pyplayer/widgets/player_widget.py`

### Task 15: Create `widgets/player_label.py`

- [ ] **Extract `QVideoPlayerLabel` class** (lines 2049-2566 from widgets.py) → `src/pyplayer/widgets/player_label.py`

### Task 16: Create remaining widget files

- [ ] **`widgets/video_slider.py`** — `QVideoSlider` (lines 2567-2968)
- [ ] **`widgets/video_list.py`** — `QVideoListItemWidget` + `QVideoList` (lines 2969-3277)
- [ ] **`widgets/overlays.py`** — `QTextOverlayPreview` + `QTextOverlay` + `QColorPickerButton` (lines 3278-3822)
- [ ] **`widgets/inputs.py`** — `QKeySequenceFlexibleEdit` + passthrough widgets + `QSpinBoxInputSignals` (lines 3823-4078)
- [ ] **`widgets/draggable.py`** — `QDraggableWindowFrame` (lines 4079-4201)

### Task 17: Create `widgets/helpers.py`

```python
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
```

### Task 18: Create `widgets/__init__.py` with re-exports

```python
"""Custom Qt widgets for PyPlayer — re-exports all public classes."""
from pyplayer.widgets.player_backend import PyPlayerBackend, PlayerVLC, PlayerQt
from pyplayer.widgets.player_widget import QVideoPlayer
from pyplayer.widgets.player_label import QVideoPlayerLabel
from pyplayer.widgets.video_slider import QVideoSlider
from pyplayer.widgets.video_list import QVideoListItemWidget, QVideoList
from pyplayer.widgets.overlays import QTextOverlayPreview, QTextOverlay, QColorPickerButton
from pyplayer.widgets.inputs import (
    QKeySequenceFlexibleEdit,
    QWidgetPassthrough,
    QDockWidgetPassthrough,
    QLineEditPassthrough,
    QSpinBoxPassthrough,
    QSpinBoxInputSignals,
)
from pyplayer.widgets.draggable import QDraggableWindowFrame
from pyplayer.widgets.helpers import (
    gui, app, cfg, settings,
    set_aliases,
    ZOOM_DYNAMIC_FIT, ZOOM_NO_SCALING, ZOOM_FIT, ZOOM_FILL,
)

__all__ = [
    'PyPlayerBackend', 'PlayerVLC', 'PlayerQt',
    'QVideoPlayer', 'QVideoPlayerLabel', 'QVideoSlider',
    'QVideoListItemWidget', 'QVideoList',
    'QTextOverlayPreview', 'QTextOverlay', 'QColorPickerButton',
    'QKeySequenceFlexibleEdit',
    'QWidgetPassthrough', 'QDockWidgetPassthrough',
    'QLineEditPassthrough', 'QSpinBoxPassthrough', 'QSpinBoxInputSignals',
    'QDraggableWindowFrame',
]
```

### Task 19: Verify widget imports

- [ ] **Run verification**

```bash
python -c "from pyplayer.widgets import QVideoPlayer, QVideoSlider; print('OK')"
```

### Task 20: Commit Phase 4

```bash
git add src/pyplayer/widgets/
git commit -m "refactor: split widgets.py into per-class modules (Phase 4)

Splits widgets.py (4,201 lines) into 9 focused files under widgets/.
widgets/__init__.py re-exports all classes for backward compatibility.
widgets/helpers.py manages runtime aliases (gui, app, cfg, settings).

Spec: docs/superpowers/specs/2026-03-28-repo-restructure-design.md"
```

---

## Chunk 5: Extract Classes from `main.pyw` (Phase 5a)

### Task 21: Create `core/edit.py`

**Files:**
- Create: `src/pyplayer/core/edit.py`
- Reference: `main.pyw` lines 548-1003

- [ ] **Step 1: Extract `Edit` class** (lines 548-1001) and `Undo` class (lines 1002-1056)

```python
"""Edit queue management — represents a pending media edit operation."""
from __future__ import annotations
import os
import logging
from traceback import format_exc

from pyplayer import constants

logger = logging.getLogger(__name__)

# [Copy Edit class and Undo class from main.pyw lines 548-1056 verbatim]
```

### Task 22: Create `core/probe.py`

**Files:**
- Create: `src/pyplayer/core/probe.py`
- Reference: `main.pyw` lines 250-447

- [ ] **Extract `probe_files()` function and related top-level functions**

Functions to extract:
- `probe_files()` (line 250)
- `close_handle()` (line 448)

Add to `core/media_utils.py`:
- `get_audio_duration()` (line 349)
- `get_image_data()` (line 364)
- `get_PIL_safe_path()` (line 376)
- `splitext_media()` (line 396)

### Task 23: Create `gui/progress.py`

**Files:**
- Create: `src/pyplayer/gui/progress.py`
- Reference: `main.pyw` lines 474-547

- [ ] **Extract `CompressProgressDialog` class**

### Task 24: Create `gui/helpers.py`

**Files:**
- Create: `src/pyplayer/gui/helpers.py`
- Reference: `qthelpers.py` (891 lines)

- [ ] **Copy `qthelpers.py` contents → `src/pyplayer/gui/helpers.py`**
- [ ] **Update imports: `import constants` → `from pyplayer import constants`, etc.**
- [ ] **Move `foreground_is_fullscreen()` and `get_font_path()` from `util.py` here** (Windows-specific, Qt-adjacent)

**NOTE:** Keep the OLD `qthelpers.py` file in place until Phase 7. Other modules (`constants.py`, `config.py`, etc.) still import from it. The old file is only safe to delete after all consumers are updated.

### Task 25: Commit Phase 5a

```bash
git add src/pyplayer/core/edit.py src/pyplayer/core/probe.py \
        src/pyplayer/core/media_utils.py \
        src/pyplayer/gui/progress.py src/pyplayer/gui/helpers.py
git commit -m "refactor: extract Edit, Undo, CompressProgressDialog, probe, helpers (Phase 5a)

Extracts standalone classes and functions from main.pyw and qthelpers.py
into their target modules. Original files preserved.

Spec: docs/superpowers/specs/2026-03-28-repo-restructure-design.md"
```

---

## Chunk 6: Create Mixin Files (Phase 5b)

This is the largest chunk. Each mixin is created by extracting methods from `GUI_Instance` in `main.pyw`.

### Task 26: Create `gui/mixins/playback.py` (20 methods)

- [ ] **Extract these methods from `GUI_Instance`:**

`pause`, `force_pause`, `stop`, `set_volume`, `set_volume_boost`, `set_mute`, `toggle_mute`, `set_playback_rate`, `set_subtitle_delay`, `set_audio_delay`, `set_fullscreen`, `toggle_maximized`, `set_track`, `cycle_track`, `restore_tracks`, `page_step`, `navigate`, `update_gif_progress`, `update_progress`, `_update_progress_slot`

```python
"""Playback controls — volume, tracks, rate, navigation."""
from __future__ import annotations
import logging
from PyQt5 import QtCore, QtGui, QtWidgets as QtW

logger = logging.getLogger(__name__)


class PlaybackMixin:
    """Methods: pause, stop, volume, tracks, rate, fullscreen, navigation."""
    # [Paste methods verbatim from GUI_Instance]
```

### Task 27: Create `gui/mixins/editing.py` (20 methods)

- [ ] **Extract:** `set_trim`, `_reset_trim_mode`, `set_trim_mode`, `set_crop_mode`, `disable_crop_mode`, `cancel_all`, `pause_all`, `add_edit`, `remove_edit`, `get_edit_with_priority`, `cycle_edit_priority`, `reset_edit_priority`, `hide_edit_progress`, `_cleanup_edit_output`, `is_safe_to_edit`, `update_time_spins`, `update_frame_spin`, `manually_update_current_time`, `_compress_with_progress`, `_handle_compression_completion`

### Task 28: Create `gui/mixins/saving.py` (12 methods)

- [ ] **Extract:** `save`, `_save`, `save_as`, `save_from_trim_button`, `concatenate`, `resize_media`, `rotate_video`, `add_audio`, `amplify_audio`, `replace_audio`, `isolate_track`, `add_text`

**Note:** `_save` alone is ~783 lines. This file will be ~1,100 lines — the largest mixin.

### Task 29: Create `gui/mixins/file_management.py` (22 methods)

- [ ] **Extract:** `open`, `_open_cleanup_slot`, `open_from_thread`, `_open_external_command_slot`, `open_folder`, `open_probe_file`, `open_recent_file`, `parse_media_file`, `search_files`, `cycle_media`, `cycle_recent_files`, `shuffle_media`, `add_subtitle_files`, `discover_subtitle_files`, `explore`, `copy`, `copy_file`, `copy_image`, `rename`, `undo_rename`, `delete`, `snapshot`

### Task 30: Create `gui/mixins/menus.py` (25 methods)

- [ ] **Extract all `*ContextMenuEvent`, `*MousePressEvent`, `*MouseReleaseEvent` methods + taskbar methods + menu refresh methods**

### Task 31: Create `gui/mixins/themes.py` (4 methods)

- [ ] **Extract:** `load_themes`, `refresh_theme_combo`, `get_theme`, `set_theme`

### Task 32: Create `gui/mixins/events.py` (10 methods)

- [ ] **Extract:** `closeEvent`, `hideEvent`, `showEvent`, `leaveEvent`, `moveEvent`, `resizeEvent`, `timerEvent`, `wheelEvent`, `keyPressEvent`, `keyReleaseEvent`

### Task 33: Create `gui/mixins/dialogs.py` (18 methods)

- [ ] **Extract:** `show_about_dialog`, `show_timestamp_dialog`, `show_trim_dialog`, `show_size_dialog`, `show_search_popup`, `show_delete_prompt`, `browse_for_directory`, `browse_for_save_file`, `browse_for_subtitle_files`, `_show_ffmpeg_missing_dialog`, `_show_duration_error_dialog`, `_show_compress_error_dialog`, `_cleanup_temp_files`, `handle_updates`, `_handle_updates`, `add_info_actions`, `convert_snapshot_to_jpeg`, `_show_color_picker`

### Task 34: Create `gui/mixins/ui_state.py` (27 methods)

- [ ] **Extract all visibility setters, refresh methods, snap/mark methods, getter helpers, `marquee`, `_log_on_statusbar_slot`**

### Task 35: Commit Phase 5b

```bash
git add src/pyplayer/gui/mixins/
git commit -m "refactor: create all 8 mixin files from GUI_Instance (Phase 5b)

Creates PlaybackMixin (20), EditingMixin (20), SavingMixin (12),
FileManagementMixin (22), MenuMixin (25), ThemeMixin (4),
EventMixin (10), DialogMixin (18), UIStateMixin (27) — 9 mixins total.

Spec: docs/superpowers/specs/2026-03-28-repo-restructure-design.md"
```

---

## Chunk 7: Wire Up MainWindow (Phase 5c)

### Task 36: Create `gui/main_window.py`

**Files:**
- Create: `src/pyplayer/gui/main_window.py`

```python
"""Main application window — composed from functional mixins."""
from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets as QtW

from pyplayer.gui.mixins.playback import PlaybackMixin
from pyplayer.gui.mixins.editing import EditingMixin
from pyplayer.gui.mixins.saving import SavingMixin
from pyplayer.gui.mixins.file_management import FileManagementMixin
from pyplayer.gui.mixins.menus import MenuMixin
from pyplayer.gui.mixins.themes import ThemeMixin
from pyplayer.gui.mixins.events import EventMixin
from pyplayer.gui.mixins.dialogs import DialogMixin
from pyplayer.gui.mixins.ui_state import UIStateMixin
from pyplayer.ui.window_pyplayer import Ui_MainWindow


class MainWindow(
    PlaybackMixin,
    EditingMixin,
    SavingMixin,
    FileManagementMixin,
    MenuMixin,
    ThemeMixin,
    EventMixin,
    DialogMixin,
    UIStateMixin,
    Ui_MainWindow,
    QtW.QMainWindow,
):
    """Main application window — composed from functional mixins."""

    def __init__(self, app, *args, **kwargs):
        # [Copy __init__ from GUI_Instance — lines ~1058-1149]
        ...

    def setup(self):
        # [Copy setup from GUI_Instance — lines ~1150-1378]
        ...

    def set_player(self, backend, _error=False):
        # [Copy set_player from GUI_Instance — lines ~2338-2422]
        ...

    def restart(self):
        # [Copy restart from GUI_Instance — lines ~3876-3942]
        ...

    def restore(self, frame, was_paused=None):
        # [Copy restore from GUI_Instance — lines ~3943-3967]
        ...

    def event(self, event):
        # [Copy event override from GUI_Instance — lines ~1431-1439]
        ...

    def external_command_interface_thread(self):
        # [Copy from GUI_Instance — lines ~1379-1430]
        ...
```

### Task 37: Create `gui/signals.py`

- [ ] **Extract `connect_widget_signals()` from `qtstart.py`** (lines 282-491)

### Task 38: Create `gui/shortcuts.py`

- [ ] **Extract `connect_shortcuts()` from `qtstart.py`** (lines 217-279)

### Task 39: Create `gui/tray.py`

- [ ] **Extract `exit()` and `get_tray_icon()` from `qtstart.py`** (lines 75-135)

### Task 40: Create `app.py`

**Files:**
- Create: `src/pyplayer/app.py`
- Reference: `qtstart.py` lines 1-74, 136-216, `main.pyw` lines 1-248

```python
"""Application startup — QApplication creation, argument parsing, main()."""
from __future__ import annotations

import os
import sys
import logging
import argparse
from traceback import format_exc

from PyQt5 import QtGui, QtWidgets as QtW

from pyplayer import constants
from pyplayer.gui.main_window import MainWindow
from pyplayer.gui.signals import connect_widget_signals
from pyplayer.gui.shortcuts import connect_shortcuts
from pyplayer.gui.tray import exit as app_exit, get_tray_icon
from pyplayer.widgets.helpers import set_aliases
from pyplayer import config


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('file', nargs='?')
    parser.add_argument('--exit', action='store_true')
    parser.add_argument('--play-and-exit', action='store_true')
    parser.add_argument('--minimized', action='store_true')
    parser.add_argument('-v', '--vlc', default='--gain=2.0')
    parser.add_argument('-d', '--debug', action='store_true')
    return parser.parse_args()


def after_show_setup(gui):
    """Post-show initialization — recent files, tray icon, hotkeys."""
    # [Copy from qtstart.py after_show_setup — lines 141-214]
    ...


def main():
    """Application entry point."""
    args = parse_args()
    if args.exit:
        sys.exit(100)

    # Setup logging
    # [Copy from qtstart.py lines 38-68]

    # Create application
    app = QtW.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Create main window
    gui = MainWindow(app)
    gui.show()

    # Post-show setup
    after_show_setup(gui)

    # Run event loop
    constants.APP_RUNNING = True
    try:
        return app.exec_()
    except:
        logging.critical(f'(!) APP FAILED: {format_exc()}')
    finally:
        try:
            app_exit(gui)
        except:
            pass
```

### Task 41: Create backward-compatible `pyplayer.pyw` stub

**Files:**
- Create: `pyplayer.pyw` (at repo root)

```python
"""Backward-compatible entry point — delegates to pyplayer package."""
import sys
import os

# Add src/ to path so the package can be found without pip install
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from pyplayer.app import main
sys.exit(main())
```

### Task 42: TEST — Verify application launches

- [ ] **Run the application via the old entry point**

```bash
python main.pyw
```

Expected: Application launches, video playback works.

- [ ] **Run via the new entry point**

```bash
python -m pyplayer
```

Expected: Application launches identically.

- [ ] **Run via backward-compatible stub**

```bash
python pyplayer.pyw
```

Expected: Application launches identically.

- [ ] **Test checklist:**
- [ ] Video playback (open a video file)
- [ ] Pause/play/stop
- [ ] Volume control
- [ ] Keyboard shortcuts (space to pause, arrows to navigate)
- [ ] Theme switching
- [ ] Trim mode
- [ ] Save/compress
- [ ] System tray (if enabled)

### Task 43: Commit Phase 5c

```bash
git add src/pyplayer/gui/main_window.py src/pyplayer/gui/signals.py \
        src/pyplayer/gui/shortcuts.py src/pyplayer/gui/tray.py \
        src/pyplayer/app.py pyplayer.pyw
git commit -m "refactor: create MainWindow, app.py, signals, shortcuts, tray (Phase 5c)

Wires up MainWindow class from mixins, creates app.py startup sequence,
and adds backward-compatible pyplayer.pyw stub at repo root.

Spec: docs/superpowers/specs/2026-03-28-repo-restructure-design.md"
```

---

## Chunk 8: Restructure Packaging & Assets (Phase 6)

### Task 44: Move `executable/` → `packaging/`

- [ ] **Step 1: Copy directory**

```bash
cp -r executable packaging
```

- [ ] **Step 2: Update `packaging/main.spec` — change entry point and paths**

```python
# OLD:
a = Analysis(['main.pyw'], ...)

# NEW:
a = Analysis(['src/pyplayer/__main__.py'], ...)
pathex=['src/'],  # Add this to find package modules
```

- [ ] **Step 3: Update `packaging/hook.py` — update module paths**

Replace references to `main.pyw` with `src/pyplayer/__main__.py`.

- [ ] **Step 4: Update `packaging/updater.spec` — update path to `bin/updater.py`**

```python
# OLD:
a = Analysis([os.path.join(ROOT_DIR, 'bin', 'updater.py')], ...)

# NEW (keep bin/updater.py in place until Phase 7):
a = Analysis([os.path.join(ROOT_DIR, 'bin', 'updater.py')], ...)
# Note: updater.py stays in bin/ until cleanup phase
```

- [ ] **Step 5: Update `build_installer.bat` at repo root — replace all `executable` references with `packaging`**

```
# OLD:
cd /d "%PROJECT_DIR%\executable"
"%INNO_COMPILER%" "%PROJECT_DIR%\executable\installer.iss"
# ... and all other references to executable\

# NEW:
cd /d "%PROJECT_DIR%\packaging"
"%INNO_COMPILER%" "%PROJECT_DIR%\packaging\installer.iss"
# ... and all other references to packaging\
```

### Task 45: Move `.ui` files → `ui_sources/`

```bash
mkdir -p ui_sources
cp bin/*.ui ui_sources/
```

### Task 46: Move assets

**NOTE:** Do NOT move `themes/resources/` — it is referenced at runtime by `resource_helper.py`, `constants.py`, and all PyInstaller spec files. Only move design files.

```bash
mkdir -p assets/logos
cp bin/*.pdn assets/logos/
```

### Task 47: Create `scripts/convert_ui.py`

**Files:**
- Create: `scripts/convert_ui.py`

```python
"""Converts all .ui files to .py files using pyuic5.
Run after editing .ui files in ui_sources/."""
import os
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
UI_DIR = os.path.join(ROOT, 'ui_sources')
OUT_DIR = os.path.join(ROOT, 'src', 'pyplayer', 'ui')

for ui_file in glob.glob(os.path.join(UI_DIR, '*.ui')):
    basename = os.path.basename(ui_file)
    py_file = os.path.join(OUT_DIR, basename.replace('.ui', '.py'))
    os.system(f'pyuic5 -x "{ui_file}" -o "{py_file}"')
    print(f'Converted: {basename} → src/pyplayer/ui/{basename.replace(".ui", ".py")}')
```

### Task 48: Update `.gitignore`

Append these entries:
```
# Build outputs
packaging/build/
packaging/compiling/
packaging/installer_output/

# Python
__pycache__/
*.pyc
dist/
*.egg-info/

# IDE
.vscode/
.idea/

# Runtime
pyplayer.log
config.ini

# Old build dirs (kept during transition)
executable/build/
executable/compiling/
executable/installer_output/
```

### Task 49: Commit Phase 6

```bash
git add packaging/ ui_sources/ assets/ scripts/ .gitignore
git commit -m "refactor: restructure packaging, assets, and build configs (Phase 6)

Moves executable/ → packaging/, .ui files → ui_sources/,
assets → assets/, creates scripts/convert_ui.py,
updates .gitignore for new directory structure.

Spec: docs/superpowers/specs/2026-03-28-repo-restructure-design.md"
```

---

## Chunk 9: Cleanup & Final Verification (Phase 7)

### Task 50: Delete old files

> **WARNING:** Only do this after Task 42 passes ALL tests.

- [ ] **Step 1: Delete root-level files that have been moved**

```bash
rm main.pyw          # Replaced by src/pyplayer/
rm compression.py    # Replaced by src/pyplayer/core/compression.py
rm util.py           # Replaced by src/pyplayer/core/*.py
rm qthelpers.py      # Replaced by src/pyplayer/gui/helpers.py
rm qtstart.py        # Replaced by src/pyplayer/app.py + gui/*.py
rm widgets.py        # Replaced by src/pyplayer/widgets/*.py
rm convert_ui_to_py.py  # Replaced by scripts/convert_ui.py
```

- [ ] **Step 2: Delete `bin/` generated files (keep .ui sources until moved)**

```bash
rm bin/window_*.py
rm bin/configparsebetter.py
# Keep bin/updater.py — standalone updater, referenced by packaging/updater.spec
# Keep bin/*.ui — already copied to ui_sources/, can delete after verification
```

- [ ] **Step 3: Delete `executable/` (replaced by `packaging/`)**

```bash
rm -rf executable/
```

### Task 51: Move `bin/updater.py` into package

```bash
mv bin/updater.py src/pyplayer/updater_cli.py
```

Update `packaging/updater.spec` to reference new path:
```python
a = Analysis([os.path.join(ROOT_DIR, 'src', 'pyplayer', 'updater_cli.py')], ...)
```

### Task 52: Update documentation

- [ ] **Update `AGENTS.md`** — Update Repository Structure section with new layout
- [ ] **Update `CLAUDE.md`** — Update to reflect new import paths
- [ ] **Update `README.md`** — Update installation instructions to use `pip install -e .`

### Task 53: Final verification — full test suite

- [ ] **Test 1: Launch via package**

```bash
python -m pyplayer
```

- [ ] **Test 2: Launch via stub**

```bash
python pyplayer.pyw
```

- [ ] **Test 3: Video playback** — Open and play MP4, MKV, AVI files
- [ ] **Test 4: Audio editing** — Trim, amplify, replace audio
- [ ] **Test 5: Video editing** — Crop, rotate, concatenate, add text
- [ ] **Test 6: Save/Compress** — Save trimmed video, auto-compress to 10MB
- [ ] **Test 7: Theme switching** — Switch between all 5 themes
- [ ] **Test 8: Configuration** — Change settings, restart, verify persistence
- [ ] **Test 9: Keyboard shortcuts** — Space, arrows, volume keys
- [ ] **Test 10: System tray** — Minimize to tray, restore
- [ ] **Test 11: Drag and drop** — Drag files onto window
- [ ] **Test 12: PyInstaller build**

```bash
cd packaging
python build.py
```

Expected: Working .exe produced.

- [ ] **Test 13: Line count verification**

```bash
find src/pyplayer -name "*.py" -exec wc -l {} + | sort -rn | head -20
```

Expected: No file exceeds 800 lines (saving.py may be ~1,100 — acceptable for now).

### Task 54: Final commit

```bash
git add -A
git commit -m "refactor: complete repo restructure — cleanup old files, update docs (Phase 7)

Removes old flat-layout files, updates all documentation,
moves updater.py into package. Full application verified working.

Spec: docs/superpowers/specs/2026-03-28-repo-restructure-design.md"
```

---

## File Count Summary

| Directory | Files Created | Purpose |
|-----------|--------------|---------|
| `src/pyplayer/` | 6 | Package root (__init__, __main__, app, config, constants, resource_helper, update) |
| `src/pyplayer/core/` | 7 | Business logic (edit, ffmpeg, file_ops, media_utils, compression, config_parser, probe) |
| `src/pyplayer/gui/` | 6 | Main window + helpers (main_window, helpers, progress, signals, shortcuts, tray) |
| `src/pyplayer/gui/mixins/` | 9 | Mixin files (playback, editing, saving, file_management, menus, themes, events, dialogs, ui_state) |
| `src/pyplayer/widgets/` | 10 | Custom widgets (player_backend, player_widget, player_label, video_slider, video_list, overlays, inputs, draggable, helpers, __init__) |
| `src/pyplayer/ui/` | 7 | Generated UI files (6 windows + __init__) |
| `packaging/` | moved | Build configs |
| `ui_sources/` | 6 | .ui source files |
| `assets/` | moved | Icons, logos |
| `scripts/` | 1 | convert_ui.py |
| `tests/` | 1 | __init__.py (placeholder) |
| **Total** | **~53 new files** | |

---

## Risk Checklist

Before starting implementation, verify:
- [ ] Current application runs without errors from `python main.pyw`
- [ ] Git working tree is clean (no uncommitted changes)
- [ ] Feature branch created (`refactor/repo-restructure`)
- [ ] Spec document reviewed and approved
- [ ] All dependencies in `requirements.txt` are installable
