# MainWindow Mixin Architecture

> MainWindow is composed from 9 mixin classes, each handling a specific domain.
> This is the core architectural pattern of PyPlayer's GUI layer.

---

## Composition

`MainWindow` in `gui/main_window.py` inherits from all 9 mixins:

```python
class MainWindow(
    PlaybackMixin,
    EditingMixin,
    SavingMixin,
    FileManagementMixin,
    MenusMixin,
    ThemesMixin,
    EventsMixin,
    DialogsMixin,
    UIStateMixin,
    Ui_MainWindow,
    QtW.QMainWindow
):
    pass
```

## Mixin Reference

| Mixin | Module | Responsibility |
|-------|--------|---------------|
| `PlaybackMixin` | `gui/mixins/playback.py` | Volume, tracks, rate, navigation |
| `EditingMixin` | `gui/mixins/editing.py` | Trim, crop, edit queue |
| `SavingMixin` | `gui/mixins/saving.py` | Save, export, compress |
| `FileManagementMixin` | `gui/mixins/file_management.py` | Open, cycle, copy, rename |
| `MenusMixin` | `gui/mixins/menus.py` | Context menus, mouse events |
| `ThemesMixin` | `gui/mixins/themes.py` | Theme loading/switching |
| `EventsMixin` | `gui/mixins/events.py` | Qt event handlers |
| `DialogsMixin` | `gui/mixins/dialogs.py` | Dialogs, browse, updates |
| `UIStateMixin` | `gui/mixins/ui_state.py` | Visibility, state, statusbar |

## Signal Connections

All signal/slot connections are wired in `gui/signals.py`, not in individual mixins.
This centralizes the wiring and makes the dependency graph explicit.

## Adding Behavior to a Mixin

1. Add new methods to the appropriate mixin in `gui/mixins/`
2. Import the mixin class in `gui/main_window.py` (already imported)
3. Connect new signals in `gui/signals.py` if needed

## Key Classes Used by Mixins

| Component | Location | Purpose |
|-----------|----------|---------|
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

Related: [[docs/architecture/app-flow]] | [[docs/architecture/package-structure]] | [[docs/features/trim-workflow]] | [[docs/features/save-and-export]]
