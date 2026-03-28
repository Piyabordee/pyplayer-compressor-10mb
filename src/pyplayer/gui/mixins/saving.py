"""Saving operations — save, save_as, concatenate, resize, rotate, audio operations, text overlay."""
from __future__ import annotations

import gc
import logging
import os
from threading import Thread
from time import time as get_time
from traceback import format_exc

from PyQt5 import QtCore, QtWidgets as QtW
from PyQt5.QtCore import Qt

from pyplayer.core.constants import TEMP_DIR, THUMBNAIL_DIR


logger = logging.getLogger(__name__)


class SavingMixin:
    """Methods: save, save_as, concatenate, resize_media, rotate_video, add_audio,
    amplify_audio, replace_audio, isolate_track, add_text, browse_for_directory,
    browse_for_save_file, browse_for_subtitle_files."""

    # NOTE: Due to the length of these methods, they are being extracted from main.pyw
    # This mixin provides the structure for the saving-related methods

    def save(
        self,
        *,                                                      # * to capture unused signal args
        dest: str = None,
        noun: str = 'media',
        filter: str = 'MP4 files (*.mp4);;MP3 files (*.mp3);;WAV files (*.wav);;AAC files (*.aac);;All files (*)',
        valid_extensions: tuple[str] = constants.ALL_MEDIA_EXTENSIONS,
        preferred_extensions: tuple[str] = None,
        ext_hint: str = None,
        unique_default: bool = False,
        open_after_save: bool | None = None
    ) -> bool | None:
        ''' Checks for any edit operations, applies them to the current media,
            and saves the new file to `dest`. If `dest` is None, `save_as()`
            is called, passing in `filter`, and a list of `valid_extensions`.
            If `preferred_extensions` is specified, `save_as()` will default
            to an extension from this list if possible, even if the current
            extension is already valid. If `dest` has no extension, `ext_hint`
            will be used. If `ext_hint` is None, PyPlayer will guess the
            extension. `unique_default` is passed to `save_as()` if necessary.

            `open_after_save` controls whether the saved file is automatically
            opened after saving. None (default) means auto-open if the saved
            file is the same as the current media. False disables auto-open.

            NOTE: Saving occurs in a separate thread. '''

        video = self.video
        if not video: return show_on_statusbar('No media is playing.', 10000)
        if not self.is_safe_to_edit(video): return show_on_statusbar('Save cancelled (source media is set to be overwritten).', 10000)

        operations = self.operations.copy()
        if self.actionCrop.isChecked():      operations['crop'] = True
        if self.buttonTrim.isChecked(): operations['trim start'] = True
        # End is always at video end, no need for 'trim end' operation

        ext = ''
        old_base, old_ext = splitext_media(video)
        if not old_ext:
            old_ext = '.' + self.extension

        # see if we haven't sufficiently edited the destination (no abspath specified, same basename (excluding the extension))
        if not dest:
            dest_was_not_modified = True                        # TODO i don't think this code actually matters anymore
        else:
            old_tail_base = os.path.split(old_base)[-1]
            new_base, new_ext = splitext_media(dest)
            dest_was_not_modified = old_tail_base == new_base

        # get output name
        if dest_was_not_modified:

            # NOTE: `unique_default` behavior examples:
            # Example 1: video='test.mp4', output='test', ext_hint='.mp3'
            #     -> open prompt with 'test.mp3' as the default if it doesn't exist, 'test (2).mp3' otherwise
            # Example 2: video='test.mp4', output='new', ext_hint='.mp3'
            #     -> immediately saves as 'new.mp3' if it doesn't exist, opens a prompt with 'new (2).mp3' otherwise
            output_text, _, ext = self.get_output(              # TODO: ^ this is extremely stupid
                valid_extensions=valid_extensions,
                ext_hint=ext_hint,
            )

            # no name OR name already exists -> use preset name or "Save as..." prompt
            # NOTE: `exists(output_text)` only applies to OTHER files, not `self.video`
            unchanged = not output_text
            if unchanged or exists(output_text):
                if ext_hint and unchanged:                      # invalid/unchanged output -> use `ext_hint` if possible but still show prompt
                    output_text = old_base + ext_hint

                if settings.checkSaveAsForceOnNoName.isChecked():
                    return self.save_as(
                        noun=noun,
                        filter=filter,
                        valid_extensions=preferred_extensions or valid_extensions,
                        ext_hint=ext_hint or old_ext,           # ^ pass preferred extensions if provided
                        default_path=output_text,
                        unique_default=unique_default
                    )
                elif operations:
                    dest = add_path_suffix(video, '_edited', unique=True)
            else:
                dest = output_text
                if not os.path.dirname(dest):                   # output text is just a name w/ no directory
                    default_dir = settings.lineDefaultOutputPath.text().strip() or os.path.dirname(video)
                    dest = abspath(os.path.expandvars(os.path.join(default_dir, dest)))     # ^ if no default dir, use source media's dir
                if not splitext_media(dest, valid_extensions)[-1]:                          # append extension if needed
                    ext = ext_hint or old_ext
                    dest += ext                                 # use extension hint if specified, otherwise just use source file's extension
            dirname, basename = os.path.split(dest)             # sanitize our custom destination (`sanitize` does not account for full paths)
            dest = os.path.join(dirname, sanitize(basename))

        # ensure output has valid extension included
        if not ext:
            if not splitext_media(dest, valid_extensions)[-1]:
                dest += ext_hint or old_ext
        logging.info(f'Destination extension is "{ext}"')
        dest = abspath(dest)                                    # clean up destination one more time, just in case

        # check for common reasons we might not be allowed to use `dest`
        if not self.is_safe_to_edit(dest=dest):                 # NOTE: we already checked `self.video` above
            return self.save_as(noun=noun, filter=filter, default_path=dest, unique_default=True)

        # no operations -> check if video was renamed and return without starting a new thread
        if not operations:
            if dest != video:                                   # no operations, but name is changed
                logging.info(f'No operations detected, but a new name was specified. Renaming to {dest}')
                return self.rename(dest)                        # do a normal rename and return
            return marquee('No changes have been made.', log=False)

        # do actual saving in separate thread
        Thread(target=self._save, args=(dest, operations, open_after_save), daemon=True).start()
        return True

    def _save(self, dest: str = None, operations: dict = {}, open_after_save: bool | None = None):
        ''' Do not call this directly. Use `save()` instead. Iteration: VII '''
        # This is a very long method - see main.pyw lines 4848-5628 for full implementation
        start_time = get_time()
        successful = True
        log_noun = ''

        # save copies of critical properties that could potentially change while we're saving
        video = self.video.strip()
        mime = self.mime_type
        extension = self.extension
        is_gif = self.is_gif
        is_static_image = self.is_static_image
        frame_count, frame_count_raw = self.frame_count, self.frame_count_raw
        frame_rate, duration = self.frame_rate, self.duration
        vwidth, vheight = self.vwidth, self.vheight
        minimum, maximum = self.minimum, self.maximum
        audio_track_count = player.get_audio_track_count()
        audio_track_titles: list[str] = [id_and_title[-1] for id_and_title in list(player.get_audio_tracks())[1:]]

        # what will we do to our output and original files after saving? (NOTE: concatenation will override these)
        if open_after_save is None:                             # None means we'll decide after the edit finishes
            open_after_save = None
        explore_after_save = False
        delete_mode = 0  # checkDeleteOriginal removed from UI (0 = no deletion)

        # operation aliases
        op_concat: dict[str] =               operations.get('concatenate', None)    # see `self.concatenate()` for details
        op_add_text =                        operations.get('add text', None)       # a list of `widgets.QTextOverlay` objects
        op_replace_audio: str =              operations.get('replace audio', None)  # path to audio track
        op_add_audio: str =                  operations.get('add audio', None)      # path to audio track
        op_isolate_track: tuple[str, int] =  operations.get('isolate track', None)  # track-type and index to isolate
        op_amplify_audio: float =            operations.get('amplify audio', None)  # new volume, from 0-1(+)
        op_resize: tuple[int, int] | float = operations.get('resize', None)         # (width, height) OR duration multiplier
        op_rotate_video: str =               operations.get('rotate video', None)   # rotation command (e.g. "vflip")
        op_trim_start: bool =                operations.get('trim start', False)    # represents both trimming and fading
        op_trim_end: bool =                  operations.get('trim end', False)      # represents both trimming and fading
        op_crop: bool =                      operations.get('crop', False)

        # The rest of this method is extremely long and handles all the FFmpeg operations
        # For the complete implementation, see main.pyw lines 4848-5628
        # This placeholder provides the method signature and initial setup
        pass

    def save_as(
        self,
        *,                                                      # * to capture unused signal args
        noun: str = 'media',
        filter: str = 'MP4 files (*.mp4);;MP3 files (*.mp3);;WAV files (*.wav);;AAC files (*.aac);;All files (*)',
        valid_extensions: tuple[str] = constants.ALL_MEDIA_EXTENSIONS,
        ext_hint: str = None,
        default_path: str = None,
        unique_default: bool = True
    ) -> bool | None:
        ''' Opens a file dialog with `filter` and the caption "Save `noun`
            as...", before saving to the user-selected path, if any. Returns
            None if the dialog is cancelled. See `save()` for more details. '''

        video = self.video
        if not video: return show_on_statusbar('No media is playing.', 10000)
        if not self.is_safe_to_edit(video): return show_on_statusbar('Save cancelled (source media is set to be overwritten).', 10000)
        if not default_path:
            default_path, _, _ = self.get_output(
                valid_extensions=valid_extensions,
                ext_hint=ext_hint
            )

        try:
            logging.info('Opening \'Save As...\' dialog.')
            file = self.browse_for_save_file(
                noun=noun,
                filter=filter,
                valid_extensions=valid_extensions,
                ext_hint=ext_hint,
                default_path=default_path or video,
                unique_default=unique_default
            )

            if file:                                            # None if cancel was selected
                logging.info(f'Saving as \'{file}\'')
                return self.save(dest=file)
        except:
            log_on_statusbar(f'(!) SAVE_AS FAILED: {format_exc()}')

    def concatenate(self, action: QtW.QAction = None, files: list[str] = None):
        ''' Opens a separate dialog for concatenation with `files` included by
            default. Behavior changes depending on which `action` is passed:

            - `actionCatDialog`     - Open dialog immediately with `self.video`
                                      if present, otherwise an empty dialog.
                                      This is the default if `action` is None.
            - `actionCatBeforeThis` - Open file browser first, then the dialog if
                                      more than one additional file was provided.
                                      Cancel if file browser is cancelled. Files
                                      picked are inserted BEFORE `self.video`.
            - `actionCatAfterThis`  - Ditto, but files are appended AFTER.
            - `actionCatBeforeLast` - Open dialog immediately with `self.video`
                                      placed before `self.last_video`. If
                                      `self.last_video` doesn't exist, cancel.
            - `actionCatAfterLast`  - Ditto, but the order is reversed.

            Dialog (if opened) stays open indefinitely until user either
            successfully concatenates or deliberately closes the dialog.
            Output naming, save-prompts, and the "Save"/"Save as..." buttons
            follow the same conventions as normal saving.

            See `self._concatenate()` for the actual concatenation process. '''
        # TODO should this be unified with the other edit methods in some way and allow chaining?
        # https://stackoverflow.com/questions/7333232/how-to-concatenate-two-mp4-files-using-ffmpeg
        # https://stackoverflow.com/questions/31691943/ffmpeg-concat-produces-dts-out-of-order-errors
        try:
            if not constants.verify_ffmpeg(self, force_warning=True):
                return marquee('You don\'t have FFmpeg installed!')
            if not action:
                action = self.actionCatDialog

            # we probe our files before starting so we set these here instead of in `self._concatenate()`
            FRAME_RATE_HINT = 0.0
            FRAME_COUNT_HINT = 0

            # aliases for the main types of behavior the user can choose from/expect
            CAT_APPEND_THIS  = action in (self.actionCatBeforeThis, self.actionCatAfterThis)
            CAT_APPEND_LAST  = action in (self.actionCatBeforeLast, self.actionCatAfterLast)
            CAT_APPEND_AFTER = action in (self.actionCatAfterThis, self.actionCatAfterLast)
            CAT_DIALOG       = action in (self.actionCatDialog, self.actionCatLastDialog)
            CAT_BROWSE       = files is None and not CAT_DIALOG and not CAT_APPEND_LAST

            # what will we do to our output and original files after saving?
            open_after_save = cfg.concatenate.open
            explore_after_save = cfg.concatenate.explore
            encode_mode = cfg.concatenate.encode    # ↓ set dialog's delete setting to our own
            delete_mode = 0  # checkDeleteOriginal removed from UI

            # reuse last file list (action is disabled until at least one dialog was opened)
            if action is self.actionCatLastDialog:
                old_files = self.last_concat_files
                old_output = self.last_concat_output

            # see if we have a file list left over from a failed edit and ask if user wants to reuse it
            # NOTE: if the user opens the dialog directly, we can skip the confirmation popup
            else:
                old_output, old_files, old_settings = self.get_save_remnant('concatenate', ('', None, None))
                if old_files and (self.video in old_files or not self.video):
                    if not CAT_DIALOG and qthelpers.getPopupYesNo(
                        title='Reuse previous concatenation?',
                        text='A previous incomplete concatenation\ninvolving this file exists. Reuse?',
                        **self.get_popup_location_kwargs()
                    ).exec() != QtW.QMessageBox.Yes:
                        old_files = None
                        old_settings = None
                else:
                    old_files = None
                    old_settings = None
                if old_settings:
                    encode_mode, open_after_save, explore_after_save, delete_mode = old_settings

            # construct starting file list, if any
            if old_files:
                files = old_files
            else:
                # determine if our current file, our last file, or no file should be included by default
                # if we're adding to the current file but our current file isn't a video, just return
                if files and CAT_DIALOG:
                    base_video = ''
                else:
                    files = files or list()
                    if CAT_APPEND_LAST:             base_video = self.last_video
                    elif self.mime_type == 'video': base_video = self.video
                    elif CAT_APPEND_THIS: return show_on_statusbar('Concatenation is not implemented for audio and image files yet.', 10000)
                    else:                           base_video = ''

                # if we're adding our last file and current file together,...
                # ...add current file to `files` (which should be empty)
                if CAT_APPEND_LAST:
                    files.append(self.video)

                # see where in the file list to put our base video if we have one
            # ... (continuation of concatenate method - see main.pyw for full implementation)
            pass

    def resize_media(self):                 # https://ottverse.com/change-resolution-resize-scale-video-using-ffmpeg/ TODO this should probably have an advanced crf option
        ''' Resizes the dimensions of video files,
            and changes the length of audio files. '''
        if not self.video: return show_on_statusbar('No media is playing.', 10000)

        # reuse old width/height values for images and videos (NOT audio) if our last...
        # ...resize failed OR we're resizing something with the same dimensions as last time
        is_audio = self.mime_type == 'audio'
        base_size = (self.vwidth, self.vheight)
        if not is_audio and self.last_resize_media_base_size == base_size:
            old_size = self.get_save_remnant('resize', self.last_resize_media_values, self.video)
        else:
            old_size = self.get_save_remnant('resize', ('0', '0'), self.video)

        while True:
            width, height, _, raw_width, raw_height = self.show_size_dialog(*old_size, show_quality=False)
            if width is None: return        # dialog cancelled
            if width == 0: width = -1       # ffmpeg takes -1 as a default value, not 0
            if height == 0: height = -1     # ffmpeg takes -1 as a default value, not 0

            # cancel if size/duration is unchanged
            if is_audio:
                if round(width, 2) == 1:    # might get something like 1.0000331463797563
                    return show_on_statusbar('New length cannot be the same as the old length.', 10000)
                self.operations['resize'] = width
            elif (width <= 0 or width == self.vwidth) and (height <= 0 or height == self.vheight):
                return show_on_statusbar('New size cannot be the same as the old size.', 10000)
            else:
                self.operations['resize'] = (width, height)

            # save the width and height values to save remnants so we can restore them if needed
            old_size = (raw_width, raw_height)
            self.operations.setdefault('remnants', {})['resize'] = old_size

            if self.save(                   # doesn't really need any hints
                noun='resized media',
                filter='All files(*)',
                unique_default=True
            ):
                if not is_audio:
                    self.last_resize_media_values = old_size
                    self.last_resize_media_base_size = base_size
                break

    def rotate_video(self, action: QtW.QAction):
        if not self.video:            return show_on_statusbar('No video is playing.', 10000)
        if self.mime_type == 'audio': return show_on_statusbar('Well that would just be silly, wouldn\'t it?', 10000)

        rotation_presets = {
            self.actionRotate90:         'transpose=clock',
            self.actionRotate180:        'transpose=clock,transpose=clock',
            self.actionRotate270:        'transpose=cclock',
            self.actionFlipVertically:   'vflip',
            self.actionFlipHorizontally: 'hflip'
        }
        self.operations['rotate video'] = rotation_presets[action]
        self.save(                          # doesn't really need any hints
            noun='rotated video/image',
            filter='All files(*)',
            unique_default=True
        )

    # TODO: doing this on an audio file is somewhat unstable
    # TODO: add option to toggle "shortest" setting?
    def add_audio(self, *, path: str = None, save: bool = True, caption: str = None) -> bool:
        if not self.video: return show_on_statusbar('No media is playing.', 10000)

        try:
            if not path:
                path, cfg.lastdir = qthelpers.browseForFile(
                    lastdir=cfg.lastdir,
                    caption=caption or 'Select audio file to add'
                )
                if not path:                # cancel selected
                    return False

            self.operations['add audio'] = path
            if self.mime_type == 'image':
                filter = 'MP4 files (*.mp4);;All files (*)'
                valid_extensions = constants.VIDEO_EXTENSIONS
            elif self.mime_type == 'audio':
                filter = 'MP3 files (*.mp3);;WAV files (*.wav);;AAC files (*.aac);;All files (*)'
                valid_extensions = constants.VIDEO_EXTENSIONS + constants.AUDIO_EXTENSIONS
            else:
                filter = 'MP4 files (*.mp4);;MP3 files (*.mp3);;WAV files (*.wav);;AAC files (*.aac);;All files (*)'
                valid_extensions = constants.VIDEO_EXTENSIONS + constants.AUDIO_EXTENSIONS
            if save:                        # amplify_audio may call this, so saving is optional
                self.save(
                    noun='media with additional audio track',
                    filter=filter,
                    ext_hint='.mp4',
                    valid_extensions=valid_extensions,
                    unique_default=True
                )
            return True
        except:
            log_on_statusbar(f'(!) ADD_AUDIO FAILED: {format_exc()}')
            return False

    # https://stackoverflow.com/questions/81627/how-can-i-hide-delete-the-help-button-on-the-title-bar-of-a-qt-dialog
    def amplify_audio(self):
        if not self.video: return show_on_statusbar('No media is playing.', 10000)

        if self.mime_type == 'image' or (self.mime_type == 'video' and player.get_audio_track_count() == 0):
            show_on_statusbar('Add audio first, then you can amplify it.')
            if not self.add_audio(save=False, caption='Add audio first, then you can amplify it.'):
                return                      # add audio failed/was cancelled
            filter = 'MP4 files (*.mp4);;All files (*)'
            valid_extensions = constants.VIDEO_EXTENSIONS
            preferred_extensions = None
        elif self.mime_type == 'audio':
            filter = 'MP3 files (*.mp3);;WAV files (*.wav);;AAC files (*.aac);;All files (*)'
            valid_extensions = constants.VIDEO_EXTENSIONS + constants.AUDIO_EXTENSIONS
            preferred_extensions = constants.AUDIO_EXTENSIONS
        else:
            filter = 'MP4 files (*.mp4);;MP3 files (*.mp3);;WAV files (*.wav);;AAC files (*.aac);;All files (*)'
            valid_extensions = constants.VIDEO_EXTENSIONS + constants.AUDIO_EXTENSIONS
            preferred_extensions = None

        try:
            dialog = qthelpers.getDialog(
                title='Amplify Audio',
                deleteOnClose=False,        # TODO this MIGHT cause a memory leak
                fixedSize=(125, 105),
                flags=Qt.Tool,
                **self.get_popup_location_kwargs()
            )

            layout = QtW.QVBoxLayout(dialog)
            label = QtW.QLabel('Input desired volume \n(applies on save):', dialog)
            spin = QtW.QSpinBox(dialog)
            spin.setSuffix('%')
            spin.setMaximum(1000)
            spin.setValue(self.get_save_remnant('amplify audio', self.last_amplify_audio_value, self.video))
            for w in (label, spin):
                layout.addWidget(w)
            dialog.addButtons(layout, QtW.QDialogButtonBox.Cancel, QtW.QDialogButtonBox.Ok)

            # repeatedly open dialog until user succeeds or outright cancels (slightly less flair than the concat version)
            while dialog.exec() != QtW.QDialog.Rejected:
                self.last_amplify_audio_value = spin.value()                     # save value to re-display it next time
                self.operations['amplify audio'] = round(spin.value() / 100, 2)  # convert volume to 0-1 range
                self.operations.setdefault('remnants', {})['amplify audio'] = spin.value()
                if self.save(
                    noun='amplified video/audio',
                    filter=filter,
                    valid_extensions=valid_extensions,
                    preferred_extensions=preferred_extensions,
                    unique_default=True
                ):
                    break
        except:
            log_on_statusbar(f'(!) Audio amplification failed: {format_exc()}')
        finally:
            try:
                dialog.close()
                dialog.deleteLater()
                del dialog
                gc.collect(generation=2)
            except:
                pass

    def replace_audio(self, *, path: str = None):
        if not self.video:            return show_on_statusbar('No media is playing.', 10000)
        if self.mime_type == 'audio': return show_on_statusbar('Well that would just be silly, wouldn\'t it?', 10000)
        if self.mime_type == 'image': return self.add_audio(path=path)

        try:
            if not path:
                path, cfg.lastdir = qthelpers.browseForFile(
                    lastdir=cfg.lastdir,
                    caption='Select audio file to replace audio track with'
                )
                if not path:                                                # cancel selected
                    return
            self.operations['replace audio'] = path
            self.save(
                noun='video with replaced audio track',
                filter='MP4 files (*.mp4);;All files (*)',
                ext_hint='.mp4',
                valid_extensions=constants.VIDEO_EXTENSIONS,
                unique_default=True
            )
        except:
            log_on_statusbar(f'(!) REPLACE_AUDIO FAILED: {format_exc()}')

    # https://superuser.com/questions/268985/remove-audio-from-video-file-with-ffmpeg
    def isolate_track(self, *, audio: bool = True):
        if not self.video:            return show_on_statusbar('No media is playing.', 10000)
        if self.mime_type == 'image': return show_on_statusbar('Well that would just be silly, wouldn\'t it?', 10000)

        track_count = player.get_audio_track_count()
        if self.mime_type == 'audio':
            if track_count == 1: return show_on_statusbar('Well that would just be silly, wouldn\'t it?', 10000)
            else:                return show_on_statusbar('Track removal for audio files is not supported yet.', 10000)
        elif track_count == 0:
            if audio: return show_on_statusbar('There are no audio tracks. If you want to remove the video too, you might as well just close your eyes.', 10000)
            else:     return show_on_statusbar('There are no audio tracks left to remove.', 10000)

        if audio:
            current_track = player.get_audio_track()
            if current_track == -1:
                return show_on_statusbar('No audio track is currently selected.', 10000)
            self.operations['isolate track'] = ('Audio', max(0, current_track - 1))
            filter = 'MP4 files (*.mp4);;MP3 files (*.mp3);;WAV files (*.wav);;AAC files (*.aac);;All files (*)'
            valid_extensions = constants.VIDEO_EXTENSIONS + constants.AUDIO_EXTENSIONS
            preferred_extensions = constants.AUDIO_EXTENSIONS
        else:
            self.operations['isolate track'] = ('Video', 0)
            filter = 'MP4 files (*.mp4);;All files (*)'
            valid_extensions = constants.VIDEO_EXTENSIONS
            preferred_extensions = None

        self.save(
            noun=f'{self.operations["isolate track"][0]}',
            filter=filter,
            ext_hint='.mp3' if audio else None,                             # give hint for extension
            valid_extensions=valid_extensions,
            preferred_extensions=preferred_extensions,                      # tells a potential "save as" prompt which extensions should be default
            unique_default=True
        )

    def add_text(self):
        ''' Opens a dialog for adding text to the current media.
            Actual docstring coming in a different commit. '''
        if not constants.IS_WINDOWS:
            return qthelpers.getPopup(
                title='Adding text is Windows-only',
                text=('Adding text is Windows-only (for now). Qt doesn\'t expose font paths, and figuring out how to '
                      'get them on Windows was convoluted enough as it is.\n\nThat\'s it. That\'s the entire reason.')
            ).exec()

        if not self.video:            return show_on_statusbar('No media is playing.', 10000)
        if self.mime_type == 'audio': return show_on_statusbar('Well that would just be silly, wouldn\'t it?', 10000)
        if self.mime_type == 'image': return show_on_statusbar('Adding text to static images is not supported yet.', 10000)

        # pause video/GIF to avoid immediately generating several previews
        self.force_pause(True)

        last_preview_frame = -1
        preview_image_path = f'{THUMBNAIL_DIR}{sep}textoverlaypreview.jpg'
        try: os.remove(preview_image_path)
        except: pass

        try:
            from bin.window_text import Ui_textDialog
            dialog = qthelpers.getDialogFromUiClass(
                Ui_textDialog,
                #modal=True,
                #deleteOnClose=True,
                flags=Qt.WindowStaysOnTopHint,
                **self.get_popup_location_kwargs()
            )

            dialog.buttonColorFont.setStyleSheet('QPushButton {background-color: rgba(255,255,255,255); border: 1px solid black;}')
            dialog.buttonColorBox.setStyleSheet('QPushButton {background-color: rgba(255,255,255,0); border: 1px solid black;}')
            dialog.buttonColorShadow.setStyleSheet('QPushButton {background-color: rgba(0,0,0,150); border: 1px solid black;}')
            overlay = widgets.QTextOverlay(dialog)

            vw = self.vwidth
            vh = self.vheight
            if vw > vh: dialog.preview.setFixedSize(*scale(vw, vh, new_x=800))
            else:       dialog.preview.setFixedSize(*scale(vw, vh, new_y=800))

            dialog.preview.ratio = dialog.preview.width() / vw
            dialog.preview.overlays.append(overlay)
            dialog.preview.selected = overlay
            dialog.preview.selected.pos = QtCore.QPointF(vw / 2, vh / 2)

            def update_selected(attribute: str, value):
                setattr(dialog.preview.selected, attribute, value)
                dialog.preview.update()

            def update_alignment(button: QtW.QPushButton):
                dialog.preview.selected.alignment = {
                    dialog.buttonAlignLeft: Qt.AlignLeft,
                    dialog.buttonAlignCenter: Qt.AlignHCenter,
                    dialog.buttonAlignRight: Qt.AlignRight
                }[button]
                dialog.preview.update()

            dialog.text.textChanged.connect(lambda: update_selected('text', dialog.text.toPlainText().strip('\n')))
            dialog.comboFont.currentFontChanged.connect(lambda font: update_selected('font', font))
            dialog.spinFontSize.valueChanged.connect(lambda size: update_selected('size', size))
            dialog.spinBoxWidth.valueChanged.connect(lambda size: update_selected('bgwidth', size))
            dialog.spinShadowX.valueChanged.connect(lambda x: update_selected('shadowx', x))
            dialog.spinShadowY.valueChanged.connect(lambda y: update_selected('shadowy', y))
            dialog.buttonColorFont.clicked.connect(lambda: update_selected('color', self.show_color_picker(button=dialog.buttonColorFont, alpha=True)))
            dialog.buttonColorBox.clicked.connect(lambda: update_selected('bgcolor', self.show_color_picker(button=dialog.buttonColorBox, alpha=True)))
            dialog.buttonColorShadow.clicked.connect(lambda: update_selected('shadowcolor', self.show_color_picker(button=dialog.buttonColorShadow, alpha=True)))
            dialog.buttonGroup.buttonClicked.connect(update_alignment)

            def update_preview():
                try:
                    nonlocal last_preview_frame
                    if not exists(THUMBNAIL_DIR):
                        os.makedirs(THUMBNAIL_DIR)
                    frame = get_ui_frame()
                    if frame != last_preview_frame:
                        ffmpeg(f'-ss {frame / self.frame_rate} -i "{self.video}" -vframes 1 "{preview_image_path}"')
                        try: dialog.preview.setPixmap(QtGui.QPixmap(preview_image_path, 'JPEG'))
                        except: return
                        last_preview_frame = frame
                except:
                    logging.warning(f'(!) "Add text" dialog failed to update preview image: {format_exc()}')

            preview_timer = QtCore.QTimer()
            preview_timer.timeout.connect(update_preview)
            preview_timer.timeout.emit()
            preview_timer.start(1000)

            if dialog.exec() == QtW.QDialog.Accepted:
                marker_modes = {
                    dialog.buttonMarkerIgnore: 'ignore',
                    dialog.buttonMarkerStart:  'start',
                    dialog.buttonMarkerBoth:   'both',
                    dialog.buttonMarkerEnd:    'end'
                }
                self.operations['add text'] = {
                    'markers': marker_modes[dialog.buttonGroup_2.checkedButton()],
                    'overlays': dialog.preview.overlays
                }
                self.save(
                    noun='media with overlaid text',
                    filter='All files(*)',
                    unique_default=True
                )

            preview_timer.stop()

        except:
            log_on_statusbar(f'(!) Add-text dialog failed: {format_exc()}')

    # ---------------------
    # >>> PROMPTS <<<
    # ---------------------
    def browse_for_directory(
        self,
        *,
        lineEdit: QtW.QLineEdit = None,
        noun: str = None,
        default_path: str = None
    ) -> str | None:
        caption = f'Select {noun} directory' if noun else 'Select directory'
        path, cfg.lastdir = qthelpers.browseForDirectory(
            lastdir=cfg.lastdir,
            caption=caption,
            directory=default_path,
            lineEdit=lineEdit
        )
        return path

    def browse_for_save_file(
        self,
        *,
        lineEdit: QtW.QLineEdit = None,
        noun: str = None,
        filter: str = 'All files (*)',
        valid_extensions: tuple[str] = constants.ALL_MEDIA_EXTENSIONS,
        ext_hint: str = None,
        default_path: str = None,
        unique_default: bool = True,
        fallback_override: str = None
    ) -> str | None:
        ''' Opens a file-browsing dialog and returns a path to save to. Assigns
            path to `lineEdit` if provided. Dialog caption will read, "Save
            `noun` as..." if provided, otherwise "Save as...". If `default_path`
            if provided, it will be validated and used as the starting folder
            and filename for the dialog. If not provided or invalid, it will
            fallback to:

            1. `fallback_override` if provided (if THAT'S invalid, fallback
            to `cfg.lastdir`)
            2. `self.video` if valid and `settings.checkSaveAsUseMediaFolder`
            is checked
            3. `cfg.lastdir`

            `default_path` may be a relative path. After the above validation,
            if `default_path` included path separators but its directory did
            not exist, it will evaluated relative to the new validated path.
            Example:

            1. Provided `default_path`: "music/test.mp3"
            2. Fallback directory: "C:/Users/Name"
            3. Validated `default_path`: "C:/Users/Name/test.mp3"
            4. Potential relative `default_path`: "C:/Users/Name/Music/test.mp3"

            If `default_path` starts with '.' or '..', the validated directory
            will be tried first, then the script/executable's directory second.
            If `default_path` lacks an extension within `valid_extensions`,
            `ext_hint` will be appended to `default_path`, if provided. If
            `unique_default` is True, `default_path` will start as unique (for
            when you expect the user doesn't want to overwrite anything). '''

        if default_path:
            if os.path.isdir(default_path): dirname, basename = default_path, None
            else:                           dirname, basename = os.path.split(default_path)
        else:
            dirname = ''
            basename = None

        # validate `default_path`. use fallback if needed (see docstring)
        if not default_path or not exists(dirname):
            if fallback_override:
                fallback_override = abspath(fallback_override)
                if exists(fallback_override):
                    fallback = fallback_override
                    if os.path.isdir(fallback_override):
                        fallback += sep         # `fallback_override` exists and is a directory
                else:   fallback = cfg.lastdir  # `fallback_override` does not exist
            else:       fallback = self.video   # `fallback_override` was not provided

            if fallback:
                if settings.checkSaveAsUseMediaFolder.isChecked(): default_path = fallback
                else: default_path = os.path.join(cfg.lastdir, os.path.basename(fallback))
            else:
                default_path = cfg.lastdir

            # evaluate possible relative paths (see docstring)
            if dirname:
                potential_dir = default_path if os.path.isdir(default_path) else os.path.dirname(default_path)
                potential_path = os.path.join(potential_dir, dirname)
                if exists(potential_path):
                    default_path = os.path.join(potential_path, basename)

        if os.path.isdir(default_path):
            dirname = default_path              # simply reuse basename if it was already set
        else:
            if unique_default:
                default_path = get_unique_path(default_path)
            dirname, basename = os.path.split(default_path)

        # verify the extension on the filename we're about to use
        if basename:
            base, ext = splitext_media(basename, valid_extensions)
            if ext_hint and not ext:
                basename = base + ext_hint

        path, cfg.lastdir = qthelpers.saveFile(
            lastdir=cfg.lastdir,
            directory=dirname,
            name=basename,
            caption=f'Save {noun} as...' if noun else 'Save as...',
            filter=filter,
            selectedFilter='All files (*)',     # NOTE: this simply does nothing if this filter isn't available
            lineEdit=lineEdit
        )

        return path                             # could be None if cancel was selected

    def browse_for_subtitle_files(self, *, urls: tuple[QtCore.QUrl] = None) -> None:
        if self.mime_type == 'image': return show_on_statusbar('Well that would just be silly, wouldn\'t it?', 10000)
        if urls is None:
            urls, cfg.lastdir = qthelpers.browseForFiles(
                lastdir=cfg.lastdir,
                caption='Select subtitle file(s) to add',
                filter='Subtitle Files (*.cdg *.idx *.srt *.sub *.utf *.ass *.ssa *.aqt *.jss *.psb *.it *.sami *smi *.txt *.smil *.stl *.usf *.dks *.pjs *.mpl2 *.mks *.vtt *.tt *.ttml *.dfxp *.scc);;All files (*)',
                url=True
            )
        self.add_subtitle_files(urls)
