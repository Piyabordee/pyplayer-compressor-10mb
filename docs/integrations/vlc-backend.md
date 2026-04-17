# VLC Backend

> How PyPlayer integrates VLC for video playback.

---

## Overview

PyPlayer uses `python-vlc` bindings to control VLC Media Player (libvlc) for all video playback. Two player backends are available.

## External Binary Locations

```
executable/include/vlc-windows/
├── libvlc.dll            # 191KB
├── libvlccore.dll        # 2.8MB
└── plugins/              # VLC codec plugins
```

## Player Backends

| Backend | Module | Description |
|---------|--------|-------------|
| `QVideoPlayer` | `widgets/player_widget.py` | VLC media player widget wrapper (primary) |
| `QVideoPlayerLabel` | `widgets/player_label.py` | VLC label-based player backend |
| Player backends | `widgets/player_backend.py` | VLC/Qt backend abstraction |

## Key Widgets

| Widget | Module | Purpose |
|--------|--------|---------|
| `QVideoPlayer` | `widgets/player_widget.py` | Main video player widget |
| `QVideoSlider` | `widgets/video_slider.py` | Custom seek bar with hover preview |
| `QVideoList` | `widgets/video_list.py` | Video file list management |

## VLC Integration

- Uses `python-vlc` (>=3.0.18122) for libvlc bindings
- Player embedded in Qt widget via `QFrame` or `QLabel`
- VLC plugins required for codec support
- Frame-seeking near video end occasionally unreliable (libvlc limitation)

## Path Resolution (Compiled Mode)

In `hook.py`:
```python
if IS_FROZEN:
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 6.x
        INTERNAL_DIR = sys._MEIPASS
        VLC_PATH = os.path.join(INTERNAL_DIR, 'plugins', 'vlc')
    else:
        # PyInstaller 5.x
        CWD = os.path.dirname(sys.argv[0])
        VLC_PATH = os.path.join(CWD, 'plugins', 'vlc')
```

See [[docs/reference/config-and-paths]] for full path resolution details.

## Known Limitations

- Frame-seeking near video end occasionally unreliable (libvlc limitation)
- High-FPS videos (>60fps) may have stability issues
- See [[docs/project/known-issues]] for the full list

---

Related: [[docs/integrations/ffmpeg-and-ffprobe]] | [[docs/architecture/mainwindow-mixins]] | [[docs/reference/config-and-paths]] | [[docs/project/known-issues]]
