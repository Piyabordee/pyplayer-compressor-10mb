# Configuration and Paths

> How PyPlayer manages configuration and resolves file paths.
> Critical for understanding dev vs compiled behavior differences.

---

## Configuration System

### Config File

- **Location:** `config.ini` in CWD (or application directory)
- **Encoding:** UTF-16
- **Parser:** Custom `ConfigParseBetterQt` class in `core/config_parser.py`

### Loading/Saving

- **Load:** `config.py:loadConfig()` reads all settings
- **Save:** `config.py:saveConfig()` writes all settings
- **Helpers:** `cfg.load()` and `cfg.save()` convenience methods

### Key Config Options

| Config Key | Default | Purpose |
|------------|---------|---------|
| `auto_compress_after_trim` | ON | Auto-compress trimmed videos |
| `auto_open_after_save` | Configurable | Auto-open saved files |
| Theme preference | — | Selected theme name |

Adding a new config option:
1. Add to `config.py:loadConfig()` for reading
2. Add to `config.py:saveConfig()` for saving
3. Use `cfg.load()` and `cfg.save()` helpers

---

## Path Resolution

### IS_COMPILED Detection

```python
IS_COMPILED = getattr(sys, 'frozen', False)
```

### Resource Paths

```python
# Dev mode:
CWD = os.path.dirname(os.path.abspath(sys.argv[0]))
RESOURCE_BASE = CWD

# Compiled mode (PyInstaller 6.x):
if IS_COMPILED and hasattr(sys, '_MEIPASS'):
    RESOURCE_BASE = sys._MEIPASS   # points to _internal/
```

### Theme Path

```python
THEME_DIR = os.path.join(RESOURCE_BASE, 'themes')
```

Must use `RESOURCE_BASE`, not `CWD` — otherwise themes won't load in compiled mode.

### FFmpeg Path

```python
FFMPEG = os.path.join(RESOURCE_BASE, 'plugins', 'ffmpeg', 'ffmpeg.exe')
```

Verified by `constants.py:verify_ffmpeg()`.

### VLC Path

Resolved in `hook.py` at runtime:
```python
if IS_FROZEN:
    if hasattr(sys, '_MEIPASS'):
        VLC_PATH = os.path.join(sys._MEIPASS, 'plugins', 'vlc')
    else:
        VLC_PATH = os.path.join(CWD, 'plugins', 'vlc')
```

---

## Platform Differences

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

## Code Style

### Naming Conventions

| Element | Style | Example |
|---------|-------|---------|
| Functions | `snake_case` | `run_ffmpeg()`, `probe_media()` |
| Qt methods | `camelCase` | (in `qthelpers.py` only) |
| Classes | `PascalCase` | `QVideoPlayer`, `SavingMixin` |
| Constants | `UPPER_SNAKE_CASE` | `VERSION`, `FFMPEG`, `IS_COMPILED` |

### Import Style

```python
# PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets as QtW

# Package imports (new code)
from pyplayer.core import run_ffmpeg
from pyplayer.gui.mixins import SavingMixin
```

### Comments

- Module headers include author attribution: `thisismy-github`
- Thai language comments present (fork maintainer: Piyabordee)

---

Related: [[docs/reference/key-constants]] | [[docs/architecture/package-structure]] | [[docs/build/packaging-guide]] | [[docs/integrations/vlc-backend]]
