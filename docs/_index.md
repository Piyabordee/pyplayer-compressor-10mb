# PyPlayer Compressor — Documentation Index

> Navigation hub for all project documentation.
> For the operational hub that Claude Code reads, see [[CLAUDE]].

---

## Project

- [[docs/project/overview]] — Project identity, stack, dependencies, core features
- [[docs/project/repository-map]] — Repo folder guide, legacy vs package layout
- [[docs/project/fork-changes]] — What changed from upstream PyPlayer
- [[docs/project/known-issues]] — Known bugs, limitations, and TODOs

## Architecture

- [[docs/architecture/app-flow]] — Application startup sequence
- [[docs/architecture/mainwindow-mixins]] — GUI mixin composition pattern
- [[docs/architecture/package-structure]] — `src/pyplayer/` layout and transition notes

## Features

- [[docs/features/trim-workflow]] — Quick Trim button behavior and flow
- [[docs/features/save-and-export]] — Save/export/compress paths
- [[docs/features/auto-compress]] — Auto-compress after trim feature

## Integrations

- [[docs/integrations/ffmpeg-and-ffprobe]] — FFmpeg subprocess wrappers, probes, compression
- [[docs/integrations/vlc-backend]] — VLC player backend, QVideoPlayer, QVideoPlayerLabel

## Build & Release

- [[docs/build/packaging-guide]] — PyInstaller + Inno Setup build instructions
- [[docs/build/release-process]] — Version bump, tagging, GitHub release checklist

## Testing

- [[docs/testing/manual-checklist]] — QA checklist for manual testing
- [[docs/testing/test-strategy]] — Testing approach and technical debt

## Reference

- [[docs/reference/config-and-paths]] — Config system, path resolution, `IS_COMPILED` handling
- [[docs/reference/key-constants]] — VERSION, FFMPEG, THEME_DIR, and other globals

## Historical

- [[AGENTS]] — Original deep reference (preserved during transition)
- [[TESTING_RESULTS]] — Auto-compress feature test results (2026-03-24)
- [[GitHub_Release]] — Build/release guide with troubleshooting (Thai)
- [[README]] — User-facing project introduction
