# Repository Map

> Guide to every folder and important file in the repo.
> The codebase was restructured from a flat layout into `src/pyplayer/` package (Phase 7).
> Original flat files are preserved in the repo root for fallback testing during the transition.

---

## Package Layout (`src/pyplayer/`)

```
src/pyplayer/
├── __init__.py           # Package root
├── __main__.py           # python -m pyplayer entry
├── app.py                # QApplication startup
├── constants.py          # Global constants (VERSION, FFMPEG, paths)
├── config.py             # Configuration management (load/save)
├── resource_helper.py    # Resource path helpers (dev vs compiled)
├── update.py             # Update checking logic
├── updater_cli.py        # Standalone updater (extracts .zip)
│
├── core/                 # Business logic (no Qt dependency)
│   ├── config_parser.py  # Custom config parser (ConfigParseBetterQt)
│   ├── compression.py    # Video compression (~10MB target)
│   ├── edit.py           # Edit queue management
│   ├── ffmpeg.py         # FFmpeg subprocess wrappers
│   ├── file_ops.py       # File operations (delete, rename, copy)
│   ├── media_utils.py    # Media utility functions
│   └── probe.py          # FFprobe media analysis
│
├── gui/                  # GUI layer
│   ├── main_window.py    # MainWindow (mixin composition)
│   ├── helpers.py        # Qt utility functions (getPopup, etc.)
│   ├── progress.py       # Progress dialogs
│   ├── signals.py        # Signal/slot connections
│   ├── shortcuts.py      # Keyboard shortcuts
│   ├── tray.py           # System tray icon
│   └── mixins/           # Behavior decomposition (9 mixins)
│       ├── playback.py       # Volume, tracks, rate, navigation
│       ├── editing.py        # Trim, crop, edit queue
│       ├── saving.py         # Save, export, compress
│       ├── file_management.py  # Open, cycle, copy, rename
│       ├── menus.py          # Context menus, mouse events
│       ├── themes.py         # Theme loading/switching
│       ├── events.py         # Qt event handlers
│       ├── dialogs.py        # Dialogs, browse, updates
│       └── ui_state.py       # Visibility, state, statusbar
│
├── widgets/              # Custom Qt widgets
│   ├── player_backend.py # VLC/Qt player backends
│   ├── player_widget.py  # QVideoPlayer
│   ├── player_label.py   # QVideoPlayerLabel
│   ├── video_slider.py   # QVideoSlider (seek bar)
│   ├── video_list.py     # QVideoList
│   ├── overlays.py       # Text overlays, color picker
│   ├── inputs.py         # Key sequence edit, passthrough widgets
│   ├── draggable.py      # Draggable window frame
│   └── helpers.py        # Runtime aliases, ZOOM constants
│
└── ui/                   # Generated UI code (from Qt Designer)
    ├── window_pyplayer.py  # Main window UI
    ├── window_settings.py  # Settings UI
    ├── window_about.py     # About dialog UI
    ├── window_cat.py       # Category dialog UI
    ├── window_text.py      # Text dialog UI
    └── window_timestamp.py # Timestamp dialog UI
```

## Support Directories

```
pyplayer-master/
├── packaging/                 # Build configs (PyInstaller specs, Inno Setup)
├── ui_sources/                # Qt Designer .ui source files
├── scripts/                   # Utility scripts (convert_ui.py)
├── assets/                    # Design files (.pdn logos)
├── tests/                     # Test suite (86 tests, pytest)
├── themes/                    # Qt theme stylesheets
│   └── resources/             # Icons (logo.ico, logo_filled.ico, updater.ico)
├── docs/                      # Project documentation (this tree)
├── bin/                       # Original files (kept during transition)
│   ├── window_pyplayer.py     # Generated UI code
│   ├── configparsebetter.py   # Config parser
│   └── updater.py             # Update utility
└── executable/                # OLD build configs (kept for fallback)
    ├── main.spec              # PyInstaller spec (onedir)
    ├── updater.spec           # PyInstaller spec (onefile)
    ├── hook.py                # Runtime hook (VLC path + PID management)
    ├── installer.iss          # Inno Setup installer script
    └── include/               # External binaries
        ├── ffmpeg-windows/    # ffmpeg.exe, ffprobe.exe, DLLs
        └── vlc-windows/       # libvlc.dll, libvlccore.dll, plugins/
```

## Legacy Root Files (Fallback)

These files are the original flat layout, preserved for fallback testing:

| File | Purpose | New Location |
|------|---------|--------------|
| `main.pyw` | Thin wrapper (was monolith) | `run.pyw` → `src/pyplayer/__main__.py` |
| `widgets.py` | All widgets | `src/pyplayer/widgets/` (per-class modules) |
| `util.py` | Utilities | `src/pyplayer/core/ffmpeg.py`, `file_ops.py`, `media_utils.py` |
| `qthelpers.py` | Qt helpers | `src/pyplayer/gui/helpers.py` |
| `qtstart.py` | Startup | `src/pyplayer/app.py` + `gui/signals.py` |
| `constants.py` | Constants | `src/pyplayer/constants.py` |
| `config.py` | Config | `src/pyplayer/config.py` |
| `compression.py` | Compression | `src/pyplayer/core/compression.py` |
| `resource_helper.py` | Resources | `src/pyplayer/resource_helper.py` |
| `update.py` | Update | `src/pyplayer/update.py` |

## Entry Points

1. **`run.pyw`** — Backward-compatible entry point (root, formerly `pyplayer.pyw`)
2. **`main.pyw`** — Legacy entry point (now a thin wrapper, same as run.pyw)
3. **`python -m pyplayer`** — Package entry via `src/pyplayer/__main__.py`
4. All resolve to `src/pyplayer/app.py` → `gui/main_window.py`

---

Related: [[docs/project/overview]] | [[docs/architecture/app-flow]] | [[docs/architecture/package-structure]] | [[docs/architecture/mainwindow-mixins]]
