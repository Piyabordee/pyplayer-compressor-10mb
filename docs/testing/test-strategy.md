# Test Strategy

> Testing approach and technical debt for PyPlayer Compressor.

---

## Current Approach

PyPlayer Compressor currently relies on **manual testing**. There is no automated test suite integrated into CI/CD.

### Manual QA

See [[docs/testing/manual-checklist]] for the full checklist.

### Test Results

See [[TESTING_RESULTS]] for the auto-compress feature test results (2026-03-24).

---

## Testing Categories

| Category | Status | Notes |
|----------|--------|-------|
| Video playback | Manual only | Various formats, frame rates |
| Trim/crop | Manual only | Edge cases with obscure formats |
| Audio editing | Manual only | Amplify, replace, add |
| Auto-compress | Manual only | See [[TESTING_RESULTS]] |
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
| FFmpeg missing scenario | Not tested |
| Cancel during compression | Partial (UI blocks) |
| Settings persistence | Not tested |

### Future Improvements

1. Add automated tests for `core/` modules (no Qt dependency)
2. Add QThread for compression to prevent UI freezing
3. Implement proper thread synchronization instead of polling
4. Add file validation after compression
5. Add progress indication during save wait phase
6. Handle edge cases (empty files, disk full, network drives)

---

## Debugging Tips

- Logs written to `pyplayer.log` in application directory
- Use `--debug` flag when running from command line
- Set `logging.DEBUG` level in `qtstart.py`
- For build issues, run exe from command prompt to see errors

---

Related: [[docs/testing/manual-checklist]] | [[docs/project/known-issues]] | [[docs/features/auto-compress]] | [[TESTING_RESULTS]]
