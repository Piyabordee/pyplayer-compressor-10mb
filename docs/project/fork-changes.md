# Fork-Specific Changes

> What PyPlayer Compressor changed from the original [PyPlayer](https://github.com/thisismy-github/pyplayer).
> Repository: https://github.com/Piyabordee/pyplayer-compressor-10mb

---

## 1. Always-Visible Save Button

Save button permanently displayed in the quick actions row.
- Eliminates need to activate trim mode first
- Improves workflow for quick video exports

## 2. Quick Trim Button

Single Trim button replaces separate Start/End buttons (fully implemented):
- Click Trim to set START at current position
- END automatically follows current playback/seek position
- Button displays remaining duration when active
- Click Trim again to cancel trim
- Visual feedback: Triangle markers on seek bar show START (left) and END (right) positions

See [[docs/features/trim-workflow]] for the full flow.

## 3. Auto-Compress After Trim

Automatic video compression after saving trimmed videos:
- Settings checkbox to enable/disable auto-compression (config: `auto_compress_after_trim`)
- Automatically compresses trimmed videos to target ~10MB using FFmpeg
- Progress dialog shows compression status with polling mechanism
- Cleanup of temporary files after compression
- Modeless dialog allows continued use during compression
- Improved error handling and completion callback

See [[docs/features/auto-compress]] for the full flow.

## 4. Save Workflow Improvements

- Option to control auto-opening of files after saving (config: `auto_open_after_save`)

See [[docs/features/save-and-export]] for the full flow.

## 5. Build & Compatibility

- Enhanced compatibility with PyInstaller 5.x and 6.x for path resolution and resource management
- Improved build process with new scripts and resource management

See [[docs/build/packaging-guide]] for details.

## 6. UI Polish

- Text color set to black for dialogs and progress indicators for better readability
- Auto-compress checkbox synchronized with loaded settings
- Improved error handling for theme directory creation

## 7. Repository Restructure (Phase 7)

- Flat layout reorganized into `src/pyplayer/` package with subpackages: `core/`, `gui/`, `widgets/`, `ui/`
- `main.pyw` (531KB) split into ~49 focused modules under 800 lines each
- MainWindow decomposed into 9 mixin classes for maintainability
- Build configs consolidated into `packaging/` directory
- Backward-compatible entry points: `pyplayer.pyw` and `python -m pyplayer`
- Original flat files preserved in repo root for fallback testing

See [[docs/architecture/package-structure]] for the new layout.

---

## Design Origin

Key features were designed via superpowers specs/plans:
- Quick Trim: [[docs/superpowers/specs/2026-03-22-quick-trim-button-design]] | [[docs/superpowers/plans/2026-03-22-quick-trim-button]]
- Auto-Compress: [[docs/superpowers/specs/2026-03-24-auto-compress-after-trim-design]] | [[docs/superpowers/plans/2026-03-24-auto-compress-after-trim]]
- Repo Restructure: [[docs/superpowers/specs/2026-03-28-repo-restructure-design]] | [[docs/superpowers/plans/2026-03-28-repo-restructure]]

---

Related: [[docs/project/overview]] | [[docs/features/trim-workflow]] | [[docs/features/auto-compress]] | [[docs/architecture/package-structure]]
