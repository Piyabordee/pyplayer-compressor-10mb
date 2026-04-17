# Test Strategy

> Testing approach and technical debt for PyPlayer Compressor.

---

## Current Approach

PyPlayer uses a **hybrid testing strategy**: automated unit tests for core modules and manual QA for GUI and integration testing.

### Automated Tests

**86 tests** covering `src/pyplayer/core/` modules:

| Module | Tests | Coverage |
|--------|-------|----------|
| `media_utils.py` | 38 | Pure functions (get_hms, scale, sanitize, etc.) |
| `file_ops.py` | 21 | sanitize, get_unique_path, get_from_PATH |
| `compression.py` | 16 | Bitrate calculation, FFmpeg mocking |
| `ffmpeg.py` | 11 | Subprocess wrappers, process management |

Run: `pytest tests/ -v`

### CI/CD

GitHub Actions runs on push/PR to main:
- **lint** — `ruff check src/ tests/`
- **test** — `pytest tests/ -v --tb=short`

See `.github/workflows/ci.yml`

### Manual QA

See [[docs/testing/manual-checklist]] for the full checklist.

### Test Results

See [[TESTING_RESULTS]] for the auto-compress feature test results (2026-03-24).

---

## Testing Categories

| Category | Status | Notes |
|----------|--------|-------|
| Core utilities | **Automated** | 86 tests in tests/core/ |
| Video playback | Manual only | Various formats, frame rates |
| Trim/crop | Manual only | Edge cases with obscure formats |
| Auto-compress | Partial | Unit tests for compression.py; UI flow manual |
| Config persistence | Manual only | Save/load across restarts |
| Theme switching | Manual only | Visual verification |
| Build/package | Manual only | Clean install test |

---

## Technical Debt

### Auto-Compress Testing Gaps

From [[TESTING_RESULTS]]:

| Test Case | Status |
|-----------|--------|
| Short video compression (5-10s) | Not tested |
| Long video compression (1+ min) | Not tested |
| Auto-compress disabled | Not tested |
| FFmpeg missing scenario | Unit tested |
| Cancel during compression | Needs manual test (QThread implemented) |
| Settings persistence | Not tested |

### Remaining Improvements

1. ~~Add automated tests for `core/` modules~~ **Done (86 tests)**
2. ~~Add QThread for compression~~ **Done (workers/compression_worker.py)**
3. Implement proper thread synchronization instead of polling
4. Add file validation after compression
5. Add progress indication during save wait phase
6. Handle edge cases (empty files, disk full, network drives)
7. Add GUI tests (pytest-qt) for widget behavior
8. Add integration tests for FFmpeg operations with real files

---

## Debugging Tips

- Logs written to `pyplayer.log` in application directory
- Use `--debug` flag when running from command line
- Set `logging.DEBUG` level in `qtstart.py`
- For build issues, run exe from command prompt to see errors

---

Related: [[docs/testing/manual-checklist]] | [[docs/project/known-issues]] | [[docs/features/auto-compress]] | [[TESTING_RESULTS]]
