# Package Structure

> The `src/pyplayer/` package layout and the transition from flat files.

---

## Package Layout

```
src/pyplayer/
├── __init__.py           # Package root
├── __main__.py           # python -m pyplayer entry
├── app.py                # QApplication startup
├── constants.py          # Global constants
├── config.py             # Configuration management
├── resource_helper.py    # Resource path helpers
├── update.py             # Update checking
├── updater_cli.py        # Standalone updater
│
├── core/                 # Business logic (no Qt dependency)
│   ├── config_parser.py
│   ├── compression.py
│   ├── edit.py
│   ├── ffmpeg.py
│   ├── file_ops.py
│   ├── media_utils.py
│   └── probe.py
│
├── workers/              # Background QThread workers
│   └── compression_worker.py
│
├── gui/                  # GUI layer
│   ├── main_window.py    # MainWindow = mixin composition
│   ├── helpers.py
│   ├── progress.py
│   ├── signals.py
│   ├── shortcuts.py
│   ├── tray.py
│   └── mixins/           # 9 behavior mixins
│
├── widgets/              # Custom Qt widgets
│   ├── player_backend.py
│   ├── player_widget.py
│   ├── player_label.py
│   ├── video_slider.py
│   ├── video_list.py
│   ├── overlays.py
│   ├── inputs.py
│   ├── draggable.py
│   └── helpers.py
│
└── ui/                   # Generated from Qt Designer
    ├── window_pyplayer.py
    ├── window_settings.py
    ├── window_about.py
    ├── window_cat.py
    ├── window_text.py
    └── window_timestamp.py
```

## Layer Separation

| Layer | Subpackage | Qt Dependency | Purpose |
|-------|-----------|---------------|---------|
| Core | `core/` | None | Business logic, FFmpeg, compression, file ops |
| Workers | `workers/` | PyQt5 (QtCore only) | Background QThread workers |
| GUI | `gui/` | PyQt5 | Windows, mixins, signals, shortcuts |
| Widgets | `widgets/` | PyQt5 | Reusable custom widgets |
| UI | `ui/` | PyQt5 | Generated UI code (from Qt Designer) |

## Transition from Flat Layout

The codebase was restructured from a flat layout (Phase 7, 2026-03-28):

- **Before:** `main.pyw` (531KB) was a single monolithic file (now a 23-line thin wrapper)
- **After:** Split into ~49 focused modules under 800 lines each
- **MainWindow** decomposed into 9 mixin classes
- **Build configs** consolidated into `packaging/` directory
- **Original flat files** preserved in repo root for fallback testing

### Migration Map

| Old File | New Location(s) |
|----------|----------------|
| `main.pyw` | `run.pyw` (backward-compatible wrapper) + `src/pyplayer/__main__.py` + `src/pyplayer/app.py` |
| `widgets.py` | `src/pyplayer/widgets/` (per-class modules) |
| `util.py` | `src/pyplayer/core/ffmpeg.py` + `file_ops.py` + `media_utils.py` |
| `qthelpers.py` | `src/pyplayer/gui/helpers.py` |
| `qtstart.py` | `src/pyplayer/app.py` + `gui/signals.py` |
| `constants.py` | `src/pyplayer/constants.py` |
| `config.py` | `src/pyplayer/config.py` |
| `compression.py` | `src/pyplayer/core/compression.py` |

## Import Style

New code uses package imports:

```python
from pyplayer.core import run_ffmpeg, probe_media
from pyplayer.gui.mixins import SavingMixin
from pyplayer.widgets import QVideoPlayer
```

Legacy code at root still uses flat imports. Both work during the transition.

## UI Generation

1. Edit `.ui` files in `ui_sources/` with Qt Designer
2. Run `scripts/convert_ui.py` to regenerate Python files into `src/pyplayer/ui/`

## Keyboard Shortcuts

1. Add to `gui/shortcuts.py` dictionary
2. Corresponding widget in `dialog_settings.formKeys`

## Adding Configuration Options

1. Add to `config.py:loadConfig()` for reading
2. Add to `config.py:saveConfig()` for saving
3. Use `cfg.load()` and `cfg.save()` helpers

## Building

Two approaches exist (pre and post restructure):
- **New way:** `python build.py` from `packaging/` directory (consolidated scripts)
- **Legacy way:** `python -m PyInstaller main.spec` from `executable/` directory

See [[docs/build/packaging-guide]] for the full build instructions.

---

## Design Origin

- Spec: [[docs/superpowers/specs/2026-03-28-repo-restructure-design]]
- Plan: [[docs/superpowers/plans/2026-03-28-repo-restructure]]

---

Related: [[docs/architecture/app-flow]] | [[docs/architecture/mainwindow-mixins]] | [[docs/project/repository-map]] | [[docs/reference/config-and-paths]]
