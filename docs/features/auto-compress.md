# Auto-Compress After Trim

> Automatic video compression to ~10MB after saving trimmed videos.
> A core fork-specific feature for easy sharing on Discord (free tier 10MB limit).

---

## Overview

When enabled, automatically compresses trimmed videos to approximately 8.2MB using FFmpeg with smart bitrate calculation based on target file size.

## Configuration

| Config Key | Default | Location |
|------------|---------|----------|
| `auto_compress_after_trim` | ON | Settings dialog → checkbox |

- Loaded in `config.py:loadConfig()`
- Saved in `config.py:saveConfig()`
- Checkbox synchronized with loaded settings on startup

## Flow

```
1. User trims and saves a video
   → See [[docs/features/save-and-export]]
2. EditingMixin detects auto_compress_after_trim is enabled
3. CompressionWorker created in a QThread (workers/compression_worker.py)
4. compress_video() called from core/compression.py
   → Calculates target bitrate based on video duration
   → Runs FFmpeg compression subprocess
5. CompressProgressDialog shows progress
   → Modeless dialog with cancel support
   → Progress updates via Qt signals (no UI freezing)
6. On completion:
   → Compressed file replaces or follows the trimmed output
   → Temporary files cleaned up
7. On error:
   → Error dialog displayed
   → Temp file cleanup attempted
```

## Key Files

| File | Role |
|------|------|
| `core/compression.py` | `compress_video()` — bitrate calculation, FFmpeg compression |
| `workers/compression_worker.py` | `CompressionWorker` — QThread worker with progress/finished signals |
| `gui/mixins/editing.py` | `_compress_with_progress()` — creates QThread + worker |
| `gui/progress.py` | `CompressProgressDialog` — modeless progress UI with cancel signal |
| `config.py` | Load/save `auto_compress_after_trim` setting |
| `core/ffmpeg.py` | FFmpeg subprocess wrapper |

## Compression Algorithm

1. Get video duration from source file
2. Calculate target bitrate: `target_size_bits / duration_seconds`
3. Subtract audio bitrate estimate from available budget
4. Pass calculated video bitrate to FFmpeg `-b:v` flag
5. Target output: ~8.2MB (fits under Discord 10MB limit)

## Technical Debt

1. ~~**UI Thread Blocking**~~ — **Fixed.** Compression runs in QThread via `workers/compression_worker.py`
2. **Polling** — Uses polling to detect when async save completes
3. **Cancel** — Cancel button emits signal to worker; UI no longer freezes
4. **Validation** — No file validation after compression
5. **Edge cases** — No handling for empty files, disk full, network drives

See [[docs/project/known-issues]] for the full list.

---

## Design Origin

- Spec: [[docs/superpowers/specs/2026-03-24-auto-compress-after-trim-design]]
- Plan: [[docs/superpowers/plans/2026-03-24-auto-compress-after-trim]]

---

Related: [[docs/features/save-and-export]] | [[docs/features/trim-workflow]] | [[docs/integrations/ffmpeg-and-ffprobe]] | [[docs/project/known-issues]] | [[TESTING_RESULTS]]
