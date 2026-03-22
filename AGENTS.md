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

```
pyplayer-master/
├── main.pyw                    # Entry point (531KB - contains most GUI logic)
├── config.py                   # Configuration loading/saving (ConfigParseBetter)
├── constants.py                # Global constants, paths, FFmpeg verification
├── util.py                     # Utility functions (FFmpeg wrappers, file ops)
├── qthelpers.py                # Qt utility functions and helpers
├── qtstart.py                  # Startup code, signal connections, tray icon
├── widgets.py                  # Custom Qt widgets (216KB)
├── update.py                   # Update checking and downloading
├── requirements.txt            # Python dependencies
├── README.md                   # User-facing documentation
│
├── bin/                        # UI components and utilities
│   ├── window_*.py            # Generated from Qt Designer .ui files
│   ├── configparsebetter.py   # Custom config parser
│   └── updater.py             # Update utility script
│
├── executable/                 # Build and distribution files
│   ├── build.py               # PyInstaller build script
│   ├── hook.py                # PyInstaller hooks
│   └── include/               # VLC and FFmpeg binaries
│
├── themes/                     # Qt Stylesheet theme files
│   ├── midnight.txt
│   ├── blueberry_breeze.txt
│   └── ...
│
└── CLAUDE.md / AGENTS.md       # AI agent guidance (you are here)
```

---

## Architecture Overview

### Application Flow

```
main.pyw (entry point)
    │
    ├─→ qtstart.py
    │   ├─→ Argument parsing
    │   ├─→ Logging setup
    │   ├─→ System tray creation
    │   └─→ Signal/widget connections
    │
    ├─→ config.py
    │   └─→ Load/Save user configuration
    │
    ├─→ constants.py
    │   ├─→ Platform detection
    │   ├─→ Path constants
    │   └─→ FFmpeg/FFprobe verification
    │
    └─→ widgets.py
        ├─→ QVideoPlayer (VLC wrapper)
        ├─→ QVideoSlider (custom progress bar)
        └─→ Custom Qt widgets
```

### Key Classes and Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `Ui_MainWindow` | `bin/window_pyplayer.py` | Main window UI structure |
| `QVideoPlayer` | `widgets.py` | VLC media player widget wrapper |
| `QVideoSlider` | `widgets.py` | Custom seek bar with hover preview |
| `ConfigParseBetterQt` | `bin/configparsebetter.py` | Configuration file management |
| `getPopup()` | `qthelpers.py` | Generic dialog creation |

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
   - Edit `.ui` files in `bin/` with Qt Designer
   - Run `convert_ui_to_py.py` to regenerate Python files
   - Connect signals in `qtstart.py:connect_widget_signals()`

2. **Configuration Options:**
   - Add to `config.py:loadConfig()` for reading
   - Add to `config.py:saveConfig()` for saving
   - Use `cfg.load()` and `cfg.save()` helpers

3. **Keyboard Shortcuts:**
   - Add to `qtstart.py:connect_shortcuts()` dictionary
   - Corresponding widget in `dialog_settings.formKeys`

### Building Executable

```bash
# From executable/ directory
python build.py
```

Uses PyInstaller with:
- `hook.py` for hidden imports
- `exclude.txt` for exclusion list
- One-file mode

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

**Recent Commits:**
```
23017fd - refactor(ui): remove unused buttons and tooltips from advanced controls
aa040b7 - refactor(ui): remove unused buttons and tooltips from advanced controls
d8cc2e6 - refactor(ui): remove unused buttons and add dummy widgets to prevent errors
6e18a87 - chore: update config.ini with new settings
09a086e - chore: update .gitignore to include build outputs and temporary files
dad013b - refactor: remove debug logging from trim implementation
c021fa7 - feat(widgets): show both START and END markers on seek bar
7084027 - fix(widgets): prevent START from moving during trim mode
d1130f7 - fix(trim): lock START position, let END follow playback
1ca518e - feat(trim): new workflow - start at current, end follows seek
0d2ccfa - fix(trim): use toggled signal instead of clicked
92d596a - fix(open): reset buttonTrim instead of buttonTrimStart/End
92855e4 - docs(readme): update trim workflow description
4b63acf - docs(AGENTS): document Quick Trim button feature
3eb5878 - docs(constants): update trim tooltip constant
eb1e5d3 - refactor(trim): update set_trim_mode for buttonTrim
b3c7348 - refactor(trim): comment out deprecated set_trim_start/end functions
ccf48cd - fix(playback): update trim end check for buttonTrim
064cb41 - fix(save): update trim check for buttonTrim
9934f57 - refactor(layout): update responsive layout for buttonTrim
33b082e - refactor(signals): connect buttonTrim signal
45d9a81 - feat(trim): add set_trim() function for quick trim behavior
4284c0d - refactor(ui): regenerate window_pyplayer.py with new Trim button
bc133a6 - refactor(ui): replace Start/End buttons with single Trim button
0175e8b - docs: Add Quick Trim Button implementation plan
6b0b4ca - docs: Add Quick Trim Button design spec
9837194 - docs: Add AGENTS.md for project-specific guidance and architecture overview
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
5. **Use existing helpers** - `qthelpers.py` and `util.py` contain useful utilities
6. **Follow Qt patterns** - Signal/slot, proper widget lifecycle, etc.
7. **Handle platform differences** - Windows is primary; Linux/macOS secondary

---

*Last Updated: 2026-03-22 (Updated with 31 recent commits)*
*Generated for: PyPlayer Compressor 0.6.0 beta*
