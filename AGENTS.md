# AGENTS.md - PyPlayer Compressor

> Project-specific guidance for AI agents working on the PyPlayer Compressor codebase.

---

## Project Overview

**PyPlayer Compressor** is a modified fork of [PyPlayer](https://github.com/thisismy-github/pyplayer) - a powerful video player and editor built on VLC and PyQt5.

### Key Characteristics
- **Type:** Desktop GUI Application (Video Player/Editor)
- **Primary Language:** Python 3.13+
- **UI Framework:** PyQt5
- **Media Backend:** VLC Media Player (libvlc) + FFmpeg for editing
- **Platform Focus:** Windows (primary), with Linux/macOS support
- **Fork Changes:** Always-visible Save button for faster video export workflow

### Core Features
- **Video Editing:** Trim, crop, concatenate, fade effects, rotate/flip
- **Audio Editing:** Amplify, replace tracks, add audio to images
- **Format Support:** MP4, MP3, WAV, AAC, GIF, and more
- **Quick Actions:** Instant file cycling, snapshots, rename/delete in place
- **Drag & Drop:** Files, folders, or subtitles
- **Custom Themes:** Qt Stylesheet-based theming system

---

## Repository Structure

The codebase has been restructured from a flat layout into a proper Python package under `src/pyplayer/`. Original flat files are preserved in the repo root for fallback testing during the transition.

```
pyplayer-master/
├── pyplayer.pyw              # Backward-compatible entry point
├── pyproject.toml            # Package build config
├── src/pyplayer/
│   ├── __init__.py           # Package root
│   ├── __main__.py           # python -m pyplayer entry
│   ├── app.py                # QApplication startup
│   ├── constants.py          # Global constants
│   ├── config.py             # Configuration management
│   ├── resource_helper.py    # Resource path helpers
│   ├── update.py             # Update checking
│   ├── updater_cli.py        # Standalone updater (extracts .zip)
│   │
│   ├── core/
│   │   ├── config_parser.py  # Custom config parser
│   │   ├── compression.py    # Video compression
│   │   ├── edit.py           # Edit queue management
│   │   ├── ffmpeg.py         # FFmpeg subprocess wrappers
│   │   ├── file_ops.py       # File operations
│   │   ├── media_utils.py    # Media utility functions
│   │   └── probe.py          # FFprobe media analysis
│   │
│   ├── gui/
│   │   ├── main_window.py    # MainWindow (mixin composition)
│   │   ├── helpers.py        # Qt utility functions
│   │   ├── progress.py       # Progress dialogs
│   │   ├── signals.py        # Signal connections
│   │   ├── shortcuts.py      # Keyboard shortcuts
│   │   ├── tray.py           # System tray
│   │   └── mixins/
│   │       ├── playback.py   # Volume, tracks, rate, navigation
│   │       ├── editing.py    # Trim, crop, edit queue
│   │       ├── saving.py     # Save, export, compress
│   │       ├── file_management.py  # Open, cycle, copy, rename
│   │       ├── menus.py      # Context menus, mouse events
│   │       ├── themes.py     # Theme loading/switching
│   │       ├── events.py     # Qt event handlers
│   │       ├── dialogs.py    # Dialogs, browse, updates
│   │       └── ui_state.py   # Visibility, state, statusbar
│   │
│   ├── widgets/
│   │   ├── player_backend.py # VLC/Qt player backends
│   │   ├── player_widget.py  # QVideoPlayer
│   │   ├── player_label.py   # QVideoPlayerLabel
│   │   ├── video_slider.py   # QVideoSlider
│   │   ├── video_list.py     # QVideoList
│   │   ├── overlays.py       # Text overlays, color picker
│   │   ├── inputs.py         # Key sequence edit, passthrough widgets
│   │   ├── draggable.py      # Draggable window frame
│   │   └── helpers.py        # Runtime aliases, ZOOM constants
│   │
│   └── ui/
│       ├── window_pyplayer.py  # Main window UI
│       ├── window_settings.py  # Settings UI
│       ├── window_about.py     # About dialog UI
│       ├── window_cat.py       # Category dialog UI
│       ├── window_text.py      # Text dialog UI
│       └── window_timestamp.py # Timestamp dialog UI
│
├── packaging/                 # Build configs (PyInstaller, Inno Setup)
├── ui_sources/                # Qt Designer .ui source files
├── assets/                    # Design files (.pdn logos)
├── scripts/                   # Utility scripts (convert_ui.py)
├── tests/                     # Test suite
├── themes/                    # Qt theme files (unchanged)
├── bin/                       # Original files (kept during transition)
│
├── main.pyw                   # OLD entry point (kept for fallback)
├── widgets.py                 # OLD widgets (kept for fallback)
├── util.py                    # OLD utilities (kept for fallback)
├── qthelpers.py               # OLD Qt helpers (kept for fallback)
├── qtstart.py                 # OLD startup (kept for fallback)
├── constants.py               # OLD constants (kept for fallback)
├── config.py                  # OLD config (kept for fallback)
├── compression.py             # OLD compression (kept for fallback)
├── resource_helper.py         # OLD resource helper (kept for fallback)
├── update.py                  # OLD update (kept for fallback)
└── executable/                # OLD build configs (kept for fallback)
```

---

## Architecture Overview

### Application Flow

```
pyplayer.pyw or python -m pyplayer (entry points)
    │
    └─→ src/pyplayer/__main__.py
        │
        └─→ src/pyplayer/app.py (QApplication startup)
            │
            ├─→ constants.py          Platform detection, paths, FFmpeg verification
            ├─→ config.py             Load/Save user configuration
            ├─→ resource_helper.py    Resource path resolution (dev vs compiled)
            │
            └─→ gui/main_window.py    MainWindow = mixin composition
                │
                ├─→ gui/signals.py     Signal/slot connections
                ├─→ gui/shortcuts.py   Keyboard shortcuts
                ├─→ gui/tray.py        System tray icon
                │
                ├─→ gui/mixins/
                │   ├─→ playback.py       Volume, tracks, rate, navigation
                │   ├─→ editing.py        Trim, crop, edit queue
                │   ├─→ saving.py         Save, export, compress
                │   ├─→ file_management.py Open, cycle, copy, rename
                │   ├─→ menus.py          Context menus, mouse events
                │   ├─→ themes.py         Theme loading/switching
                │   ├─→ events.py         Qt event handlers
                │   ├─→ dialogs.py        Dialogs, browse, updates
                │   └─→ ui_state.py       Visibility, state, statusbar
                │
                ├─→ widgets/
                │   ├─→ player_backend.py VLC backend integration
                │   ├─→ player_widget.py  QVideoPlayer
                │   ├─→ video_slider.py   QVideoSlider (seek bar)
                │   └─→ ...
                │
                └─→ core/
                    ├─→ ffmpeg.py         FFmpeg subprocess wrappers
                    ├─→ compression.py    Video compression (~10MB)
                    ├─→ edit.py           Edit queue management
                    ├─→ probe.py          FFprobe media analysis
                    └─→ ...
```

### Key Classes and Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `MainWindow` | `gui/main_window.py` | Main window (mixin composition) |
| `PlaybackMixin` | `gui/mixins/playback.py` | Volume, tracks, rate, navigation |
| `EditingMixin` | `gui/mixins/editing.py` | Trim, crop, edit queue |
| `SavingMixin` | `gui/mixins/saving.py` | Save, export, compress |
| `FileManagementMixin` | `gui/mixins/file_management.py` | Open, cycle, copy, rename |
| `MenusMixin` | `gui/mixins/menus.py` | Context menus, mouse events |
| `ThemesMixin` | `gui/mixins/themes.py` | Theme loading/switching |
| `EventsMixin` | `gui/mixins/events.py` | Qt event handlers |
| `DialogsMixin` | `gui/mixins/dialogs.py` | Dialogs, browse, updates |
| `UIStateMixin` | `gui/mixins/ui_state.py` | Visibility, state, statusbar |
| `QVideoPlayer` | `widgets/player_widget.py` | VLC media player widget wrapper |
| `QVideoSlider` | `widgets/video_slider.py` | Custom seek bar with hover preview |
| `QVideoPlayerLabel` | `widgets/player_label.py` | VLC label-based player backend |
| `Ui_MainWindow` | `ui/window_pyplayer.py` | Main window UI structure |
| `ConfigParseBetterQt` | `core/config_parser.py` | Configuration file management |
| `compress_video()` | `core/compression.py` | Video compression with bitrate calculation |
| `getPopup()` | `gui/helpers.py` | Generic dialog creation |
| `run_ffmpeg()` | `core/ffmpeg.py` | FFmpeg subprocess wrapper |
| `probe_media()` | `core/probe.py` | FFprobe media analysis |

---

## Core Dependencies

```python
# From requirements.txt
PyQt5>=5.15.9          # UI Framework
python-vlc>=3.0.18122  # VLC bindings
pillow==9.5.0          # Image processing
requests>=2.31.0       # Update checking
pywin32>=306           # Windows-specific APIs
pyinstaller>=5.13.0    # Building executables
tinytag>=1.9.0         # Media metadata
music-tag>=0.4.3       # Audio metadata
```

### External Binaries Required
- **VLC:** `libvlc.dll`, `libvlccore.dll`, plugins/
- **FFmpeg:** `ffmpeg.exe`, `ffprobe.exe` (for editing features)

---

## Working with This Codebase

### Code Style Conventions

1. **Naming:**
   - Functions: `snake_case` (Python standard)
   - Qt methods in `qthelpers.py`: `camelCase` (to match Qt style)
   - Classes: `PascalCase`
   - Constants: `UPPER_SNAKE_CASE`

2. **Imports:**
   - PyQt5 imports typically: `from PyQt5 import QtCore, QtGui, QtWidgets as QtW`
   - Relative imports for project modules

3. **Comments:**
   - Module headers include author attribution: `thisismy-github`
   - Thai language comments present (fork maintainer: Piyabordee)

### Key Patterns

1. **Signal-Slot Connections:** Heavy use of Qt's signal/slot mechanism throughout
2. **Threading:** Daemon threads for background operations (update checking, command interface)
3. **Configuration:** Custom `ConfigParseBetterQt` class with UTF-16 encoding
4. **Logging:** Python's `logging` module with file and stream handlers

### Important Constants

| Constant | Value/Location | Purpose |
|----------|----------------|---------|
| `VERSION` | `'pyplayer 0.6.0 beta'` | Application version |
| `CONFIG_PATH` | `config.ini` in CWD | User settings |
| `LOG_PATH` | `pyplayer.log` in CWD | Application log |
| `FFMPEG` | Dynamic path | FFmpeg executable |
| `IS_COMPILED` | `sys.frozen` check | Detects if running as exe |

---

## Common Tasks

### Adding a New Feature

1. **UI Components:**
   - Edit `.ui` files in `ui_sources/` with Qt Designer
   - Run `scripts/convert_ui.py` to regenerate Python files into `src/pyplayer/ui/`
   - Connect signals in `gui/signals.py`

2. **Configuration Options:**
   - Add to `config.py:loadConfig()` for reading
   - Add to `config.py:saveConfig()` for saving
   - Use `cfg.load()` and `cfg.save()` helpers

3. **Keyboard Shortcuts:**
   - Add to `gui/shortcuts.py` dictionary
   - Corresponding widget in `dialog_settings.formKeys`

4. **MainWindow Mixins:**
   - Add new behavior to the appropriate mixin in `gui/mixins/`
   - Import the mixin class in `gui/main_window.py`

### Building Executable

```bash
# From packaging/ directory
python build.py
```

Uses PyInstaller with:
- Spec files in `packaging/` (pyplayer.spec, updater.spec)
- One-file mode
- Entry point: `src/pyplayer/__main__.py`

### Debugging

- Logs written to `pyplayer.log` in application directory
- Use `--debug` flag when running from command line
- Set `logging.DEBUG` level in `qtstart.py`

---

## Platform-Specific Notes

### Windows (Primary)
- Uses `pywin32` for:
  - File properties dialogs (`util.open_properties()`)
  - Font path resolution (`util.get_font_path()`)
  - Process suspension (`util.suspend_process()`)
- System tray icon with `QSystemTrayIcon`
- Taskbar progress/controls integration

### Linux/macOS
- FFmpeg via `shlex.split()` for command parsing
- Different startup info (no `STARTUPINFO`)
- Some Windows-specific features gracefully disabled

---

## Known Issues and TODOs

### High Priority TODOs (from main.pyw)
- DPI/scaling support
- Further polish cropping feature
- Stability for videos >60fps
- Trimming support for obscure formats (3gp, ogv, mpg)
- Filetype associations

### Medium Priority
- System tray menu on Linux
- High-precision progress bar on non-1x speeds
- Resize-snapping on Linux

### Known Limitations
- Frame-seeking near video end occasionally unreliable (libvlc limitation)
- Concatenated videos may have missing frames between clips
- Some formats require specific FFmpeg codecs

---

## Fork-Specific Changes

### This Fork: PyPlayer Compressor
**Repository:** https://github.com/Piyabordee/pyplayer-compressor-10mb

**Modifications:**
1. **Always-visible Save button** - Save button permanently displayed in the quick actions row
   - Eliminates need to activate trim mode first
   - Improves workflow for quick video exports

2. **Quick Trim button** - Single Trim button replaces Start/End buttons (fully implemented)
   - Click Trim to set START at current position
   - END automatically follows current playback/seek position
   - Button displays remaining duration when active
   - Click Trim again to cancel trim
   - Visual feedback: Triangle markers on seek bar show START (left) and END (right) positions

3. **Auto-compress after trim** - Automatic video compression after saving trimmed videos
   - Settings checkbox to enable/disable auto-compression (config: `auto_compress_after_trim`)
   - Automatically compresses trimmed videos to target ~10MB using FFmpeg
   - Progress dialog shows compression status with polling mechanism
   - Cleanup of temporary files after compression
   - Modeless dialog allows continued use during compression
   - Improved error handling and completion callback

4. **Save workflow improvements**
   - Option to control auto-opening of files after saving (config: `auto_open_after_save`)

5. **Build & Compatibility**
   - Enhanced compatibility with PyInstaller 5.x and 6.x for path resolution and resource management
   - Improved build process with new scripts and resource management

6. **UI Polish**
   - Text color set to black for dialogs and progress indicators for better readability
   - Auto-compress checkbox synchronized with loaded settings
   - Improved error handling for theme directory creation

7. **Repository Restructure** (Phase 7)
   - Flat layout reorganized into `src/pyplayer/` package with subpackages: `core/`, `gui/`, `widgets/`, `ui/`
   - `main.pyw` (531KB) split into ~49 focused modules under 800 lines each
   - MainWindow decomposed into 9 mixin classes for maintainability
   - Build configs consolidated into `packaging/` directory
   - Backward-compatible entry points: `pyplayer.pyw` and `python -m pyplayer`
   - Original flat files preserved in repo root for fallback testing

**Recent Commits:**
```
c5b669a - feat(docs): add GitHub release guide for PyPlayer Compressor 10MB
b0adef1 - fix(constants): improve error handling for theme directory creation
aad8f39 - feat(compatibility): enhance compatibility with PyInstaller 5.x and 6.x for path resolution and resource management
81aec14 - feat(build): enhance build process with new scripts and resource management
1177be3 - fix(ui): set text color to black for various UI elements in dialogs and progress indicators
cc82a0c - feat(save): add option to control auto-opening of files after saving
c91f4c6 - fix(compression): improve error handling and completion callback for video compression
d4f57cc - fix(ui): synchronize auto-compress checkbox with loaded settings and improve compression handling
85cbdea - refactor(logging): change info logs to debug for detailed tracing
5058fff - fix(config): update default settings for trim mode and auto-compress
7646912 - fix(ui): make compression dialog modeless
3642d23 - fix(ui): add saving dialog during polling phase
f542c1d - fix(compression): use glob pattern to find temp files
e8a29e3 - fix(compression): fix polling to check correct temp filename
5af2324 - docs: add auto-compress feature testing documentation
e0767cd - feat(compression): add temp file cleanup helper
0542174 - feat(ui): add compression error dialog helpers
a4be93f - feat(compression): integrate auto-compress into trim save flow
b92bcda - feat(compression): add _compress_with_progress method
ded439d - feat(ui): add CompressProgressDialog class
e51f62c - fix(settings): pass parent to settings dialog creation
ded7401 - fix(settings): update runtime state when checkbox toggled
7e7b086 - feat(settings): connect auto-compress checkbox to config
539ac33 - fix(settings): add missing label text for auto-compress checkbox
1b045e8 - feat(settings): add auto-compress checkbox to settings dialog
4888f30 - fix(config): correctly assign auto_compress_after_trim to gui object
096035b - feat(config): save auto_compress_after_trim setting
ce346f6 - feat(config): load auto_compress_after_trim setting
66dec25 - feat(compression): add compress_video function with progress callback
72ec57f - fix(compression): correct import order for constants module
1ebda88 - feat(compression): add core compression module with bitrate calculation
e471d7d - docs: add implementation plan for auto-compress after trim
30a3a40 - docs: add auto-compress after trim feature design
a25ae0c - refactor(ui): remove duration display update from video slider functionality
6091752 - refactor(ui): enhance trim button functionality and streamline save process
8e10889 - refactor(ui): enhance video slider functionality for improved user interaction
79c6528 - refactor(ui): override setVisible method to ensure consistent visibility behavior
75207ca - refactor(ui): update volume slider layout and functionality for improved user experience
37d0c82 - refactor(ui): remove frameQuickChecks and frameCropInfo from advanced controls layout
15c5ced - refactor(ui): adjust layout by adding spacers and repositioning elements in advanced controls
60e6a2f - refactor(ui): remove checkboxes for deleting originals and skipping marked files from UI
```

---

## Testing Guidelines

### Manual Testing Checklist
- [ ] Video playback (various formats)
- [ ] Trim/crop operations
- [ ] Audio editing features
- [ ] Theme switching
- [ ] Configuration save/load
- [ ] Keyboard shortcuts
- [ ] Drag and drop functionality
- [ ] System tray (Windows)

### Before Committing
- Test on primary platform (Windows)
- Verify FFmpeg operations complete
- Check configuration persistence
- Test with various media file types

---

## Resources

### Original Project
- **GitHub:** https://github.com/thisismy-github/pyplayer
- **Credits:** All credit to `thisismy-github` for creating PyPlayer

### Key Documentation
- **PyQt5:** https://doc.qt.io/qtforpython/
- **python-vlc:** https://www.olivieraubert.net/vlc/python-ctypes/
- **FFmpeg:** https://ffmpeg.org/documentation.html

---

## Agent Instructions Summary

When working on this codebase:

1. **Read before modifying** - This is a mature codebase with established patterns
2. **Preserve existing behavior** - The fork's value is in its workflow improvements
3. **Test FFmpeg operations** - Editing features depend on external binaries
4. **Respect the original author's work** - This is a fork; maintain compatibility
5. **Use existing helpers** - `gui/helpers.py` and `core/file_ops.py` contain useful utilities
6. **Follow Qt patterns** - Signal/slot, proper widget lifecycle, etc.
7. **Handle platform differences** - Windows is primary; Linux/macOS secondary
8. **Package imports** - New code uses `from pyplayer.core import ...` style imports

---

*Last Updated: 2026-03-28 (Repo restructure into src/pyplayer/ package — Phase 7 complete)*
*Generated for: PyPlayer Compressor 0.6.0 beta*
