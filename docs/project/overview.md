# Project Overview

> PyPlayer Compressor 10MB — a modified fork of [PyPlayer](https://github.com/thisismy-github/pyplayer)

---

## Identity

| Field | Value |
|-------|-------|
| Name | PyPlayer Compressor 10MB |
| Type | Desktop GUI Application (Video Player/Editor) |
| Repo | https://github.com/Piyabordee/pyplayer-compressor-10mb |
| Version | 0.6.0 beta |
| Original | [thisismy-github/pyplayer](https://github.com/thisismy-github/pyplayer) |
| Credits | All credit to `thisismy-github` for creating PyPlayer |

## Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.13+ |
| UI Framework | PyQt5 |
| Media Backend | VLC Media Player (libvlc) + FFmpeg for editing |
| Platform Focus | Windows (primary), Linux/macOS support |

## Core Features

- **Video Editing:** Trim, crop, concatenate, fade effects, rotate/flip
- **Audio Editing:** Amplify, replace tracks, add audio to images
- **Format Support:** MP4, MP3, WAV, AAC, GIF, and more
- **Quick Actions:** Instant file cycling, snapshots, rename/delete in place
- **Drag & Drop:** Files, folders, or subtitles
- **Custom Themes:** Qt Stylesheet-based theming system

## Fork-Specific Features

- Always-visible Save button for faster video export
- Quick Trim button (single-click trim workflow)
- Auto-compress after trim (target ~10MB for Discord)
- Auto-open after save (configurable)

See [[docs/project/fork-changes]] for the full change log.

## Dependencies

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

## Key Documentation Links

- **PyQt5:** https://doc.qt.io/qtforpython/
- **python-vlc:** https://www.olivieraubert.net/vlc/python-ctypes/
- **FFmpeg:** https://ffmpeg.org/documentation.html

---

Related: [[docs/project/repository-map]] | [[docs/project/fork-changes]] | [[docs/architecture/app-flow]] | [[README]]
