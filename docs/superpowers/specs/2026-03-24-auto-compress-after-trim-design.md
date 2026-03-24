# Auto-Compress After Trim Feature Design

**Date:** 2026-03-24
**Status:** Approved
**Author:** Claude + User

## Overview

Integrate automatic video compression for Discord into PyPlayer's trim workflow. When a user saves a trimmed video, the system will automatically compress it to approximately 8.2MB to fit within Discord's 10MB upload limit for free tier users.

## Requirements

### Functional Requirements
- **FR1:** Automatically compress trimmed videos when saving
- **FR2:** Target output size of ~8.2MB (with safety margin for Discord's 10MB limit)
- **FR3:** Use smart bitrate calculation based on video duration
- **FR4:** Show progress dialog during compression
- **FR5:** Allow users to toggle the feature on/off via settings
- **FR6:** Default to ON when first introduced
- **FR7:** Append `_compressed` suffix to output filenames

### Non-Functional Requirements
- **NFR1:** Compression must not freeze the UI
- **NFR2:** All errors must be gracefully handled with user-friendly messages
- **NFR3:** Temporary files must be cleaned up on failure
- **NFR4:** Progress must be cancelable by the user

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      PyPlayer                            │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐      ┌──────────────┐                 │
│  │ Trim Module  │─────▶│ Compression  │                 │
│  │ (existing)   │      │   Module     │                 │
│  └──────────────┘      │   (NEW)      │                 │
│         │              └──────┬───────┘                 │
│         │                     │                         │
│         v                     v                         │
│  ┌──────────────────────────────────────┐               │
│  │        Settings (config.ini)         │               │
│  │  auto_compress_after_trim = true     │               │
│  └──────────────────────────────────────┘               │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. New File: `compression.py`

```python
# constants
TARGET_FILESIZE_MB = 8.2
AUDIO_BITRATE_KBPS = 128
MIN_VIDEO_BITRATE_KBPS = 64

def compress_video(
    ffmpeg_path: str,
    ffprobe_path: str,
    input_path: str,
    output_path: str,
    progress_callback: callable = None
) -> tuple[bool, str]:
    """
    Compress video to ~8.2MB for Discord upload.

    Returns: (success, error_message)
    """
```

**Responsibilities:**
- Calculate video bitrate from duration using formula:
  ```
  video_bitrate = (TARGET_FILESIZE_MB × 8 × 1024) / duration - AUDIO_BITRATE_KBPS
  ```
- Execute FFmpeg compression command
- Parse FFmpeg output for progress updates
- Return success/failure status

### 2. Modify: `main.pyw`

**2a. New method: `_compress_with_progress()`**
```python
def _compress_with_progress(self, input_path: str, output_path: str) -> bool:
    """Show progress dialog and compress video. Returns True on success."""
```

**2b. Modify `save_as()` method (around line 6207):**
```python
def save_as(self, noun='media', filter=None, valid_extensions=None, ext_hint=None):
    # ... existing save dialog code ...

    # NEW: Check if auto-compress is enabled
    if config.cfg.auto_compress_after_trim and self._is_trimmed_media():
        base, ext = os.path.splitext(output_path)
        compressed_path = f"{base}_compressed{ext}"

        success = self._compress_with_progress(
            input_path=temp_output,
            output_path=compressed_path
        )

        if not success:
            return  # Abort on failure

        output_path = compressed_path

    # ... continue with save ...
```

**2c. New class: `CompressProgressDialog`**
```python
class CompressProgressDialog(QtW.QDialog):
    """Shows compression progress with percentage and cancel button."""

    def __init__(self, parent, input_path):
        self.label = QtW.QLabel(f"Compressing for Discord...\n\n{os.path.basename(input_path)}")
        self.progressBar = QtW.QProgressBar()
        self.btnCancel = QtW.QPushButton("Cancel")
        self.process = None

    def update_progress(self, percent: int):
        self.progressBar.setValue(percent)
```

### 3. Modify: Settings Dialog

Add checkbox in `dialog_settings`:

```python
self.checkAutoCompress = QtW.QCheckBox("Auto-compress trimmed videos for Discord")
self.checkAutoCompress.setToolTip(
    "Automatically compress trimmed videos to ~8.2MB for Discord upload.\n"
    "Output will be saved as {filename}_compressed.mp4"
)
self.checkAutoCompress.setChecked(config.cfg.auto_compress_after_trim)
self.checkAutoCompress.toggled.connect(self._on_auto_compress_toggled)
```

### 4. Modify: `config.ini`

Add new configuration option:
```ini
[General]
auto_compress_after_trim = true
```

## Data Flow

```
1. User sets trim points (start/end)
         │
         v
2. User exits trim mode
         │
         v
3. User clicks "Save As" button
         │
         ├──▶ Show file save dialog
         │    └──▶ User selects: "C:\Videos\myclip.mp4"
         │
         v
4. PyPlayer creates trimmed version (temporary)
         │
         ├──▶ FFmpeg trim: ffmpeg -i input -ss start -to end temp_trim.mp4
         │
         v
5. Check config.cfg.auto_compress_after_trim
         │
         ├──▶ FALSE ──▶ Save temp_trim.mp4 → myclip.mp4 → DONE
         │
         ├──▶ TRUE ──▶ Continue below
         │
         v
6. Get video duration
         │
         ├──▶ Use FFprobe: ffprobe -i temp_trim.mp4 -show_entries format=duration
         │
         v
7. Calculate target bitrate
         │
         ├──▶ formula: video_bitrate = (8.2 × 8 × 1024) / duration - 128
         │
         v
8. Show CompressProgressDialog
         │
         v
9. Execute FFmpeg compression
         │
         ├──▶ ffmpeg -i temp_trim.mp4
         │         -c:v libx264 -b:v {video_bitrate}k
         │         -preset medium -vsync 0
         │         -c:a aac -b:a 128k
         │         myclip_compressed.mp4
         │
         v
10. SUCCESS → Save myclip_compressed.mp4 → DONE
    FAILURE → Show error → Abort
```

## Error Handling

### Scenario 1: FFmpeg/FFprobe Not Available
**Detection:** `constants.verify_ffmpeg()` returns empty string
**Action:** Show warning dialog with option to go to settings or cancel
**Result:** Abort operation, don't save file

### Scenario 2: Duration Detection Failed
**Detection:** FFprobe command fails or returns invalid data
**Action:** Log error, show dialog with instructions
**Result:** Abort, delete temp files

### Scenario 3: FFmpeg Compression Failed
**Detection:** FFmpeg returns non-zero exit code
**Action:** Show error dialog with error message
**Result:** Abort, delete temp files, log full error

### Scenario 4: User Cancels During Compression
**Detection:** User clicks Cancel button in progress dialog
**Action:** Send SIGTERM to FFmpeg process
**Result:** Delete partial output file, return to trim mode

### Scenario 5: Disk Full / Write Permission Error
**Detection:** File write exception
**Action:** Show error dialog explaining disk space issue
**Result:** Abort, cleanup temp files

## FFmpeg Command Reference

**Compression command:**
```bash
ffmpeg -y -i "{input}" \
       -c:v libx264 \
       -b:v {video_bitrate}k \
       -preset medium \
       -vsync 0 \
       -c:a aac \
       -b:a 128k \
       "{output}"
```

**Duration detection:**
```bash
ffprobe -v quiet -i "{input}" -show_entries format=duration -of csv=p=0
```

## File Naming Convention

- Input: `video.mp4`
- Trimmed output: `video_trimmed_compressed.mp4`
- Pattern: `{original_name}_trimmed_compressed.{ext}`

## Testing Requirements

### Basic Functionality
| Test Case | Expected Result |
|-----------|-----------------|
| Trim 10s video → Save | Creates `_compressed.mp4` ~8MB |
| Trim 60s video → Save | Creates `_compressed.mp4` ~8MB (lower bitrate) |
| Trim 5s video → Save | Creates `_compressed.mp4` ~8MB (higher bitrate) |
| Disable auto-compress → Save | Creates normal trimmed file |

### Edge Cases
| Test Case | Expected Result |
|-----------|-----------------|
| Very short video (<1s) | Works with reasonable bitrate |
| Very long video (>10 min) | Bitrate drops near minimum |
| Video with no audio | Compresses with video-only settings |
| 4K video | Scales down bitrate to fit 8.2MB |

### Error Scenarios
| Test Case | Expected Result |
|-----------|-----------------|
| FFmpeg missing | Show warning, abort gracefully |
| Invalid video file | Detect early, show error |
| Disk full during compression | Cleanup, show error |
| User cancels mid-compression | Kill FFmpeg, cleanup |

## Success Criteria

- [ ] Compressed file ≤ 8.2MB (allow small margin for container overhead)
- [ ] Audio quality maintained at 128kbps AAC
- [ ] Video plays correctly on Discord after upload
- [ ] No file corruption even when process interrupted
- [ ] Progress dialog responsive - doesn't freeze UI
- [ ] All error scenarios handled gracefully
- [ ] Settings toggle persists across sessions

## Implementation Order

1. Create `compression.py` module with core compression logic
2. Add `auto_compress_after_trim` to `config.ini`
3. Add checkbox in settings dialog
4. Create `CompressProgressDialog` class
5. Add `_compress_with_progress()` method to `main.pyw`
6. Integrate compression into `save_as()` workflow
7. Add error handling dialogs
8. Test with various video lengths
9. Test error scenarios

## References

- Source compression logic: https://github.com/Piyabordee/discord-video-compressor
- Discord file limits: 10MB for free tier, 8.2MB target for safety margin
- FFmpeg libx264 documentation: https://trac.ffmpeg.org/wiki/Encode/H.264
