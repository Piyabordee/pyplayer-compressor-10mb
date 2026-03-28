"""Editing operations — trim, crop, edit priority, compression."""
from __future__ import annotations

import glob
import logging
import os
import time
import uuid
from threading import Thread
from traceback import format_exc

from PyQt5 import QtCore, QtGui, QtWidgets as QtW

from pyplayer.core.constants import TEMP_DIR


logger = logging.getLogger(__name__)


class EditingMixin:
    """Methods: trim, crop, edit priority, compression."""

    def set_trim(self, enabled: bool):
        ''' Toggle trim mode - set start at current position, end at current + 20sec.

        Simple workflow:
            1. First click (enabled=True):
               - Enter trim mode
               - Start = current position, End = +20 seconds
               - Button shows "Save As" immediately
               - User can drag START/END markers to adjust

            2. Click "Save As" (either Trim button or Save As button):
               - Opens "Save As" dialog
               - Saves the trimmed video
               - Resets to full video playback
        '''
        if not self.video:
            return
        if self.is_static_image:
            return

        # Avoid loop - block signals while updating button state
        self.buttonTrim.blockSignals(True)
        self.buttonTrim.setChecked(enabled)
        self.buttonTrim.blockSignals(False)

        self.sliderProgress.clamp_minimum = enabled
        self.sliderProgress.clamp_maximum = enabled  # Allow dragging END marker too
        # Ensure slider remains enabled and can receive mouse events
        self.sliderProgress.setEnabled(True)
        self.sliderProgress.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        if enabled:
            self.minimum = get_ui_frame()
            # Set initial maximum to 20 seconds from now
            twenty_sec_frames = int(20 * self.frame_rate)
            self.maximum = min(self.minimum + twenty_sec_frames, self.sliderProgress.maximum())

            # Show "Save As" immediately - no duration display
            self.buttonTrim.setText('Save As')
            # Show the Save As button in advanced controls
            self.buttonTrimSave.setVisible(True)
        else:
            self._reset_trim_mode()

    def _reset_trim_mode(self):
        ''' Reset trim mode to default state (full range, button text). '''
        self.minimum = self.sliderProgress.minimum()
        self.maximum = self.sliderProgress.maximum()
        self.buttonTrim.setText('Trim')
        self.buttonTrim.setChecked(False)
        self.sliderProgress.clamp_minimum = False
        self.sliderProgress.clamp_maximum = False
        self.buttonTrimSave.setVisible(False)

    def save_from_trim_button(self):
        ''' Called when clicking Save As button after exiting trim mode.
            Opens save dialog and resets trim mode after completion.
            If auto_compress_after_trim is enabled, compresses the output. '''
        import os

        # Check if auto-compress is enabled (self IS the gui object with this attribute)
        auto_compress = getattr(self, 'auto_compress_after_trim', False)

        if not auto_compress:
            # Use normal save flow if auto-compress is disabled
            result = self.save_as(
                noun='trimmed media',
                filter='MP4 files (*.mp4);;All files (*)',
                valid_extensions=('.mp4',),
                ext_hint='.mp4'
            )

            # After save_as dialog (whether saved or cancelled), reset everything
            self._reset_trim_mode()
            self.buttonTrimSave.setVisible(False)
            return

        # Auto-compress is enabled - use custom two-step flow
        video = self.video
        if not video:
            show_on_statusbar('No media is playing.', 10000)
            self._reset_trim_mode()
            self.buttonTrimSave.setVisible(False)
            return

        if not self.is_safe_to_edit(video):
            show_on_statusbar('Save cancelled (source media is set to be overwritten).', 10000)
            self._reset_trim_mode()
            self.buttonTrimSave.setVisible(False)
            return

        # Step 1: Open save dialog to get the base output path
        default_path, _, _ = self.get_output(
            valid_extensions=('.mp4',),
            ext_hint='.mp4'
        )

        try:
            logging.info('Opening \'Save As...\' dialog for auto-compression.')
            base_output = self.browse_for_save_file(
                noun='trimmed media',
                filter='MP4 files (*.mp4);;All files (*)',
                valid_extensions=('.mp4',),
                ext_hint='.mp4',
                default_path=default_path or video,
                unique_default=True
            )

            if not base_output:
                # User cancelled - reset trim mode
                self._reset_trim_mode()
                self.buttonTrimSave.setVisible(False)
                return

            # Step 2: Prepare paths for two-step process
            base, ext = os.path.splitext(base_output)
            compressed_output = f"{base}_compressed{ext}"
            # Save temp file in app's temp directory (hidden from user), not in output folder
            temp_name = f"pyplayer_trim_{uuid.uuid4().hex[:8]}{ext}"
            temp_trimmed = os.path.join(TEMP_DIR, temp_name)

            logging.info(f'Step 1: Saving trimmed video to temp: {temp_trimmed}')
            logging.info(f'Step 2: Will compress to: {compressed_output}')

            # Show saving dialog during polling
            save_dialog = QtW.QProgressDialog('Saving trimmed video...', 'Cancel', 0, 0, self)
            save_dialog.setWindowModality(QtCore.Qt.WindowModal)
            save_dialog.setWindowTitle('Saving')
            # Style all text as black
            save_dialog.setStyleSheet('''
                QProgressDialog { color: black; }
                QLabel { color: black; }
                QPushButton { color: black; }
                QProgressBar { color: black; }
            ''')
            save_dialog.show()
            # Keep dialog responsive by processing events
            save_dialog.setValue(0)

            # Step 3: Save the trimmed video to temp location first
            # We use save() which handles all the trim operations
            # Pass open_after_save=False to prevent auto-opening the temp file
            save_result = self.save(dest=temp_trimmed, open_after_save=False)

            if not save_result:
                # Save was cancelled or failed
                self._reset_trim_mode()
                self.buttonTrimSave.setVisible(False)
                return

            # Step 4: Wait for save thread to complete by polling for file
            max_wait = 600  # 10 minutes max wait for large videos
            wait_interval = 0.5  # Check every 0.5 seconds
            waited = 0

            while waited < max_wait:
                # save() creates a temp file during processing, then renames to final name
                # Use glob to find any file matching base + _temp* pattern
                base_without_ext = temp_trimmed.replace('_temp.mp4', '')
                temp_files = glob.glob(f"{base_without_ext}_temp*")

                if os.path.exists(temp_trimmed):
                    # Final _temp.mp4 exists - save is complete
                    try:
                        size2 = os.path.getsize(temp_trimmed)
                        if size2 > 0:
                            break
                    except:
                        pass
                elif temp_files:
                    # _temp_temp.mp4 or _temp (2).mp4 exists - save is in progress
                    pass

                # Update dialog to show it's still working
                QtW.QApplication.processEvents()
                save_dialog.setValue(1)

                time.sleep(wait_interval)
                waited += wait_interval

            save_dialog.close()

            if not os.path.exists(temp_trimmed):
                save_dialog.close()
                show_on_statusbar('Save operation failed or timed out.', 10000)
                self._reset_trim_mode()
                self.buttonTrimSave.setVisible(False)
                return

            # Step 5: Compress the trimmed video (runs in background thread)
            logging.info(f'Compressing trimmed video to: {compressed_output}')

            # Define completion callback for async compression
            def compression_complete(success: bool, error: str):
                '''Called when compression completes (on main thread).'''
                logging.info(f'Compression complete callback: success={success}, error={error}')

                # Step 6: Clean up temp trimmed file
                try:
                    if os.path.exists(temp_trimmed):
                        os.remove(temp_trimmed)
                        logging.info(f'Cleaned up temp file: {temp_trimmed}')
                except Exception as e:
                    logging.warning(f'Failed to remove temp file {temp_trimmed}: {e}')

                if not success:
                    # Compression failed - reset trim mode
                    logging.error(f'Compression failed: {error}')
                    self._reset_trim_mode()
                    self.buttonTrimSave.setVisible(False)
                    return

                # Step 7: Success! Show status (file opening handled by _handle_compression_completion)
                logging.info(f'Successfully trimmed and compressed: {compressed_output}')
                show_on_statusbar(f'Trimmed and compressed: {os.path.basename(compressed_output)}', 5000)

                # Finally, reset trim mode
                self._reset_trim_mode()
                self.buttonTrimSave.setVisible(False)
                logging.info('Trim mode reset and button hidden')

            # Start async compression (returns immediately)
            self._compress_with_progress(
                input_path=temp_trimmed,
                output_path=compressed_output,
                completion_callback=compression_complete
            )

            # Function returns here - compression continues in background

        except Exception as e:
            logging.getLogger('main.pyw').error(f'Error in save_from_trim_button with auto-compress: {e}')
            show_on_statusbar(f'Auto-compress failed: {str(e)}', 10000)
            self._reset_trim_mode()
            self.buttonTrimSave.setVisible(False)

    def set_trim_mode(self, action: QtW.QAction):
        ''' Updates UI/tooltips for `action`'s associated trim mode. '''
        cfg.trimmodeselected = True
        # buttonTrim text shows duration, not mode-specific
        # Only update tooltip
        mode = 'trim' if action in (self.actionTrimAuto, self.actionTrimPrecise) else 'fade'
        self.buttonTrim.setToolTip(constants.TRIM_BUTTON_TOOLTIP_BASE.replace('?mode', mode))

    def set_crop_mode(self, on: bool):
        try:
            mime = self.mime_type
            is_gif = self.is_gif
            if not self.video or self.is_audio_without_cover_art:                   # reset crop mode if there's nothing to crop
                return self.actionCrop.trigger() if on else None

            if not on:
                self.disable_crop_mode()
            else:
                vlc = self.vlc
                restore_state = self.crop_restore_state
                if self.menubar.isVisible():
                    self.set_menubar_visible(False)
                    restore_state['menubar_visible'] = True
                else: restore_state['menubar_visible'] = False

                if is_gif:
                    restore_state['scale_setting'] = settings.comboScaleGifs
                    restore_state['scale_updater'] = image_player._updateGifScale
                elif mime == 'image':
                    restore_state['scale_setting'] = settings.comboScaleImages
                    restore_state['scale_updater'] = image_player._updateImageScale
                elif mime == 'audio':
                    restore_state['scale_setting'] = settings.comboScaleArt
                    restore_state['scale_updater'] = image_player._updateArtScale

                if 'scale_updater' in restore_state:
                    restore_state['scale_updater'](1 if is_gif else 2, force=True)
                    image_player.disableZoom()

                log_on_statusbar('Crop mode enabled. Right-click or press C to exit.')
                vlc.find_true_borders()

                if not vlc.selection:
                    vlc.selection = [
                        QtCore.QPoint(vlc.true_left + 20,  vlc.true_top + 20),      # 0 top left
                        QtCore.QPoint(vlc.true_right - 20, vlc.true_top + 20),      # 1 top right
                        QtCore.QPoint(vlc.true_left + 20,  vlc.true_bottom - 20),   # 2 bottom left
                        QtCore.QPoint(vlc.true_right - 20, vlc.true_bottom - 20)    # 3 bottom right
                    ]
                    s = vlc.selection
                    vlc.last_factored_points = s.copy()
                    vlc.crop_rect = QtCore.QRect(s[0], s[3])

                    class P:
                        ''' Enum representing points of the crop rectangle in QVideoPlayer.selection. Used here
                            purely for readablity purposes, performance impact is not worth it in realtime. '''
                        TOP_LEFT = 0
                        TOP_RIGHT = 1
                        BOTTOM_LEFT = 2
                        BOTTOM_RIGHT = 3

                    vlc.reference_example = {
                        P.TOP_LEFT:     {P.TOP_LEFT:     lambda x, y: (s[0].setX(min(x, s[3].x() - 10)), s[0].setY(min(y, s[3].y() - 10))),
                                         P.TOP_RIGHT:    lambda _, y:  s[1].setY(min(y, s[2].y() - 10)),
                                         P.BOTTOM_LEFT:  lambda x, _:  s[2].setX(min(x, s[1].x() - 10))},
                        P.TOP_RIGHT:    {P.TOP_LEFT:     lambda _, y:  s[0].setY(min(y, s[2].y() - 10)),
                                         P.TOP_RIGHT:    lambda x, y: (s[1].setX(max(x, s[2].x() + 10)), s[1].setY(min(y, s[2].y() - 10))),
                                         P.BOTTOM_RIGHT: lambda x, _:  s[3].setX(max(x, s[0].x() + 10))},
                        P.BOTTOM_LEFT:  {P.TOP_LEFT:     lambda x, _:  s[0].setX(min(x, s[1].x() - 10)),
                                         P.BOTTOM_LEFT:  lambda x, y: (s[2].setX(min(x, s[1].x() - 10)), s[2].setY(max(y, s[1].y() + 10))),
                                         P.BOTTOM_RIGHT: lambda _, y:  s[3].setY(max(y, s[0].y() + 10))},
                        P.BOTTOM_RIGHT: {P.TOP_RIGHT:    lambda x, _:  s[1].setX(max(x, s[0].x() + 10)),
                                         P.BOTTOM_LEFT:  lambda _, y:  s[2].setY(max(y, s[0].y() + 10)),
                                         P.BOTTOM_RIGHT: lambda x, y: (s[3].setX(max(x, s[0].x() + 10)), s[3].setY(max(y, s[0].y() + 10)))}
                    }
                    vlc.text_y_offsets = {P.TOP_LEFT: -8, P.TOP_RIGHT: -8, P.BOTTOM_LEFT: 14, P.BOTTOM_RIGHT: 14}

                # create & setup crop frames for the first time. this is done here... because...
                if not vlc.crop_frames:
                    vlc.crop_frames = (
                        QtW.QFrame(self),   # 0 top
                        QtW.QFrame(self),   # 1 left
                        QtW.QFrame(self),   # 2 right
                        QtW.QFrame(self),   # 3 bottom
                    )

                    for view in vlc.crop_frames:
                        view.mousePressEvent = vlc.mousePressEvent
                        view.mouseMoveEvent = vlc.mouseMoveEvent
                        view.mouseReleaseEvent = vlc.mouseReleaseEvent
                        view.mouseDoubleClickEvent = vlc.mouseDoubleClickEvent
                        view.leaveEvent = vlc.leaveEvent
                        view.setVisible(True)
                        view.setMouseTracking(True)
                        view.setStyleSheet('background: rgba(0, 0, 0, 135)')        # TODO add setting here?

                # crop frames already exist -> enable/restore them
                else:
                    for view in vlc.crop_frames:
                        view.setEnabled(True)
                        view.setVisible(True)

                width = self.width()
                vlc.update_crop_frames()                                            # update crop frames and factored points
                vlc.refresh_crop_cursor(vlc.mapFromGlobal(QtGui.QCursor.pos()))     # set appropriate cropping cursor
                if self.underMouse():                                               # unhide/lock ui if we're over the window
                    self.vlc.idle_timeout_time = 0.0
        except:
            log_on_statusbar(f'(!) Failed to toggle crop mode: {format_exc()}')

    def disable_crop_mode(self, log: bool = True):
        for view in self.vlc.crop_frames:                       # hide/disable crop frames
            view.setVisible(False)
            view.setEnabled(False)

        image_player.update()                                   # repaint gifPlayer to fix background
        self.vlc.dragging = None                                # clear crop-drag
        self.vlc.panning = False                                # clear crop-pan
        if settings.checkHideIdleCursor.isChecked():            # start hiding the cursor/UI right away if possible
            self.vlc.idle_timeout_time = 1.0                    # 0 locks the UI, so set it to 1

        # uncheck action and restore menubar/scale state. NOTE: if you do this part...
        # ...first, there's a chance of seeing a flicker after a crop edit is saved
        self.actionCrop.setChecked(False)
        restore_state = self.crop_restore_state
        self.set_menubar_visible(restore_state['menubar_visible'])
        if 'scale_setting' in restore_state:
            current_value = restore_state['scale_setting'].currentIndex()
            restore_state['scale_updater'](current_value, force=True)
        restore_state.clear()

        # `log` may be False when we're forcing crop mode to disable, such as while saving
        if log:
            log_on_statusbar('Crop mode disabled.')

    def cancel_all(self, *, wait: bool = False):
        ''' Cancels all edits in progress. If `wait` is True, this method
            blocks until the offending `Edit` objects are no longer in
            `self.edits_in_progress`, while ignoring any edits started
            after this method is called. '''

        # NOTE: this method works on the assumption a cancelled edit isn't removed from...
        # ...`self.edits_in_progress` until its FFmpeg process is confirmed to be killed
        log_on_statusbar('Cancelling all active edits...')
        if wait: to_cancel = self.edits_in_progress.copy()
        else:    to_cancel = self.edits_in_progress

        for edit in to_cancel:
            edit.cancel()

        if wait and to_cancel:                  # don't wait if we never had anything to cancel
            app.processEvents()                 # process events so our statusbar message shows up
            while True:
                sleep(0.1)
                for edit in to_cancel:
                    if edit in self.edits_in_progress:
                        break
                else:                           # else in a for-loop means we didn't break
                    log_on_statusbar('All edits cancelled, killed, and cleaned up.')
                    return

    def pause_all(self, paused: bool = True):
        ''' Sets the pause-state of all edits to `paused`. '''
        verb = 'Pausing' if paused else 'Resuming'
        logging.info(verb + ' all active edits...')
        for edit in self.edits_in_progress:
            edit.pause(paused=paused)

    def add_edit(self, edit: Edit):
        ''' Adds an `edit` to `self.edits_in_progress` and manually
            refreshes the progress bar in case the current edit is paused. '''
        self.edits_in_progress.append(edit)
        priority_edit = self.get_edit_with_priority()
        if priority_edit:
            priority_edit.set_progress_bar(value=priority_edit.value)

    def remove_edit(self, edit: Edit):
        ''' Removes an `edit` from `self.edits_in_progress` and updates edit
            priority if `edit` was the priority edit (or hides edit progress
            altogether if there are no edits remaining), otherwise refreshes
            the progress bar in case the actual priority edit is paused. '''
        self.edits_in_progress.remove(edit)
        if edit.has_priority or not self.edits_in_progress:
            self.reset_edit_priority()
        else:
            priority_edit = self.get_edit_with_priority()
            if priority_edit:
                priority_edit.set_progress_bar(value=priority_edit.value)

    def get_edit_with_priority(self) -> Edit:
        ''' Returns the `Edit` object in `self.edits_in_progress` that currently
            has priority. Only returns the first one found. '''
        for edit in self.edits_in_progress:
            if edit.has_priority:
                return edit

    def cycle_edit_priority(self):
        ''' Gives priority to the `Edit` at `self.edits_in_progress`'s next index,
            wrapping if necessary. Updates the progress bar immediately. '''
        try:
            edits = self.edits_in_progress
            for new_index, save in enumerate(edits, start=1):
                if save.has_priority:
                    save.has_priority = False
                    edits[new_index % len(edits)].give_priority()
                    break
        except ZeroDivisionError:
            logging.info('(?) Tried to cycle edit priority, but `self.edits_in_progress` became empty while doing so.')
        except:
            log_on_statusbar(f'(!) Unexpected error while cycling edit: {format_exc()}')

    def reset_edit_priority(self, _paranoia: bool = False):
        ''' Sets priority to the `Edit` in `self.edits_in_progress` closest
            to completion, preferring an unpaused one if possible. If 20+
            edits are running, the first unpaused edit is used instead.
            If they're all paused, index 0 is used instead. If no edits
            are remaining, the progress bar is reset. '''
        if not _paranoia:
            self.lock_edit_priority = True      # lock priority so the progress bar doesn't flicker from a rare double-switch

        # NOTE: Dealing with the high-precision slider has made me very, very paranoid about race conditions.
        # TODO: we should probably calculate ETAs and use those instead (and display them somewhere)
        try:
            sleep(0.05)                         # sleep to absolutely ensure we don't double-switch priority
            edits = self.edits_in_progress
            if edits:

                # 1 edit, switch priority immediately
                if len(edits) == 1:
                    edits[0].give_priority(ignore_lock=True, conditional=True)

                # 2-19 edits, switch to edit closest to completion
                elif len(edits) < 20:
                    highest_edit = None
                    highest_unpaused_edit = None
                    highest_value = -1
                    highest_unpaused_value = -1
                    for edit in edits:
                        percent = edit.value
                        if percent > highest_value:
                            highest_value = percent
                            highest_edit = edit
                        if not edit._is_paused:
                            if percent > highest_unpaused_value:
                                highest_unpaused_value = percent
                                highest_unpaused_edit = edit

                    # switch to highest unpaused edit if one exists, otherwise fallback to paused ones
                    if highest_unpaused_edit:
                        highest_unpaused_edit.give_priority(ignore_lock=True, conditional=True)
                    elif highest_edit:          # they're all paused
                        highest_edit.give_priority(ignore_lock=True, conditional=True)

                # 20+ edits in progress, just change priority fast
                else:
                    for edit in edits:
                        if not edit._is_paused:
                            edit.give_priority(ignore_lock=True, conditional=True)
                            break
                    else:                       # we didn't break the for-loop (they're all paused)
                        edits[0].give_priority(ignore_lock=True, conditional=True)

                # make sure something actually got priority
                if self.get_edit_with_priority() is None:
                    if not _paranoia:           # somehow, nothing got set. try again?
                        logging.warning('(!) Edit priority auto-update somehow accomplished nothing, resorting to emergency measures.')
                        self.reset_edit_priority(_paranoia=True)
                    elif edits:                 # nothing got set AGAIN? just try and brute-force the first edit
                        edits[0].give_priority(ignore_lock=True, update_others=True)
                    else:                       # failed repeatedly, yet there aren't even any edits. just hide everything
                        self.hide_edit_progress()

            # no edits are in progress anymore, hide progress bar and reset titlebar/taskbar
            else:
                self.hide_edit_progress()

        # uh oh spaghettios
        except:
            logging.warning(f'(!) Edit priority auto-update is failing, trying last-ditch effort: {format_exc()}')
            if not edits:                       # likely failed because all edits finished while this method was executing
                self.hide_edit_progress()
            else:
                try:                            # failed because... huh? try and set priority one more time
                    edits[0].give_priority(ignore_lock=True, update_others=True)
                except:                         # getting here basically requires several consecutive race conditions
                    log_on_statusbar(f'(!) Edit priority auto-update failed BADLY: {format_exc()}')
        finally:
            if not _paranoia:
                self.lock_edit_priority = False

    def hide_edit_progress(self):
        ''' Resets the editing progress bar to zero and hides its
            widget on the statusbar while clearing its percentage
            from the titlebar and taskbar button (on Windows). You
            should probably use `self.reset_edit_priority()` instead. '''
        self.set_save_progress_visible_signal.emit(False)           # hide the progress bar
        self.set_save_progress_max_signal.emit(0)                   # reset progress bar values
        self.set_save_progress_value_signal.emit(0)
        if constants.IS_WINDOWS and settings.checkTaskbarProgressEdit.isChecked():
            self.taskbar_progress.reset()                           # reset taskbar progress (`setVisible(False)` not needed)
        refresh_title()                                             # refresh title to hide progress percentage

    def is_safe_to_edit(self, *infiles: str, dest: str = None, popup: bool = True) -> bool:
        ''' Returns True if `dest` and `infiles` are safe to use for FFmpeg
            operations. If not and `popup` is True, a detailed warning is shown.
            Checks if `dest`/`infiles` are in `self.locked_files` and tries
            renaming `dest` to itself to ensure no handles exist. Stops the
            player before the rename-check if `dest` is `self.video`. '''
        msg = ''
        if dest in infiles:                     # check if we're overwriting `dest`
            infiles = [file for file in infiles if file != dest]

        # check if our files were explicitly locked
        locked_files = self.locked_files
        output_locked = dest in locked_files
        locked = [(i, f) for i, f in enumerate(infiles) if f in locked_files]
        if locked or output_locked:
            logging.info(f'(?) Files to be concatenated and/or the output are locked, cancelling: {locked}')

            # generate an appropriate title, body, and list of offending files depending on how many...
            # ...files were provided, how many are invalid, and if both the output AND input files were bad
            if not popup:
                header = ''
                footer = ''
            elif output_locked:
                if len(locked) > 1:
                    title = 'Output and input files are in use!'
                    header = 'The output path and the files at the following indexes are set to be overwritten by different edit(s):'
                    footer = f'Output: {dest}\n' + '\n'.join(f'{index + 1}. {file}' for index, file in locked)
                elif len(locked) == 1:
                    title = 'Output and input file are both in use!'
                    if len(infiles) > 1:
                        header = 'The output path and the file at the following index are set to be overwritten by different edit(s):'
                        footer = '\n'.join(f'{index + 1}. {file}' for index, file in locked)
                    else:
                        header = 'The output path and input file are set to be overwritten by different edit(s):'
                        footer = f'Output: {dest}\nInput: {infiles[0]}'
                else:
                    title = 'Output is in use!'
                    header = 'The output path is set to be overwritten by a different edit:'
                    footer = dest
            else:
                if len(locked) == 1:
                    title = 'Input file is in use!'
                    if len(infiles) > 1:
                        header = 'The file at the following index is set to be overwritten by a different edit:'
                        footer = '\n'.join(f'{index + 1}. {file}' for index, file in locked)
                    else:
                        header = 'The input file is set to be overwritten by a different edit:'
                        footer = infiles[0]
                else:
                    title = 'Input files are in use!'
                    header = 'The files at the following indexes are set to be overwritten by different edit(s):'
                    footer = '\n'.join(f'{index + 1}. {file}' for index, file in locked)
            msg = f'{header}\n\n{footer}'

        # check if we might not be able to write to our `dest` when the edit is finished
        elif dest and exists(dest):
            try:
                if dest == self.video:          # stop player to make sure nothing else is using our destination
                    self.stop()
                os.rename(dest, dest)           # rename file to itself as a simple access-check
            except PermissionError:             # the path still cannot be written to
                title = 'Output is in use!'
                msg = f'The output path is currently being used by another process:\n\n{dest}'

        if msg:
            if popup:
                qthelpers.getPopup(             # TODO: add the signal version too if we need it
                    title=title,
                    text=msg,
                    icon='warning',
                    **self.get_popup_location_kwargs()
                ).exec()
            return False
        return True

    def update_time_spins(self):
        ''' Handles the hour, minute, and second spinboxes. Calculates
            the next frame based on the new values, and updates the progress
            UI accordingly. If the new frame is outside the bounds of the
            media, it's replaced with the current frame and the progress
            UI is reset to its previous state. '''

        # return if user is not manually setting the time spins
        if self.lock_progress_updates: return
        self.lock_progress_updates = True               # lock progress updates to prevent recursion errors from multiple elements updating at once

        try:
            seconds = self.spinHour.value() * 3600
            seconds += self.spinMinute.value() * 60
            seconds += self.spinSecond.value()

            old_frame = self.spinFrame.value()
            excess_frames = old_frame % self.frame_rate
            new_frame = round((seconds * self.frame_rate) + excess_frames)

            # if the new frame is out of bounds, just reset the UI to match the old frame
            if self.minimum < new_frame > self.maximum:
                update_progress(old_frame)
            else:
                set_and_update_progress(new_frame, SetProgressContext.NAVIGATION_EXACT)
            logging.debug(f'Manually updating time-spins: seconds={seconds} frame {old_frame} -> {new_frame} ({excess_frames} excess frame(s))')

        except: logging.error(f'(!) UPDATE_TIME_SPINS FAILED: {format_exc()}')
        finally: self.lock_progress_updates = False     # always release lock on progress updates

    def update_frame_spin(self, frame: int):
        ''' Sets progress to `frame` if media is paused. This is meant as a
            slot for `self.spinFrame` - Do not use this for frame seeking. '''
        if not self.is_paused or self.lock_progress_updates: return
        self.lock_progress_updates = True               # lock progress updates to prevent recursion errors from multiple elements updating at once

        try: player.set_frame(frame)
        except: logging.warning(f'Abnormal error while updating frame-spins: {format_exc()}')
        finally: self.lock_progress_updates = False     # always release lock on progress updates

    def manually_update_current_time(self):
        ''' Sets progress to the timestamp within `self.lineCurrentTime`.
            Supports various formats, including percentages and raw seconds. '''
        text = self.lineCurrentTime.text().strip()
        if not text: return
        logging.info(f'Manually updating current time "label" to {text}')

        try:
            if '%' in text:                             # do regular strip() again in case spaces were placed between number and %
                percent = float(text.strip('%').strip()) / 100
                frame = self.frame_count * percent
            else:
                seconds = 0
                parts = tuple(float(part) for part in text.split(':') if part)    # float() takes care of milliseconds at the end
                if len(parts) == 3:   seconds += (parts[0] * 3600) + (parts[1] * 60) + parts[2]
                elif len(parts) == 2: seconds += (parts[0] * 60) + parts[1]
                elif len(parts) == 1: seconds = parts[0]
                frame = int(seconds * self.frame_rate)  # int() instead of ceil() to ensure we don't go too far

            if self.minimum <= frame <= self.maximum:
                try:
                    self.lock_progress_updates = True
                    set_and_update_progress(frame, SetProgressContext.NAVIGATION_EXACT)
                except: logging.warning(f'Abnormal error while locking/setting/updating progress: {format_exc()}')
                finally: self.lock_progress_updates = False

        except: pass                                    # ignore invalid inputs
        finally: self.lineCurrentTime.clearFocus()      # clear focus after update no matter what

    def _cleanup_edit_output(
        self,
        temp_dest: str,
        final_dest: str,
        ctime: float,
        mtime: float,
        delete_mode: int = 0,
        to_delete: str | tuple[str] = None,
        noun: str = ''
    ) -> str | None:
        ''' Ensures `temp_dest` exists, isn't empty, and produces a valid probe.
            If unsuccessful, None is returned, the specific failure is logged
            (referring to the file as `noun`), and `temp_dest` is deleted.
            Once validated, `temp_dest` is renamed to `final_dest` with its
            timestamps set to `ctime`/`mtime`.

            - `delete_mode=1` - `to_delete` is marked for deletion
            - `delete_mode=2` - `to_delete` is deleted/recycled outright
            - NOTE: `final_dest` cannot be marked or deleted.

            If everything is valid but `temp_dest` cannot be renamed, a popup is
            shown and `temp_dest` is returned. Otherwise, returns `final_dest`.

            NOTE: If `temp_dest` is valid, this function is relatively "slow"
            as we must wait for a fresh probe file to be created. '''
        try:
            noun = noun or 'Media'
            if not exists(temp_dest):
                return log_on_statusbar(f'(!) {noun} saved without error, but never actually appeared. Possibly an FFmpeg error. No changes have been made.')
            if os.stat(temp_dest).st_size == 0:
                return log_on_statusbar(f'(!) {noun} saved without error, but was completely empty. Possibly an FFmpeg error. No changes have been made.')

            # next part takes a while so show text on the progress bar if this is the last edit
            if len(self.edits_in_progress) == 1:
                self.set_save_progress_format_signal.emit('Cleaning up...')

            # NOTE: this probe can't be reused since `temp_dest` is about to be renamed,...
            # ...but cleanup is 100x easier if we do this now rather than later
            new_probe = probe_files(temp_dest, refresh=True, write=False)
            if not new_probe:                   # no probe returned
                return log_on_statusbar(f'(!) {noun} saved without error, but cannot be probed. Possibly an FFmpeg error. No changes have been made.')
            elif not new_probe[temp_dest]:      # empty probe returned TODO: not possible anymore. add parameter for old `probe_files()` behavior?
                return log_on_statusbar(f'(!) {noun} saved without error, but returned an invalid probe. Possibly an FFmpeg error. No changes have been made.')

            # handle deletion behavior, ignoring `final_dest`
            if isinstance(to_delete, str): to_delete = (to_delete,) if to_delete != final_dest else None
            elif to_delete:                to_delete = [file for file in to_delete if file != final_dest]
            if to_delete:                       # 1 -> mark for deletion, 2 -> recycle/delete outright
                if delete_mode == 1:       self.mark_for_deletion(*to_delete, mark=True, mode='')
                elif delete_mode == 2:     self.delete(*to_delete, cycle=False)

            # rename `dest` back to `final_dest` if possible
            if self.video == final_dest:        # stop player if necessary
                self.stop()
            try:
                if exists(final_dest): os.replace(temp_dest, final_dest)
                else:                  os.rename(temp_dest, final_dest)
            except PermissionError:
                dirname = os.path.dirname(temp_dest)
                temp_filename = os.path.basename(temp_dest)
                final_filename = os.path.basename(final_dest)
                header = 'Unable to rename our temporary file to our final output path.'
                body = f'\n\nFolder: {dirname}\n---\nFilenames: "{temp_filename}" -> "{final_filename}"\n\n'
                footer = 'Either the output path or the temporary file is currently being used by another process. The temporary file has not be renamed.'
                self.popup_signal.emit(
                    dict(
                        title='Output is in use!',
                        text=f'{header}{body}{footer}',
                        icon='warning',
                        **self.get_popup_location_kwargs()
                    )
                )
                final_dest = temp_dest

            # update `final_dest`'s ctime/mtime if necessary
            self.set_file_timestamps(
                path=final_dest,
                ctime=ctime,
                mtime=mtime
            )

            # delete `final_dest`'s probe file in rare event it becomes stale (size & mtime/ctime were not altered)
            self.open_probe_file(file=final_dest, delete=True, verbose=False)
            return final_dest
        except:
            return log_on_statusbar(f'(!) Post-{noun.lower() or "save"} destination cleanup failed: {format_exc()}')
        finally:                                # make sure `temp_dest` does not actually have a probe file
            self.open_probe_file(file=temp_dest, delete=True, verbose=False)

    def _compress_with_progress(self, input_path: str, output_path: str, completion_callback=None) -> None:
        '''
        Show progress dialog and compress video for Discord in a background thread.
        This method returns immediately and calls completion_callback when done.

        Args:
            input_path: Path to input video file
            output_path: Path to output compressed video
            completion_callback: Optional callback(success: bool, error: str) -> None
        '''
        import compression

        # Store completion callback so the slot can access it
        self._compression_completion_callback = completion_callback

        # Verify FFmpeg is available
        if not constants.FFMPEG:
            self._show_ffmpeg_missing_dialog()
            if completion_callback:
                completion_callback(False, 'FFmpeg not available')
            self._compression_completion_callback = None
            return

        # Verify FFprobe is available (optional but recommended)
        ffprobe = constants.FFPROBE if constants.FFPROBE else ''

        # Create and show progress dialog (modeless so it doesn't block)
        from main import CompressProgressDialog
        dialog = CompressProgressDialog(self, input_path)

        # Hide main window during compression
        self.hide()

        # Show progress dialog (now only this is visible)
        dialog.show()

        # Keep dialog reference for the thread
        self._compression_dialog = dialog

        # Store output path to open later
        self._compression_output_path = output_path

        # Progress callback using Qt's thread-safe method
        def progress_callback(percent: int):
            QtCore.QMetaObject.invokeMethod(
                dialog.progressBar,
                'setValue',
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(int, percent)
            )

        # Compression function to run in background thread
        def run_compression():
            try:
                success, error = compression.compress_video(
                    ffmpeg_path=constants.FFMPEG,
                    ffprobe_path=ffprobe,
                    input_path=input_path,
                    output_path=output_path,
                    progress_callback=progress_callback
                )
            except Exception as e:
                success, error = False, f'Compression exception: {e}'
                logging.getLogger('main.pyw').error(f'Compression failed: {e}')

            logging.info(f'Compression thread finished: success={success}')

            # Ensure progress reaches 100% even if callback wasn't called
            if success:
                progress_callback(100)

            # Use invokeMethod to schedule dialog close on main thread
            # This is more reliable than QTimer.singleShot for cross-thread calls
            QtCore.QMetaObject.invokeMethod(
                self,
                '_handle_compression_completion',
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(bool, success),
                QtCore.Q_ARG(str, error)
            )

        # Start compression in background thread
        Thread(target=run_compression, daemon=True).start()

    @QtCore.pyqtSlot(bool, str)
    def _handle_compression_completion(self, success: bool, error: str):
        '''
        Slot method called on main thread when compression completes.
        This is invoked via QMetaObject.invokeMethod from the background thread.

        Args:
            success: Whether compression succeeded
            error: Error message if failed
        '''
        import os
        logging.info(f'Compression completion handler called: success={success}')

        # Close the progress dialog
        if hasattr(self, '_compression_dialog') and self._compression_dialog:
            logging.info('Closing compression progress dialog')
            self._compression_dialog.accept()
            self._compression_dialog.deleteLater()
            self._compression_dialog = None

        # Show main window back (it was hidden during compression)
        self.show()
        logging.info('Main window restored after compression')

        # If successful, open the compressed file
        if success and hasattr(self, '_compression_output_path'):
            output_path = self._compression_output_path
            self._compression_output_path = None
            logging.info(f'Opening compressed file: {output_path}')
            self.open(output_path)
        elif not success:
            # Show error if compression failed
            self._show_compress_error_dialog(error)
            self._cleanup_temp_files(getattr(self, '_compression_output_path', ''))

        # Call the stored completion callback if provided
        # This handles trim mode reset, cleanup, etc.
        if hasattr(self, '_compression_completion_callback'):
            callback = self._compression_completion_callback
            self._compression_completion_callback = None  # Clear reference
            if callback:
                callback(success, error)
