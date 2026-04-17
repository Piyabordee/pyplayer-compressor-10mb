# Application Flow

> How PyPlayer starts up and connects its subsystems.

---

## Entry Points

Both resolve to the same startup sequence:

1. `pyplayer.pyw` (root, backward-compatible)
2. `python -m pyplayer` (package entry via `src/pyplayer/__main__.py`)

## Startup Sequence

```
pyplayer.pyw or python -m pyplayer
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
                ├─→ gui/mixins/        Behavior modules (9 mixins)
                │   See [[docs/architecture/mainwindow-mixins]]
                │
                ├─→ widgets/           Custom Qt widgets
                │   See [[docs/integrations/vlc-backend]]
                │
                └─→ core/              Business logic (no Qt dependency)
                    See [[docs/integrations/ffmpeg-and-ffprobe]]
```

## Initialization Order

1. **Platform detection** (`constants.py`) — Detect OS, set paths, verify FFmpeg
2. **Configuration** (`config.py`) — Load user settings from `config.ini`
3. **Resource resolution** (`resource_helper.py`) — Determine resource paths (dev vs compiled)
4. **QApplication** (`app.py`) — Create Qt application, parse CLI args
5. **MainWindow** (`gui/main_window.py`) — Compose from 9 mixins
6. **Signal connections** (`gui/signals.py`) — Wire up all signal/slot connections
7. **Keyboard shortcuts** (`gui/shortcuts.py`) — Register all shortcuts
8. **System tray** (`gui/tray.py`) — Set up tray icon and menu

## Key Patterns

1. **Signal-Slot Connections** — Heavy use of Qt's signal/slot mechanism throughout
2. **Threading** — Daemon threads for background operations (update checking, command interface)
3. **Configuration** — Custom `ConfigParseBetterQt` class with UTF-16 encoding
4. **Logging** — Python's `logging` module with file and stream handlers

## Debugging

- Logs written to `pyplayer.log` in application directory
- Use `--debug` flag when running from command line
- Set `logging.DEBUG` level in `qtstart.py`

---

Related: [[docs/architecture/mainwindow-mixins]] | [[docs/architecture/package-structure]] | [[docs/reference/config-and-paths]] | [[docs/integrations/vlc-backend]]
