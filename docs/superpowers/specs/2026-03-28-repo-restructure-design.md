# PyPlayer Repo Restructure — Design Spec

> **Date:** 2026-03-28
> **Status:** Draft
> **Scope:** Full repository restructure with standard Python package layout

---

## Problem Statement

`main.pyw` is 9,880 lines / 531KB containing a single `GUI_Instance` class with 164 methods — a classic "God Class" anti-pattern. `widgets.py` adds another 4,201 lines with 15+ classes. The `bin/` folder mixes generated UI code with libraries and build artifacts. The repository lacks a standard Python package structure, making it hard for both humans and AI agents to navigate and maintain.

## Goals

1. **Standard Python package structure** — `src/` layout following PyPA packaging guidelines
2. **Decompose God Class** — Split `GUI_Instance` into focused, maintainable modules
3. **Clean file naming** — Follow Python conventions (lowercase, no spaces)
4. **Preserve functionality** — All existing features must work identically after restructure
5. **AI-friendly** — Each file < 500 lines ideally, with clear single-responsibility

## Non-Goals

- Adding new features
- Changing public API or user-facing behavior
- Rewriting existing logic
- Adding tests (separate future effort)

---

## Target Directory Structure

```
pyplayer/                              # repo root
├── src/
│   └── pyplayer/                      # main package
│       ├── __init__.py                # version, metadata
│       ├── __main__.py                # python -m pyplayer entry point
│       ├── app.py                     # QApplication creation, startup sequence
│       ├── config.py                  # loadConfig(), saveConfig()
│       ├── constants.py               # global constants, paths, FFmpeg verification
│       ├── resource_helper.py         # PyInstaller resource helper
│       ├── update.py                  # update checking/downloading
│       │
│       ├── core/                      # business logic (minimal Qt dependency)
│       │   ├── __init__.py
│       │   ├── config_parser.py       # ConfigParseBetterQt class (from bin/configparsebetter.py)
│       │   ├── edit.py                # Edit class, Undo class
│       │   ├── ffmpeg.py              # ffmpeg(), ffmpeg_async(), kill_process(), suspend_process()
│       │   ├── compression.py         # compress_video() with bitrate calculation
│       │   ├── file_ops.py            # sanitize(), get_unique_path(), open_properties(), setctime()
│       │   └── media_utils.py         # get_PIL_Image(), get_hms(), get_ratio_string(), etc.
│       │
│       ├── gui/                       # main window + mixins
│       │   ├── __init__.py
│       │   ├── main_window.py         # MainWindow class (__init__, setup, restart, restore)
│       │   ├── mixins/
│       │   │   ├── __init__.py
│       │   │   ├── playback.py        # play, pause, stop, volume, tracks, rate, fullscreen
│       │   │   ├── editing.py         # trim, crop, save, compress, concat, rotate, audio edits
│       │   │   ├── file_management.py # open, folder, recent, search, subtitles, rename, delete
│       │   │   ├── menus.py           # context menus, taskbar controls, refresh_* methods
│       │   │   ├── themes.py          # load_themes, set_theme, refresh_theme_combo
│       │   │   ├── events.py          # Qt event handlers (key, mouse, resize, etc.)
│       │   │   └── dialogs.py         # about, settings, timestamps, search, delete prompt
│       │   ├── signals.py             # connect_widget_signals() (~200 lines of signal wiring)
│       │   ├── shortcuts.py           # connect_shortcuts() (hotkey setup)
│       │   ├── tray.py                # exit(), get_tray_icon()
│       │   ├── helpers.py             # qthelpers.py functions (getPopup, etc.)
│       │   └── progress.py            # CompressProgressDialog class
│       │
│       ├── widgets/                   # custom Qt widgets (from widgets.py)
│       │   ├── __init__.py            # re-exports all public classes
│       │   ├── video_player.py        # PyPlayerBackend, PlayerVLC, PlayerQt, QVideoPlayer, QVideoPlayerLabel
│       │   ├── video_slider.py        # QVideoSlider
│       │   ├── video_list.py          # QVideoListItemWidget, QVideoList
│       │   ├── overlays.py            # QTextOverlayPreview, QTextOverlay, QColorPickerButton
│       │   ├── inputs.py              # QKeySequenceFlexibleEdit, passthrough widgets
│       │   ├── draggable.py           # QDraggableWindowFrame
│       │   └── helpers.py             # widget utility functions
│       │
│       └── ui/                        # generated UI files (from bin/)
│           ├── __init__.py
│           ├── window_pyplayer.py
│           ├── window_settings.py
│           ├── window_about.py
│           ├── window_cat.py
│           ├── window_text.py
│           └── window_timestamp.py
│
├── ui_sources/                        # .ui files for Qt Designer (from bin/)
│   ├── window_pyplayer.ui
│   ├── window_settings.ui
│   ├── window_about.ui
│   ├── window_cat.ui
│   ├── window_text.ui
│   └── window_timestamp.ui
│
├── assets/                            # static resources (from bin/ + themes/resources/)
│   ├── icons/
│   └── logos/
│
├── themes/                            # theme files (stays at root level)
│   ├── midnight.txt
│   ├── blueberry_breeze.txt
│   └── ...
│
├── packaging/                         # build configs (from executable/) — NOT "build/" to avoid setuptools conflict
│   ├── build.py
│   ├── hook.py
│   ├── main.spec
│   ├── main_onefile.spec
│   ├── updater.spec
│   ├── exclude.txt
│   ├── installer.iss
│   └── version_info/
│       ├── main.txt
│       └── updater.txt
│
├── scripts/                           # development scripts
│   └── convert_ui.py                  # convert_ui_to_py.py (moved + renamed)
│
├── tests/                             # future test directory
│   └── __init__.py
│
├── pyproject.toml                     # standard Python project config
├── requirements.txt                   # kept for compatibility
├── build_installer.bat
├── README.md
├── LICENSE
├── CLAUDE.md
└── AGENTS.md
```

---

## Architecture: Mixin Pattern for MainWindow

The core architectural decision is decomposing the 164-method `GUI_Instance` class using Python's multiple inheritance (Mixin pattern).

### Why Mixins

1. **Minimal code changes** — Methods use `self` extensively (accessing widgets, player, etc.). Mixins preserve this without refactoring every `self.xxx` reference.
2. **Single class at runtime** — `MainWindow(PlaybackMixin, EditingMixin, ..., QMainWindow)` behaves identically to the original monolithic class.
3. **Clear file boundaries** — Each mixin file has a single responsibility, making it easy for AI agents and developers to locate code.

### Composition

```python
# gui/main_window.py
from .mixins.playback import PlaybackMixin
from .mixins.editing import EditingMixin
from .mixins.file_management import FileManagementMixin
from .mixins.menus import MenuMixin
from .mixins.themes import ThemeMixin
from .mixins.events import EventMixin
from .mixins.dialogs import DialogMixin

class MainWindow(
    PlaybackMixin,
    EditingMixin,
    FileManagementMixin,
    MenuMixin,
    ThemeMixin,
    EventMixin,
    DialogMixin,
    Ui_MainWindow,
    QtW.QMainWindow
):
    """Main application window — composed from functional mixins."""

    def __init__(self, app, *args, **kwargs): ...
    def setup(self): ...
    def restart(self): ...
    def restore(self, frame, was_paused): ...
    def external_command_interface_thread(self): ...
```

### Method Distribution — Complete Mapping (164 methods)

**Note:** Methods 1-4 belong to `CompressProgressDialog`, 5-15 to `Edit`/`Undo` classes (extracted to `core/edit.py` and `gui/progress.py`). Below maps all 164 `GUI_Instance` methods.

| Module | Count | Methods |
|--------|-------|---------|
| **`main_window.py`** | 7 | `__init__`, `setup`, `restart`, `restore`, `external_command_interface_thread`, `event`, `set_player` |
| **`mixins/playback.py`** | 20 | `pause`, `force_pause`, `stop`, `set_volume`, `set_volume_boost`, `set_mute`, `toggle_mute`, `set_playback_rate`, `set_subtitle_delay`, `set_audio_delay`, `set_fullscreen`, `toggle_maximized`, `set_track`, `cycle_track`, `restore_tracks`, `page_step`, `navigate`, `update_gif_progress`, `update_progress`, `_update_progress_slot` |
| **`mixins/editing.py`** | 32 | `set_trim`, `_reset_trim_mode`, `save_from_trim_button`, `set_trim_mode`, `save`, `_save`, `save_as`, `concatenate`, `resize_media`, `rotate_video`, `add_audio`, `amplify_audio`, `replace_audio`, `isolate_track`, `add_text`, `set_crop_mode`, `disable_crop_mode`, `cancel_all`, `pause_all`, `add_edit`, `remove_edit`, `get_edit_with_priority`, `cycle_edit_priority`, `reset_edit_priority`, `hide_edit_progress`, `update_time_spins`, `update_frame_spin`, `manually_update_current_time`, `_cleanup_edit_output`, `is_safe_to_edit`, `_compress_with_progress`, `_handle_compression_completion` |
| **`mixins/file_management.py`** | 22 | `open`, `_open_cleanup_slot`, `open_from_thread`, `_open_external_command_slot`, `open_folder`, `open_probe_file`, `open_recent_file`, `parse_media_file`, `search_files`, `cycle_media`, `cycle_recent_files`, `shuffle_media`, `add_subtitle_files`, `discover_subtitle_files`, `explore`, `copy`, `copy_file`, `copy_image`, `rename`, `undo_rename`, `delete`, `snapshot` |
| **`mixins/menus.py`** | 25 | `dockControlsResizeEvent`, `frameProgressContextMenuEvent`, `trimButtonContextMenuEvent`, `buttonMediaLocationContextMenuEvent`, `buttonMarkDeletedContextMenuEvent`, `buttonSnapshotContextMenuEvent`, `buttonAutoplayContextMenuEvent`, `cycleButtonContextMenuEvent`, `menuRecentContextMenuEvent`, `frameVolumeContextMenuEvent`, `frameVolumeMousePressEvent`, `buttonPauseContextMenuEvent`, `buttonPauseMousePressEvent`, `editProgressBarContextMenuEvent`, `editProgressBarMouseReleaseEvent`, `contextMenuEvent`, `create_taskbar_controls`, `enable_taskbar_controls`, `refresh_taskbar`, `handle_cycle_buttons`, `handle_snapshot_button`, `setup_trim_button_custom_handler`, `refresh_track_menu`, `refresh_recent_menu`, `refresh_undo_menu` |
| **`mixins/themes.py`** | 4 | `load_themes`, `refresh_theme_combo`, `get_theme`, `set_theme` |
| **`mixins/events.py`** | 9 | `closeEvent`, `hideEvent`, `showEvent`, `leaveEvent`, `moveEvent`, `resizeEvent`, `timerEvent`, `wheelEvent`, `keyPressEvent`, `keyReleaseEvent` |
| **`mixins/dialogs.py`** | 20 | `show_about_dialog`, `show_timestamp_dialog`, `show_trim_dialog`, `show_size_dialog`, `show_search_popup`, `show_delete_prompt`, `browse_for_directory`, `browse_for_save_file`, `browse_for_subtitle_files`, `_show_ffmpeg_missing_dialog`, `_show_duration_error_dialog`, `_show_compress_error_dialog`, `_cleanup_temp_files`, `marquee`, `_log_on_statusbar_slot`, `handle_updates`, `_handle_updates`, `add_info_actions`, `convert_snapshot_to_jpeg` |
| **`mixins/ui_state.py`** | 25 | `set_advancedcontrols_visible`, `set_progressbar_visible`, `set_statusbar_visible`, `set_menubar_visible`, `refresh_copy_image_action`, `refresh_shortcuts`, `refresh_cover_art`, `refresh_autoplay_button`, `refresh_confusing_zoom_setting_tooltip`, `refresh_recycle_tooltip`, `refresh_volume_tooltip`, `refresh_marked_for_deletion_tooltip`, `refresh_snapshot_button_controls`, `is_snap_mode_enabled`, `snap_to_player_size`, `snap_to_native_size`, `mark_for_deletion`, `clear_marked_for_deletion`, `get_output`, `get_save_remnant`, `get_popup_location_kwargs`, `get_hotkey_full_string`, `get_new_file_timestamps`, `set_file_timestamps`, `_refresh_title_slot` |
| **`signals.py`** | 1 (function) | `connect_widget_signals()` |
| **`shortcuts.py`** | 1 (function) | `connect_shortcuts()` |
| **`tray.py`** | 2 (functions) | `exit()`, `get_tray_icon()` |
| **`app.py`** | 1 (function) | `after_show_setup()` |

**Total: 164 methods + 5 module-level functions = 169 units accounted for.**

---

## File Mapping: Current → New

### Root-level Python files

| Current Location | New Location | Notes |
|-----------------|--------------|-------|
| `main.pyw` | `src/pyplayer/__main__.py` + `src/pyplayer/app.py` + `gui/mixins/*.py` | Decomposed |
| `config.py` | `src/pyplayer/config.py` | Moved, imports updated |
| `constants.py` | `src/pyplayer/constants.py` | Moved, imports updated |
| `compression.py` | `src/pyplayer/core/compression.py` | Moved to core/ |
| `util.py` | `src/pyplayer/core/ffmpeg.py` + `core/file_ops.py` + `core/media_utils.py` | Split by domain |
| `qthelpers.py` | `src/pyplayer/gui/helpers.py` | Moved to gui/ |
| `qtstart.py` | `src/pyplayer/app.py` + `gui/signals.py` + `gui/shortcuts.py` + `gui/tray.py` | Decomposed |
| `update.py` | `src/pyplayer/update.py` | Moved |
| `resource_helper.py` | `src/pyplayer/resource_helper.py` | Moved |
| `widgets.py` | `src/pyplayer/widgets/*.py` | Split per-class |

### bin/ directory

| Current Location | New Location | Notes |
|-----------------|--------------|-------|
| `bin/window_*.py` | `src/pyplayer/ui/window_*.py` | Generated UI files |
| `bin/window_*.ui` | `ui_sources/*.ui` | Qt Designer sources |
| `bin/configparsebetter.py` | `src/pyplayer/core/config_parser.py` | Moved to core/ |
| `bin/updater.py` | `src/pyplayer/updater_cli.py` | **NOT a duplicate** — standalone zip extractor used for auto-updates, referenced by `executable/updater.spec` |
| `bin/*.pdn` | `assets/logos/` | Design files |

### executable/ directory → packaging/

> **Note:** Using `packaging/` instead of `build/` to avoid conflict with setuptools' default `build/` output directory.

| Current Location | New Location | Notes |
|-----------------|--------------|-------|
| `executable/build.py` | `packaging/build.py` | Renamed dir |
| `executable/hook.py` | `packaging/hook.py` | Moved |
| `executable/main.spec` | `packaging/main.spec` | Moved |
| `executable/main_onefile.spec` | `packaging/main_onefile.spec` | Moved |
| `executable/updater.spec` | `packaging/updater.spec` | Moved — references `bin/updater.py` (must update path) |
| `executable/exclude.txt` | `packaging/exclude.txt` | Moved |
| `executable/installer.iss` | `packaging/installer.iss` | Moved |
| `executable/version_info_*.txt` | `packaging/version_info/*.txt` | Moved |
| `executable/include/` | `packaging/include/` | Moved |
| `executable/!readme.txt` | `packaging/README.md` | Moved + renamed |
| `executable/build/` (PyInstaller output) | `.gitignore` | Build output, not source |
| `executable/compiling/` | `.gitignore` | Build output, not source |
| `executable/installer_output/` | `.gitignore` | Build output, not source |

### util.py per-function mapping (19 functions + 2 lambdas)

| Function | Target Module | Notes |
|----------|--------------|-------|
| `ffmpeg()` | `core/ffmpeg.py` | FFmpeg subprocess wrapper |
| `ffmpeg_async()` | `core/ffmpeg.py` | Async FFmpeg subprocess |
| `kill_process()` | `core/ffmpeg.py` | Process management |
| `suspend_process()` | `core/ffmpeg.py` | Windows process suspend |
| `sanitize()` | `core/file_ops.py` | Filename sanitization |
| `get_unique_path()` | `core/file_ops.py` | Path uniqueness |
| `add_path_suffix()` | `core/file_ops.py` | Path suffix helper |
| `open_properties()` | `core/file_ops.py` | Windows file properties dialog |
| `setctime()` | `core/file_ops.py` | File creation time (Windows) |
| `get_from_PATH()` | `core/file_ops.py` | PATH lookup utility |
| `file_is_hidden` (lambda) | `core/file_ops.py` | Hidden file check |
| `get_hms()` | `core/media_utils.py` | Seconds to H:M:S:MS |
| `get_PIL_Image()` | `core/media_utils.py` | PIL Image import wrapper |
| `get_ratio_string()` | `core/media_utils.py` | Aspect ratio string |
| `get_verbose_timestamp()` | `core/media_utils.py` | Human-readable timestamp |
| `scale()` | `core/media_utils.py` | Dimension scaling |
| `remove_dict_value()` | `core/media_utils.py` | Dict utility |
| `remove_dict_values()` | `core/media_utils.py` | Dict utility |
| `foreground_is_fullscreen()` | `gui/helpers.py` | Windows-specific, Qt-adjacent |
| `get_font_path()` | `gui/helpers.py` | Windows-specific, font utility |

### widgets.py per-class mapping

| Class | Target Module | Lines (~) | Notes |
|-------|--------------|-----------|-------|
| `PyPlayerBackend` | `widgets/video_player.py` | 320 | Abstract backend |
| `PlayerVLC` | `widgets/video_player.py` | 750 | VLC implementation |
| `PlayerQt` | `widgets/video_player.py` | 240 | Qt multimedia implementation |
| `QVideoPlayer` | `widgets/video_player.py` | 680 | Main player widget |
| `QVideoPlayerLabel` | `widgets/video_player.py` | 520 | Video display label |
| `QVideoSlider` | `widgets/video_slider.py` | 400 | Custom seek bar |
| `QVideoListItemWidget` | `widgets/video_list.py` | 40 | Concat list item |
| `QVideoList` | `widgets/video_list.py` | 270 | Concat list widget |
| `QTextOverlayPreview` | `widgets/overlays.py` | 250 | Text overlay preview |
| `QTextOverlay` | `widgets/overlays.py` | 35 | Text overlay handler |
| `QColorPickerButton` | `widgets/overlays.py` | 260 | Color picker widget |
| `QKeySequenceFlexibleEdit` | `widgets/inputs.py` | 130 | Hotkey input widget |
| `QWidgetPassthrough` + subclasses | `widgets/inputs.py` | 100 | Passthrough widgets |
| `QSpinBoxInputSignals` | `widgets/inputs.py` | 35 | SpinBox signal helper |
| `QDraggableWindowFrame` | `widgets/draggable.py` | 200 | Draggable frame widget |

**Module-level aliases in `widgets.py`** (`gui`, `app`, `cfg`, `settings`, `ZOOM_*` constants) are set by `main.pyw` at runtime. These must be relocated to `widgets/__init__.py` and the alias-setting mechanism updated in `app.py`.

### qtstart.py per-function mapping

| Function | Target Module | Lines | Notes |
|----------|--------------|-------|-------|
| `exit()` | `gui/tray.py` | ~25 | Application exit handler |
| `get_tray_icon()` | `gui/tray.py` | ~40 | System tray icon creation |
| `after_show_setup()` | `app.py` | ~75 | Post-show initialization |
| `connect_shortcuts()` | `gui/shortcuts.py` | ~63 | Hotkey connections |
| `connect_widget_signals()` | `gui/signals.py` | ~210 | Widget signal wiring |
| Module-level code (argparse, logging) | `app.py` | ~70 | Startup sequence |

---

## Key Design Decisions

### 1. src/ layout
Standard PyPA-recommended layout. Prevents import confusion between local files and installed package. PyInstaller supports this via `--paths src/` in spec files.

### 2. Mixin pattern over Composition
The existing codebase uses `self.widget_name` extensively — over 500 direct widget attribute accesses in `GUI_Instance`. Composition would require changing every one of these. Mixins preserve the flat `self.xxx` access pattern while splitting code into separate files.

### 3. config_parser.py stays separate
`ConfigParseBetterQt` is a standalone library (1,079 lines) with its own API. It should not be merged into `config.py` which is the consumer of that library.

### 4. signals.py and shortcuts.py as standalone modules
These contain 200+ and 60 lines of signal wiring respectively. They don't fit as mixins (no reusable logic) and are called once during setup. Keeping them as standalone functions that accept `MainWindow` instances matches the existing `qtstart.py` pattern.

### 5. widgets/ package with __init__.py re-exports
All widget classes are re-exported from `widgets/__init__.py` so existing imports like `from widgets import QVideoPlayer` continue to work with minimal changes.

---

## Import Strategy

All internal imports use absolute imports from the package root:

```python
# Before (relative, from root)
import util
import constants
import widgets
from bin.configparsebetter import ConfigParseBetterQt

# After (absolute, from package)
from pyplayer.core import ffmpeg, file_ops, media_utils
from pyplayer.core.config_parser import ConfigParseBetterQt
from pyplayer.widgets import QVideoPlayer
from pyplayer import constants
```

For the `__main__.py` entry point:

```python
# src/pyplayer/__main__.py
import sys
from pyplayer.app import main

if __name__ == '__main__':
    sys.exit(main())
```

---

## Build System Changes

### pyproject.toml

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
    "tinytag>=1.9.0",
    "music-tag>=0.4.3",
]

[project.gui-scripts]
pyplayer = "pyplayer.app:main"  # Not __main__ — app.py owns the actual main() function

[project.optional-dependencies]
build = ["pyinstaller>=5.13.0"]

[tool.setuptools.packages.find]
where = ["src"]
```

### PyInstaller spec updates

- Add `--paths src/` to locate the package
- Update `hook.py` to use new module paths
- Update `exclude.txt` with new module structure
- Update `version_info` file paths

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Circular imports between mixins | Each mixin only imports from `core/`, not from other mixins. All shared state goes through `self` (the MainWindow instance). |
| PyInstaller can't find modules | Update spec file `--paths` and `hiddenimports`. Test build early. |
| Qt Designer .ui file paths | Update `convert_ui.py` script to output to `src/pyplayer/ui/`. |
| Missing imports after refactor | Use grep to verify all imports resolve before testing. Run application to verify. |
| MRO (Method Resolution Order) conflicts | Only `Ui_MainWindow` and `QMainWindow` have `__init__` — mixins use no `__init__` or call `super().__init__()` consistently. **Critical ordering:** `MainWindow.__init__()` must call `Ui_MainWindow.setupUi(self)` before any mixin methods access widget attributes. |
| `.pyw` console suppression on Windows | `.pyw` extension suppresses console window. After restructure: (1) use `pythonw -m pyplayer` for console-free execution, (2) or provide a `pyplayer.pyw` stub at repo root for backward compatibility, (3) PyInstaller spec handles console suppression via its own configuration. |

---

## Migration Order

The migration must be done in phases to ensure the application works at each step:

### Phase 1: Package scaffold (no logic changes)
1. Create `src/pyplayer/` with `__init__.py`, `__main__.py`
2. Create `pyproject.toml`
3. Create empty sub-packages (`core/`, `gui/`, `gui/mixins/`, `widgets/`, `ui/`)
4. Verify `python -m pyplayer` can start (even if it just imports)

### Phase 2: Move independent modules (no dependency changes)
1. Move `constants.py` → `src/pyplayer/constants.py`
2. Move `resource_helper.py` → `src/pyplayer/resource_helper.py`
3. Move `update.py` → `src/pyplayer/update.py`
4. Move `bin/configparsebetter.py` → `src/pyplayer/core/config_parser.py`
5. Move `bin/window_*.py` → `src/pyplayer/ui/`
6. Move `compression.py` → `src/pyplayer/core/compression.py`

### Phase 3: Move util.py (split into core/)
1. Create `core/ffmpeg.py`, `core/file_ops.py`, `core/media_utils.py`
2. Split functions from `util.py` into appropriate modules
3. Update all imports referencing `util`

### Phase 4: Split widgets.py
1. Create `widgets/*.py` files per class grouping
2. Create `widgets/__init__.py` with re-exports
3. Update all imports referencing `widgets`

### Phase 5: Decompose main.pyw (biggest phase)
1. Extract `Edit` and `Undo` classes → `core/edit.py`
2. Extract `CompressProgressDialog` → `gui/progress.py`
3. Extract top-level functions (`probe_files`, `get_audio_duration`, etc.) → `core/`
4. Create mixin files and move methods from `GUI_Instance`
5. Create `MainWindow` class composing all mixins
6. Create `gui/signals.py`, `gui/shortcuts.py`, `gui/tray.py` from `qtstart.py`
7. Create `app.py` from remaining `qtstart.py` code + entry point

### Phase 6: Restructure packaging & assets
1. Move `executable/` → `packaging/` (not `build/` — avoids setuptools conflict)
2. Move `.ui` files → `ui_sources/`
3. Move assets → `assets/`
4. Update `build.py`, `.spec` files, and `hook.py` for new module paths
5. Update `convert_ui_to_py.py` → `scripts/convert_ui.py`

### Phase 7: Cleanup
1. Delete old files (`main.pyw`, `bin/`, `executable/`)
2. Update `README.md`, `AGENTS.md`, `CLAUDE.md`
3. Update `.gitignore`
4. Test full application + build

---

## Validation Criteria

The restructure is successful when:
- [ ] `python -m pyplayer` launches the application
- [ ] Video playback works for all supported formats
- [ ] Trim/crop/save/compress operations work
- [ ] Theme switching works
- [ ] Configuration save/load persists correctly
- [ ] Keyboard shortcuts function
- [ ] System tray icon works
- [ ] Drag and drop works
- [ ] PyInstaller build produces a working executable
- [ ] No file exceeds 500 lines (ideal) or 800 lines (maximum)
