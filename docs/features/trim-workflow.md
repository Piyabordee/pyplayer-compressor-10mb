# Quick Trim Workflow

> How the Quick Trim button works — a core fork-specific feature.

---

## Overview

The Quick Trim button replaces the original separate Start/End buttons with a single-click workflow.

## User Flow

```
1. User opens a video file
2. User seeks to the desired START position
3. User clicks Trim button
   → START marker set at current position
   → Triangle marker appears on seek bar (left)
   → Button shows remaining duration
4. User seeks/plays to the desired END position
   → END marker automatically follows current position
   → Triangle marker appears on seek bar (right)
5. User clicks Save
   → Trimmed segment exported via FFmpeg
   → If auto-compress enabled: compression starts automatically
6. User clicks Trim again to cancel (if needed)
```

## Visual Feedback

- **Left triangle marker** on seek bar = START position
- **Right triangle marker** on seek bar = END position (follows playback/seek)
- **Button text** shows remaining duration when trim is active

## Key Files

| File | Role |
|------|------|
| `gui/mixins/editing.py` | Trim logic, START/END management |
| `widgets/video_slider.py` | Seek bar markers, visual feedback |
| `gui/mixins/saving.py` | Save/export of trimmed segment |
| `gui/signals.py` | Signal connections for trim events |

## State Management

Trim state is tracked on the `gui` instance:
- `gui.trim_start` — START position in milliseconds
- `gui.trim_end` — END position in milliseconds
- Trim mode is toggled by repeated clicks of the Trim button

## Related Features

- After saving, auto-compress may trigger → [[docs/features/auto-compress]]
- Save/export path details → [[docs/features/save-and-export]]

---

## Design Origin

- Spec: [[docs/superpowers/specs/2026-03-22-quick-trim-button-design]]
- Plan: [[docs/superpowers/plans/2026-03-22-quick-trim-button]]

---

Related: [[docs/features/save-and-export]] | [[docs/features/auto-compress]] | [[docs/architecture/mainwindow-mixins]] | [[docs/integrations/ffmpeg-and-ffprobe]]
