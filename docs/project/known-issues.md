# Known Issues and TODOs

> Bugs, limitations, and planned improvements.

---

## High Priority TODOs

From `main.pyw`:
- DPI/scaling support
- Further polish cropping feature
- Stability for videos >60fps
- Trimming support for obscure formats (3gp, ogv, mpg)
- Filetype associations

## Medium Priority

- System tray menu on Linux
- High-precision progress bar on non-1x speeds
- Resize-snapping on Linux

## Known Limitations

- Frame-seeking near video end occasionally unreliable (libvlc limitation)
- Concatenated videos may have missing frames between clips
- Some formats require specific FFmpeg codecs

## Auto-Compress Technical Debt

From [[TESTING_RESULTS]]:
1. UI Thread Blocking — Compression runs on the main thread, causing UI freeze. **Future: Move to QThread.**
2. File Size Polling — Trim save integration uses polling to detect async save completion. Not production-robust.
3. Cancel Functionality — Cancel button terminates FFmpeg, but UI remains frozen during compression.
4. Add file validation after compression
5. Handle edge cases (empty files, disk full, network drives)

---

Related: [[docs/features/auto-compress]] | [[docs/features/trim-workflow]] | [[docs/testing/test-strategy]] | [[TESTING_RESULTS]]
