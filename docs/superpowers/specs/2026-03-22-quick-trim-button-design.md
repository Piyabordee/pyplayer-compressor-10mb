# Quick Trim Button Design

**Date:** 2026-03-22
**Status:** Approved
**Author:** Claude (with user input)

---

## Overview

Replace the current two-button trim system (`Start` + `End`) with a single `Trim` button that automatically sets the start point at the current position and the end point at the video's end.

### User Problem

The current trim workflow requires two separate actions:
1. Click `Start` to set trim start
2. Click `End` to set trim end

This is cumbersome for the common use case of trimming from a specific point to the video's end.

### Solution

A single toggle button that:
- **First click:** Sets start = current position, end = video end
- **Second click:** Cancels trim, returns to normal playback
- **Visual feedback:** Shows remaining duration (e.g., "1:23.45")

---

## Requirements

### Functional Requirements

| ID | Requirement |
|----|-------------|
| R1 | Single `Trim` button replaces `Start` and `End` buttons |
| R2 | Clicking `Trim` sets start at current position |
| R3 | End position is automatically set to video end |
| R4 | Button displays remaining duration when active |
| R5 | Clicking again cancels trim (toggle behavior) |
| R6 | Right-click menu shows trim info and options |
| R7 | Save function uses trim state when button is active |

### Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| N1 | Maintain existing slider visual feedback (rainbow marker at start) |
| N2 | Preserve right-click menu functionality |
| N3 | Keep compatibility with fade modes |
| N4 | No new config settings required |

---

## Design

### UI Changes

**Files to modify:**
1. `bin/window_pyplayer.ui` - Qt Designer file
2. `bin/window_pyplayer.py` - Generated from .ui
3. `main.pyw` - Layout and logic

**Button Properties:**
```
Name: buttonTrim
Text: "Trim"
Checkable: True
MinimumWidth: 44
MaximumWidth: 95
FocusPolicy: NoFocus
```

**Layout Change (main.pyw:1717-1718):**
```python
# Before:
self.buttonTrimStart.setVisible(primary_visible)
self.buttonTrimEnd.setVisible(primary_visible)

# After:
self.buttonTrim.setVisible(primary_visible)
```

### Behavior

#### State Diagram

```
          [Inactive]
               |
               | Click
               v
          [Active]
          /     \
    Play      End of video
    to end    → Auto pause
          \     /
           | Click
           v
          [Inactive]
```

#### Button Text States

| State | Text |
|-------|------|
| Inactive | "Trim" |
| Active (< 1 hr remaining) | "M:SS.ms" |
| Active (≥ 1 hr remaining) | "H:MM:SS" |

### Logic Implementation

**New Function (`main.pyw`):**

```python
def set_trim(self, enabled: bool):
    ''' Toggle trim mode - set start at current, end at video end.

    When enabled:
        - Start position = current playback position
        - End position = video end (automatic)
        - Button displays remaining duration
        - Slider clamps at minimum (start position)

    When disabled:
        - Reset to full video playback
        - Button text returns to "Trim"
    '''
    if not self.video:       return self.buttonTrim.setChecked(False)
    if self.is_static_image: return self.buttonTrim.setChecked(False)

    self.buttonTrim.setChecked(enabled)
    self.sliderProgress.clamp_minimum = enabled
    self.sliderProgress.clamp_maximum = False  # end is always video end

    if enabled:
        self.minimum = get_ui_frame()
        self.maximum = self.sliderProgress.maximum()

        # Calculate and display remaining duration
        remaining_ms = (self.maximum - self.minimum) * (1000 / self.fps)
        h, m, s, ms = get_hms(remaining_ms)
        if remaining_ms < 3600:
            self.buttonTrim.setText(f'{m}:{s:02}.{ms:02}')
        else:
            self.buttonTrim.setText(f'{h}:{m:02}:{s:02}')
    else:
        self.minimum = self.sliderProgress.minimum()
        self.maximum = self.sliderProgress.maximum()
        self.buttonTrim.setText('Trim')
```

**Signal Connection (`qtstart.py`):**

```python
gui.buttonTrim.clicked.connect(lambda: gui.set_trim(not gui.buttonTrim.isChecked()))
```

### Context Menu

Right-click menu should display:

| Item | Description |
|------|-------------|
| Start position | Shows current start timestamp |
| Remaining duration | Shows calculated remaining time |
| Set end to current | Allows manual end adjustment (optional) |
| Fade mode options | Existing fade functionality |

### Save Function

**Change in `main.pyw:4630-4631`:**

```python
# Before:
if self.buttonTrimStart.isChecked(): operations['trim start'] = True
if self.buttonTrimEnd.isChecked():   operations['trim end'] = True

# After:
if self.buttonTrim.isChecked(): operations['trim start'] = True
# End is always implied at video end
```

### Slider Visual Feedback

- Keep rainbow marker at `minimum` (start position)
- No marker needed at `maximum` (it's always at video end)
- Existing paint logic in `widgets.py:QVideoSlider.paintEvent` mostly unchanged

---

## Files Summary

| File | Changes |
|------|---------|
| `bin/window_pyplayer.ui` | Replace Start/End buttons with Trim button |
| `bin/window_pyplayer.py` | Regenerated from .ui |
| `main.pyw` | Layout logic, new `set_trim()` function, save logic update |
| `qtstart.py` | Signal connection for new button |
| `widgets.py` | Minor: remove `clamp_maximum` visual if needed |

---

## Edge Cases

| Case | Behavior |
|------|----------|
| No media loaded | Button disabled/unchecked |
| Static image | Button disabled/unchecked |
| Start position > end | Validation prevents this (end = video end always) |
| Click near video end | Remaining duration shows small value |
| Already at video start | Trim has no effect (duration = full video) |

---

## Testing Checklist

- [ ] Button appears correctly in UI
- [ ] Click sets start at current position
- [ ] End is at video end (verified by save output)
- [ ] Button displays correct remaining duration
- [ ] Click again cancels trim
- [ ] Right-click menu works
- [ ] Save produces correctly trimmed video
- [ ] Fade modes still work
- [ ] Keyboard shortcuts (if added) work
- [ ] Layout responsive on window resize

---

## Future Enhancements (Out of Scope)

- Keyboard shortcut (e.g., `Ctrl+T`)
- Visual indicator for "trim from beginning" (reverse case)
- Multiple trim ranges support
- Trim preview mode

---

## Implementation Notes

1. **Run `convert_ui_to_py.py`** after editing `window_pyplayer.ui`
2. **Test with various video formats** to ensure FFmpeg operations work
3. **Check theme compatibility** - button should work with all themes
4. **Preserve existing fade mode behavior** - don't break `actionFadeIn`, `actionFadeOut`

---

*End of Design Document*
