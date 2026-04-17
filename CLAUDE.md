# PyPlayer Compressor — Project Hub

> Central operational hub for AI agents working on this codebase.
> For full documentation index, see [[docs/_index]].

---

## Identity

| Field | Value |
|-------|-------|
| Name | PyPlayer Compressor 10MB |
| Fork of | [thisismy-github/pyplayer](https://github.com/thisismy-github/pyplayer) |
| Stack | Python 3.13+ / PyQt5 / VLC (libvlc) / FFmpeg |
| Version | 0.6.0 beta |
| Repo | https://github.com/Piyabordee/pyplayer-compressor-10mb |

---

## Read First

- [[docs/_index]] — Full documentation map
- [[docs/project/overview]] — Project identity and stack
- [[docs/project/repository-map]] — Repo folder guide
- [[README]] — User-facing introduction

---

## Quick Commands

```bash
python run.pyw               # Run app (backward-compatible entry)
python main.pyw              # Run app (legacy entry, thin wrapper)
python -m pyplayer           # Run app (package entry)
python build.py              # Build exe (from packaging/)
pytest tests/ -v             # Run tests (86 tests)
ruff check src/ tests/       # Lint
```

---

## Working Rules

1. **Read before modifying** — mature codebase with established patterns
2. **Preserve existing behavior** — fork's value is in its workflow improvements
3. **Test FFmpeg operations** — editing features depend on external binaries
4. **Respect original author** — this is a fork; maintain compatibility
5. **Use existing helpers** — `gui/helpers.py` (dialogs) and `core/file_ops.py` (file operations) contain useful utilities
6. **Follow Qt patterns** — Signal/slot, proper widget lifecycle
7. **Handle platform differences** — Windows primary; Linux/macOS secondary
8. **Package imports** — new code uses `from pyplayer.core import ...` style

---

## Doc Workflow

When creating or significantly modifying a feature, **automatically** follow this workflow:

### New Feature / Significant Change

1. **Spec + Plan** — `write-plan` creates spec and plan in `docs/superpowers/specs/` and `docs/superpowers/plans/`
2. **Feature doc** — Create `docs/features/<feature-name>.md` with: purpose, flow, key files, config
3. **Design Origin** — Add `## Design Origin` section linking to the spec and plan
4. **Link here** — Add entry to the appropriate section in Documentation Map below
5. **Link related docs** — Add wiki links in `Related:` section to connected docs

### Where to put docs

| Category | Path | When |
|----------|------|------|
| Feature workflow | `docs/features/` | New user-facing behavior |
| Architecture change | `docs/architecture/` | Structural codebase changes |
| Integration detail | `docs/integrations/` | New external dependency usage |
| Build/packaging | `docs/build/` | Build system changes |
| Config/reference | `docs/reference/` | New constants, config options |
| Project-level | `docs/project/` | Known issues, fork changes |

### Doc template

```markdown
# Feature Name
> One-line description

## Overview
## Flow / User Journey
## Key Files
## Configuration (if any)
## Design Origin
- Spec: [[docs/superpowers/specs/YYYY-MM-DD-<name>-design]]
- Plan: [[docs/superpowers/plans/YYYY-MM-DD-<name>]]
---

Related: [[linked-doc-1]] | [[linked-doc-2]]
```

---

## Documentation Map

### Project
- [[docs/project/overview]] — Identity, stack, dependencies, features
- [[docs/project/repository-map]] — Folder guide, legacy vs package layout
- [[docs/project/fork-changes]] — What changed from upstream PyPlayer
- [[docs/project/known-issues]] — Bugs, limitations, TODOs

### Architecture
- [[docs/architecture/app-flow]] — Application startup sequence
- [[docs/architecture/mainwindow-mixins]] — GUI mixin composition (9 mixins)
- [[docs/architecture/package-structure]] — `src/pyplayer/` layout and transition

### Features
- [[docs/features/trim-workflow]] — Quick Trim button behavior
- [[docs/features/save-and-export]] — Save/export/compress paths
- [[docs/features/auto-compress]] — Auto-compress after trim (~10MB)

### Integrations
- [[docs/integrations/ffmpeg-and-ffprobe]] — FFmpeg subprocess, probes
- [[docs/integrations/vlc-backend]] — VLC player backend

### Build & Release
- [[docs/build/packaging-guide]] — PyInstaller + Inno Setup
- [[docs/build/release-process]] — Version bump, tag, GitHub release

### Testing
- [[docs/testing/manual-checklist]] — QA checklist
- [[docs/testing/test-strategy]] — Testing approach and tech debt

### Reference
- [[docs/reference/config-and-paths]] — Config system, path resolution
- [[docs/reference/key-constants]] — VERSION, FFMPEG, THEME_DIR, etc.

---

## Key Warnings

- **Trim/Save/Compress flow** is fragile — see [[docs/features/auto-compress]]
- **Path resolution differs** dev vs compiled — see [[docs/reference/config-and-paths]]
- **PyInstaller 5.x vs 6.x** breaking changes — see [[docs/build/packaging-guide]]
- **Theme path** must use `RESOURCE_BASE` not `CWD` — see [[docs/reference/config-and-paths]]

---

## Related Files

- [[AGENTS]] — Original deep reference (preserved during transition)
- [[README]] — User-facing intro
- [[TESTING_RESULTS]] — Auto-compress test results (2026-03-24)
- [[GitHub_Release]] — Build/release guide with troubleshooting (Thai)
