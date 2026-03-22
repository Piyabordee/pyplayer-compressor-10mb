# Quick Trim Button Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two-button trim system (Start/End) with a single Trim button that sets start at current position and end at video end automatically.

**Architecture:**
1. Remove `buttonTrimStart` and `buttonTrimEnd` from UI
2. Add new `buttonTrim` with toggle behavior
3. New `set_trim()` function handles start=end logic
4. Update save logic to use new button state

**Tech Stack:**
- PyQt5 (UI Framework)
- Python 3.13+
- Qt Designer (.ui files)
- Existing codebase patterns (widgets.py, main.pyw, qtstart.py)

**Spec Reference:** `docs/superpowers/specs/2026-03-22-quick-trim-button-design.md`

---

## Chunk 1: UI Changes (Qt Designer)

### Task 1.1: Edit window_pyplayer.ui to replace trim buttons

**Files:**
- Modify: `bin/window_pyplayer.ui`

- [ ] **Step 1: Backup the original .ui file**

```bash
cp bin/window_pyplayer.ui bin/window_pyplayer.ui.backup
```

- [ ] **Step 2: Remove buttonTrimStart definition**

Find and delete these lines (~lines 431-438):
```xml
<widget class="QPushButton" name="buttonTrimStart">
 <property name="minimumSize">
  <size>
   <width>44</width>
   <height>18</height>
  </size>
 </property>
 <property name="maximumSize">
  <size>
   <width>95</width>
   <height>16777215</height>
  </size>
 </property>
 <property name="focusPolicy">
  <enum>Qt::NoFocus</enum>
 </property>
 <property name="text">
  <string>Start</string>
 </property>
 <property name="checkable">
  <bool>true</bool>
 </property>
</widget>
```

- [ ] **Step 3: Remove buttonTrimEnd definition**

Find and delete these lines (~lines 439-446):
```xml
<widget class="QPushButton" name="buttonTrimEnd">
 <property name="minimumSize">
  <size>
   <width>0</width>
   <height>18</height>
  </size>
 </property>
 <property name="maximumSize">
  <size>
   <width>95</width>
   <height>16777215</height>
  </size>
 </property>
 <property name="focusPolicy">
  <enum>Qt::NoFocus</enum>
 </property>
 <property name="text">
  <string>End</string>
 </property>
 <property name="checkable">
  <bool>true</bool>
 </property>
</widget>
```

- [ ] **Step 4: Add new buttonTrim widget**

In the same location (within `verticalLayout` in `frameAdvancedControls`), add:
```xml
<widget class="QPushButton" name="buttonTrim">
 <property name="minimumSize">
  <size>
   <width>44</width>
   <height>18</height>
  </size>
 </property>
 <property name="maximumSize">
  <size>
   <width>95</width>
   <height>16777215</height>
  </size>
 </property>
 <property name="focusPolicy">
  <enum>Qt::NoFocus</enum>
 </property>
 <property name="text">
  <string>Trim</string>
 </property>
 <property name="checkable">
  <bool>true</bool>
 </property>
</widget>
```

- [ ] **Step 5: Update tab order**

Find the tabOrder section (~lines 774-775) and replace:
```xml
<tabstop>buttonPause</tabstop>
<tabstop>buttonTrimStart</tabstop>
<tabstop>buttonTrimEnd</tabstop>
<tabstop>spinFrame</tabstop>
```

With:
```xml
<tabstop>buttonPause</tabstop>
<tabstop>buttonTrim</tabstop>
<tabstop>spinFrame</tabstop>
```

- [ ] **Step 6: Update tooltip strings**

Find and replace the tooltip sections (~lines 843-850):

Remove:
```xml
<string extracomment="Right-click for more options.">Click to set the starting position of a trim/
the point where the intro fade will stop.

Right-click for more options.</string>
<string extracomment="Right-click for more options.">Click to set the ending position of a trim/
the point where the outro fade will stop.

Right-click for more options.</string>
```

Add:
```xml
<string extracomment="Right-click for more options.">Click to set trim start at current position.
End is automatically set to video end.

Right-click for more options.</string>
```

- [ ] **Step 7: Verify XML is well-formed**

```bash
python -c "import xml.etree.ElementTree as ET; ET.parse('bin/window_pyplayer.ui')"
echo "XML is valid"
```

Expected: No error messages

- [ ] **Step 8: Commit UI changes**

```bash
git add bin/window_pyplayer.ui bin/window_pyplayer.ui.backup
git commit -m "refactor(ui): replace Start/End buttons with single Trim button

- Remove buttonTrimStart and buttonTrimEnd
- Add new buttonTrim with toggle behavior
- Update tab order and tooltips

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 1.2: Regenerate Python file from .ui

**Files:**
- Create: `bin/window_pyplayer.py` (regenerated)
- Modify: `bin/window_pyplayer.py`

- [ ] **Step 1: Run UI to Python converter**

```bash
python bin/convert_ui_to_py.py
```

Expected: `bin/window_pyplayer.py` regenerated with new button

- [ ] **Step 2: Verify buttonTrim exists in generated file**

```bash
grep -n "buttonTrim" bin/window_pyplayer.py
```

Expected: Should see `self.buttonTrim` definition

- [ ] **Step 3: Verify old buttons are removed**

```bash
grep -n "buttonTrimStart\|buttonTrimEnd" bin/window_pyplayer.py | wc -l
```

Expected: 0 (or only in comments)

- [ ] **Step 4: Commit generated file**

```bash
git add bin/window_pyplayer.py
git commit -m "refactor(ui): regenerate window_pyplayer.py with new Trim button

Auto-generated from window_pyplayer.ui changes

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Chunk 2: Core Logic Implementation

### Task 2.1: Add set_trim() function to main.pyw

**Files:**
- Modify: `main.pyw`

- [ ] **Step 1: Locate insertion point**

The new function should go after `set_trim_end()` (~line 6088)

- [ ] **Step 2: Add set_trim() function**

Insert after `set_trim_end()` function:

```python
def set_trim(self, enabled: bool):
    ''' Toggle trim mode - set start at current position, end at video end.

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

- [ ] **Step 3: Update trimButtonContextMenuEvent to use buttonTrim**

Find `trimButtonContextMenuEvent` (~line 1746) and update the context menu setup:

Change the reference from `buttonTrimStart`/`buttonTrimEnd` to `buttonTrim`:

```python
def trimButtonContextMenuEvent(self, event: QtGui.QContextMenuEvent):
    ''' Handles the context (right-click) menu for the trim button.
        Includes trim info display and options. '''
    is_trim_mode = self.is_trim_mode()
    is_trim_active = self.buttonTrim.isChecked()

    context = QtW.QMenu(self)

    # Show current trim status if active
    if is_trim_active:
        start_ms = self.minimum * (1000 / self.fps)
        remaining_ms = (self.maximum - self.minimum) * (1000 / self.fps)

        h, m, s, ms = get_hms(start_ms)
        if self.duration_rounded < 3600:
            start_label = f'Start: {m}:{s:02}.{ms:02}'
        else:
            start_label = f'Start: {h}:{m:02}:{s:02}'

        h, m, s, ms = get_hms(remaining_ms)
        if remaining_ms < 3600:
            length_label = f'Length: {m}:{s:02}.{ms:02}'
        else:
            length_label = f'Length: {h}:{m:02}:{s:02}'

        start_label_action = QtW.QAction(start_label, self)
        start_label_action.setEnabled(False)
        context.addAction(start_label_action)

        length_label_action = QtW.QAction(length_label, self)
        length_label_action.setEnabled(False)
        context.addAction(length_label_action)
        context.addSeparator()

    # Set start action (for consistency with old workflow)
    set_start_action = QtW.QAction('Set &start to current position', self)
    set_start_action.triggered.connect(lambda: self.set_trim(enabled=True))
    if not self.video or self.is_static_image:
        set_start_action.setEnabled(False)
    context.addAction(set_start_action)

    # Cancel trim action if active
    if is_trim_active:
        cancel_action = QtW.QAction('&Cancel trim', self)
        cancel_action.triggered.connect(lambda: self.set_trim(enabled=False))
        context.addAction(cancel_action)

    context.exec(event.globalPos())
```

- [ ] **Step 4: Update is_trim_mode() references**

The function `is_trim_mode()` checks if trim buttons are visible. Update if needed:

```python
def is_trim_mode(self):
    ''' Returns True if trim mode is selected (not fade mode). '''
    return self.actionTrimAuto.isChecked() or self.actionTrimPrecise.isChecked()
```

No changes needed - this function checks menu actions, not button state.

- [ ] **Step 5: Commit function implementation**

```bash
git add main.pyw
git commit -m "feat(trim): add set_trim() function for quick trim behavior

- New set_trim() function replaces set_trim_start/set_trim_end
- Sets start at current position, end at video end automatically
- Button displays remaining duration when active
- Updated trimButtonContextMenuEvent for new button

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2.2: Connect signal in qtstart.py

**Files:**
- Modify: `qtstart.py`

- [ ] **Step 1: Find signal connection section**

Look for `connect_widget_signals()` function

- [ ] **Step 2: Remove old button connections**

Find and remove/comment out:
```python
gui.buttonTrimStart.clicked.disconnect()
gui.buttonTrimStart.clicked.connect(lambda: gui.set_trim_start(enabled=not gui.buttonTrimStart.isChecked()))

gui.buttonTrimEnd.clicked.disconnect()
gui.buttonTrimEnd.clicked.connect(lambda: gui.set_trim_end(enabled=not gui.buttonTrimEnd.isChecked()))
```

- [ ] **Step 3: Add new buttonTrim connection**

Add:
```python
gui.buttonTrim.clicked.connect(lambda: gui.set_trim(not gui.buttonTrim.isChecked()))
```

- [ ] **Step 4: Update context menu event handler**

Find the line that assigns context menu:
```python
gui.buttonTrimStart.contextMenuEvent = gui.trimButtonContextMenuEvent
gui.buttonTrimEnd.contextMenuEvent = gui.trimButtonContextMenuEvent
```

Replace with:
```python
gui.buttonTrim.contextMenuEvent = gui.trimButtonContextMenuEvent
```

- [ ] **Step 5: Commit signal connections**

```bash
git add qtstart.py
git commit -m "refactor(signals): connect buttonTrim signal

- Remove buttonTrimStart/buttonTrimEnd signal connections
- Add buttonTrim.clicked signal to set_trim()
- Update context menu event handler assignment

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Chunk 3: Layout and Display Updates

### Task 3.1: Update layout logic in main.pyw

**Files:**
- Modify: `main.pyw`

- [ ] **Step 1: Find responsive_layout() function**

Search for the function that handles button visibility based on window width

- [ ] **Step 2: Update button visibility logic**

Find these lines (~line 1717-1718):
```python
self.buttonTrimStart.setVisible(primary_visible)
self.buttonTrimEnd.setVisible(primary_visible)
```

Replace with:
```python
self.buttonTrim.setVisible(primary_visible)
```

- [ ] **Step 3: Update button minimum width logic**

Find this line (~line 1712):
```python
self.buttonTrimStart.setMinimumWidth(32 if width <= 347 else 44)
```

Replace with:
```python
self.buttonTrim.setMinimumWidth(32 if width <= 347 else 44)
```

- [ ] **Step 4: Commit layout updates**

```bash
git add main.pyw
git commit -m "refactor(layout): update responsive layout for buttonTrim

- Replace buttonTrimStart/End visibility with buttonTrim
- Update minimum width logic for new button

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3.2: Update save() function

**Files:**
- Modify: `main.pyw`

- [ ] **Step 1: Find save() function operations check**

Search for `if self.buttonTrimStart.isChecked()` (~line 4630)

- [ ] **Step 2: Update trim operations check**

Find:
```python
if self.buttonTrimStart.isChecked(): operations['trim start'] = True
if self.buttonTrimEnd.isChecked():   operations['trim end'] = True
```

Replace with:
```python
if self.buttonTrim.isChecked(): operations['trim start'] = True
# End is always at video end, no need for 'trim end' operation
```

- [ ] **Step 3: Commit save logic update**

```bash
git add main.pyw
git commit -m "fix(save): update trim check for buttonTrim

- Use buttonTrim.isChecked() instead of buttonTrimStart/End
- End is always video end, no separate trim end operation

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3.3: Update playback loop logic

**Files:**
- Modify: `main.pyw`

- [ ] **Step 1: Find playback loop that checks trim end**

Search for `if frame >= self.maximum and self.buttonTrimEnd.isChecked()` (~line 5514)

- [ ] **Step 2: Update trim end check**

Find:
```python
if frame >= self.maximum and self.buttonTrimEnd.isChecked():
```

Replace with:
```python
if frame >= self.maximum and self.buttonTrim.isChecked():
```

- [ ] **Step 3: Commit playback loop update**

```bash
git add main.pyw
git commit -m "fix(playback): update trim end check for buttonTrim

- Use buttonTrim.isChecked() in playback loop
- Maintains auto-pause at trim end behavior

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Chunk 4: Cleanup and Finalization

### Task 4.1: Remove unused set_trim_start and set_trim_end functions

**Files:**
- Modify: `main.pyw`

- [ ] **Step 1: Locate old functions**

Find `def set_trim_start()` (~line 6038) and `def set_trim_end()` (~line 6064)

- [ ] **Step 2: Comment out or remove old functions**

These functions are no longer needed with the new `set_trim()` function.

Option A - Comment out (safer, allows rollback):
```python
# def set_trim_start(self, enabled: bool):
#     ''' DEPRECATED: Use set_trim() instead '''
#     ...
```

Option B - Remove entirely:
Delete the entire functions

- [ ] **Step 3: Commit cleanup**

```bash
git add main.pyw
git commit -m "refactor(trim): remove deprecated set_trim_start/end functions

Replaced by unified set_trim() function

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4.2: Update set_trim_mode function

**Files:**
- Modify: `main.pyw`

- [ ] **Step 1: Find set_trim_mode() function**

Search for `def set_trim_mode()` (~line 6090)

- [ ] **Step 2: Update button text references**

Find:
```python
self.buttonTrimStart.setText(self.buttonTrimStart.text().replace(' Fade to ', 'Start'))
self.buttonTrimEnd.setText(self.buttonTrimEnd.text().replace(' Fade from ', 'End'))
```

And:
```python
self.buttonTrimStart.setText(self.buttonTrimStart.text().replace('Start', ' Fade to '))
self.buttonTrimEnd.setText(self.buttonTrimEnd.text().replace('End', ' Fade from '))
```

Replace with:
```python
# buttonTrim text shows duration, not mode-specific
# No mode-specific text changes needed
```

- [ ] **Step 3: Commit mode update**

```bash
git add main.pyw
git commit -m "refactor(trim): update set_trim_mode for buttonTrim

- Remove mode-specific text changes
- buttonTrim displays duration, not mode labels

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4.3: Update constants.py if needed

**Files:**
- Check: `constants.py`

- [ ] **Step 1: Check for trim-related constants**

```bash
grep -n "TRIM" constants.py
```

- [ ] **Step 2: Update tooltip constant if found**

If `TRIM_BUTTON_TOOLTIP_BASE` exists, update it:

```python
TRIM_BUTTON_TOOLTIP_BASE = (
    'Click to set trim start at current position.\n'
    'End is automatically set to video end.\n'
    '\n'
    'Right-click for more options.'
)
```

- [ ] **Step 3: Commit if changes made**

```bash
git add constants.py
git commit -m "docs(constants): update trim tooltip constant

Reflect new quick trim button behavior

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Chunk 5: Testing

### Task 5.1: Manual testing

**Files:**
- None (manual testing)

- [ ] **Step 1: Launch application**

```bash
python main.pyw
```

- [ ] **Step 2: Test basic trim toggle**

1. Load a video file
2. Play to ~30% through video
3. Click "Trim" button
4. Verify: Button shows remaining duration
5. Verify: Playback continues from current position
6. Verify: Slider has rainbow marker at start position
7. Click "Trim" button again
8. Verify: Trim is cancelled, button shows "Trim"

- [ ] **Step 3: Test save functionality**

1. Set trim at some position
2. Click Save button
3. Verify: Output video starts from trim position
4. Verify: Output video ends at original video end

- [ ] **Step 4: Test right-click menu**

1. Right-click Trim button when inactive
2. Verify: Menu shows "Set start to current position"
3. Right-click Trim button when active
4. Verify: Menu shows start position and remaining duration
5. Verify: Menu shows "Cancel trim" option

- [ ] **Step 5: Test edge cases**

1. Try trim when no video loaded → button should be disabled
2. Try trim with static image → button should be disabled
3. Try trim at video start → should show full duration
4. Try trim near video end → should show small duration
5. Try different window widths → button should hide/show appropriately

- [ ] **Step 6: Test with different themes**

1. Switch between different themes (midnight, blueberry_breeze, etc.)
2. Verify button appearance in each theme

- [ ] **Step 7: Document test results**

Create test notes in `docs/testing/trim-button-notes.md` if issues found

---

### Task 5.2: Verify no regressions

**Files:**
- None (regression testing)

- [ ] **Step 1: Test existing features still work**

1. Play/pause/skip controls
2. Crop functionality
3. Other editing features (fade, rotate, etc.)
4. Keyboard shortcuts
5. System tray
6. Configuration save/load

- [ ] **Step 2: Check for any AttributeError in logs**

```bash
tail -50 pyplayer.log
```

Look for: `AttributeError: 'GUI_Instance' object has no attribute 'buttonTrimStart'`

---

## Chunk 6: Documentation

### Task 6.1: Update AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Add note about trim button change**

In the "Fork-Specific Changes" section, add:

```markdown
### This Fork: PyPlayer Compressor
**Repository:** https://github.com/Piyabordee/pyplayer-compressor-10mb

**Modifications:**
1. **Always-visible Save button** - Save button permanently displayed
2. **Quick Trim button** - Single Trim button replaces Start/End buttons
   - Sets start at current position, end at video end automatically
   - Toggle on/off with single click
```

- [ ] **Step 2: Commit documentation**

```bash
git add AGENTS.md
git commit -m "docs(AGents): document Quick Trim button feature

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 6.2: Update README if needed

**Files:**
- Check: `README.md`

- [ ] **Step 1: Check if trim is mentioned in README**

```bash
grep -n -i "trim" README.md
```

- [ ] **Step 2: Update any trim-related descriptions**

If README mentions trim workflow, update to reflect new button

- [ ] **Step 3: Commit if changes made**

```bash
git add README.md
git commit -m "docs(readme): update trim workflow description

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Final Checklist

- [ ] All tasks completed
- [ ] All tests pass
- [ ] No regressions found
- [ ] Documentation updated
- [ ] Clean git history (logical commits)

---

## Rollback Instructions

If issues arise, rollback to before changes:

```bash
git log --oneline -10  # Find commit before first change
git reset --hard <commit-hash>
```

Or restore from backup:
```bash
cp bin/window_pyplayer.ui.backup bin/window_pyplayer.ui
python bin/convert_ui_to_py.py
```

---

*End of Implementation Plan*
