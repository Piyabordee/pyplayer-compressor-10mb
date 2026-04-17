# Save and Export

> How PyPlayer saves and exports edited video files.

---

## Save Paths

Save is always accessible via the always-visible Save button (fork change).

### Save Flow

```
1. User has a video loaded and optionally a trim range active
2. User clicks Save
3. If trim range is active:
   → Export trimmed segment via FFmpeg
   → Temporary file created
   → If auto-compress enabled: compress temporary file
   → Final file placed in output location
4. If no trim range:
   → Save current edits (crop, effects, etc.)
5. If auto_open_after_save is enabled:
   → Open the saved file automatically
```

## Configuration Options

| Config Key | Default | Purpose |
|------------|---------|---------|
| `auto_compress_after_trim` | ON | Auto-compress trimmed videos to ~10MB |
| `auto_open_after_save` | Configurable | Auto-open file after saving |

## Key Files

| File | Role |
|------|------|
| `gui/mixins/saving.py` | Save/export logic, integration with compression |
| `gui/mixins/editing.py` | Trim range state (START/END) |
| `core/ffmpeg.py` | FFmpeg subprocess wrapper for export |
| `core/compression.py` | Video compression after save |
| `core/probe.py` | FFprobe analysis of source file |
| `gui/progress.py` | Progress dialogs during save/compress |

## Save Behavior

- Save button is always visible (fork change from original)
- Export uses FFmpeg for all video operations
- Trim range uses `-ss` and `-to` FFmpeg flags for segment extraction
- Temporary files may be created during the save process
- Error handling includes FFmpeg failure and disk space checks

## Fork Changes from Original

1. **Always-visible Save button** — No need to activate trim mode first
2. **Auto-compress integration** — Optional compression after save
3. **Auto-open option** — Configurable auto-opening of saved files

---

## Design Origin

Auto-compress integration designed in:
- Spec: [[docs/superpowers/specs/2026-03-24-auto-compress-after-trim-design]]
- Plan: [[docs/superpowers/plans/2026-03-24-auto-compress-after-trim]]

---

Related: [[docs/features/trim-workflow]] | [[docs/features/auto-compress]] | [[docs/integrations/ffmpeg-and-ffprobe]] | [[docs/architecture/mainwindow-mixins]]
