# FFmpeg and FFprobe Integration

> How PyPlayer uses FFmpeg for video editing and media analysis.

---

## Overview

FFmpeg is the backbone of all editing operations in PyPlayer. FFprobe is used for media file analysis. Both are external binaries that must be present on the system.

## External Binary Locations

```
executable/include/ffmpeg-windows/
├── ffmpeg.exe            # 355KB
├── ffprobe.exe           # 192KB
└── *.dll                 # avcodec-59, avformat-59, etc.
```

Path resolution is handled in `constants.py` via `FFMPEG` constant.

## Key Functions

| Function | Module | Purpose |
|----------|--------|---------|
| `run_ffmpeg()` | `core/ffmpeg.py` | FFmpeg subprocess wrapper |
| `probe_media()` | `core/probe.py` | FFprobe media analysis |
| `compress_video()` | `core/compression.py` | Video compression with bitrate calculation |

## FFmpeg Operations

PyPlayer uses FFmpeg for:
- **Trim** — Extract video segment with `-ss` and `-to` flags
- **Crop** — Crop video with crop filter
- **Concatenate** — Join multiple video files
- **Fade effects** — Audio/video fade in/out
- **Rotate/Flip** — Transform video orientation
- **Audio editing** — Amplify, replace tracks, add audio to images
- **Compression** — Reduce file size with calculated bitrate
- **Format conversion** — Convert between MP4, MP3, WAV, AAC, GIF, etc.

## Subprocess Handling

- **Windows:** Uses `subprocess.STARTUPINFO` for hidden console window
- **Linux/macOS:** Uses `shlex.split()` for command parsing
- All FFmpeg operations run through `run_ffmpeg()` wrapper in `core/ffmpeg.py`

## Compression Algorithm

See [[docs/features/auto-compress]] for the bitrate calculation details.

## Platform Differences

| Platform | FFmpeg Path | Command Parsing |
|----------|-------------|-----------------|
| Windows (dev) | `executable/include/ffmpeg-windows/ffmpeg.exe` | Direct string |
| Windows (compiled) | `_internal/plugins/ffmpeg/ffmpeg.exe` | Direct string |
| Linux/macOS | System FFmpeg or bundled | `shlex.split()` |

## Troubleshooting

- If FFmpeg is not detected, check `constants.py:verify_ffmpeg()`
- Path resolution differs between dev and compiled modes — see [[docs/reference/config-and-paths]]
- Some formats require specific FFmpeg codecs — see [[docs/project/known-issues]]

---

Related: [[docs/features/auto-compress]] | [[docs/features/trim-workflow]] | [[docs/reference/config-and-paths]] | [[docs/reference/key-constants]]
