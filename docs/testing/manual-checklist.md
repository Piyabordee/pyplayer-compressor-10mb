# Manual Testing Checklist

> QA checklist for manual testing before committing and releasing.

---

## Functional Tests

### Video Playback
- [ ] Video playback works (various formats: MP4, AVI, MKV, MOV)
- [ ] Play/Pause works
- [ ] Seek works (click on progress bar, arrow keys)
- [ ] Volume control works
- [ ] Fullscreen works
- [ ] Rate control works (speed up / slow down)

### Trim/Crop Operations
- [ ] Quick Trim button sets START marker
- [ ] END marker follows playback/seek position
- [ ] Trim markers visible on seek bar
- [ ] Save trimmed segment works
- [ ] Cancel trim works
- [ ] Crop mode works
- [ ] Crop borders adjustable

### Audio Editing
- [ ] Audio amplification works
- [ ] Replace audio track works
- [ ] Add audio to image works

### Auto-Compress
- [ ] Auto-compress triggers after trim save (when enabled)
- [ ] Output file size approximately 8.2MB
- [ ] Compressed video plays correctly
- [ ] Cancel during compression works
- [ ] Auto-compress can be disabled in settings
- [ ] Settings persistence across restarts

### File Management
- [ ] Open file via drag & drop
- [ ] Open file via file menu
- [ ] Cycle through files (Next/Previous)
- [ ] Rename file in place
- [ ] Delete file
- [ ] Snapshot capture works

### UI
- [ ] Theme switching works
- [ ] Configuration save/load works
- [ ] Keyboard shortcuts work
- [ ] System tray icon works (Windows)
- [ ] Drag & drop files, folders, subtitles

---

## Before Committing

- Test on primary platform (Windows)
- Verify FFmpeg operations complete
- Check configuration persistence
- Test with various media file types

---

## Pre-Release Testing

See [[docs/build/release-process]] for the full pre-release checklist.

---

Related: [[docs/testing/test-strategy]] | [[docs/project/known-issues]] | [[docs/features/auto-compress]] | [[TESTING_RESULTS]]
