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

from pyplayer import constants
from pyplayer.constants import TEMP_DIR, THUMBNAIL_DIR


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
        audio_track_count = self.player.get_audio_track_count()
        audio_track_titles: list[str] = [id_and_title[-1] for id_and_title in list(self.player.get_audio_tracks())[1:]]

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

        # save remnants dict (contains stuff like dialogs we want to hang onto for later if the save fails)
        if 'remnants' in operations:
            operations['remnants'].setdefault('video', video)
            operations['remnants'].setdefault('_in_progress', True)
            self.save_remnants[start_time] = operations['remnants']
            del operations['remnants']                          # delete the operation key, not the remnant itself

        # quick pre-operation checks (we do this here instead of being the...
        # ...thread because it's kinda slow + we reuse some of these variables)
        if op_crop:
            if mime == 'audio':                                 # don't disable crop, but ignore it as an operation for audio
                log_on_statusbar('Crop mode on audio files is designed for cropping cover art through snapshots/image copying.')
                del operations['crop']                          # remove operation key
                op_crop = False
            lfp = tuple(self.vlc.last_factored_points)
            crop_selection = tuple(self.vlc.factor_point(point) for point in self.vlc.selection)
            crop_top =    min(crop_selection[0].y(), vheight - 1)
            crop_left =   min(crop_selection[0].x(), vwidth - 1)
            crop_right =  min(crop_selection[1].x(), vwidth)
            crop_bottom = min(crop_selection[2].y(), vheight)
            crop_width =  round(crop_right - crop_left)
            crop_height = round(crop_bottom - crop_top)
            if crop_width == vwidth and crop_height == vheight:  # not actually cropped -> disable crop mode and update our operations
                log_on_statusbar('Crop is the same size as the source media.')
                self.disable_crop_mode_signal.emit(False)        # False to make sure we don't log crop mode being disabled
                del operations['crop']                           # remove operation key
                op_crop = False
        if op_trim_start or op_trim_end:
            if is_static_image:                                 # NOTE: shouldn't be possible, but just in case
                log_on_statusbar('I don\'t know how you got this far, but you can\'t trim/fade a static image.')
                operations.pop('trim start', None)              # remove operation keys if they exist
                operations.pop('trim end', None)
                op_trim_start = False
                op_trim_end = False
            elif minimum == 0 and maximum == frame_count:
                log_on_statusbar('It\'s not really a "trim" if you end up with the entire duration of the file, is it?')
                operations.pop('trim start', None)              # remove operation keys if they exist
                operations.pop('trim end', None)
                op_trim_start = False
                op_trim_end = False
            elif minimum == maximum:
                log_on_statusbar('If you want to trim off 100% of the file, you might as well just delete it.')
                operations.pop('trim start', None)              # remove operation keys if they exist
                operations.pop('trim end', None)
                op_trim_start = False
                op_trim_end = False

        # check if we still have work to do after the above checks
        if not operations:
            return logging.info('(?) All pre-operation checks failed, nothing left to do.')

        # min/max are usually offset in ffmpeg for some reason, so adjust if necessary
        # NOTE: audio-only will never be truly correct. might require audio re-encoding
        if mime == 'audio':
            maximum = min(frame_count, maximum + 3)
        else:
            minimum = max(0, minimum - 2)
            maximum = maximum if maximum == frame_count else (maximum - 1)

        # ffmpeg is required after this point, so check that it's actually present, and because...
        # ...we're in a thread, we skip the warning and display it separately through a signal
        if not self.constants.verify_ffmpeg(self, warning=False, force_warning=False):
            self.show_ffmpeg_warning_signal.emit(self)
            return self.marquee('You don\'t have FFmpeg installed!')

        # get the new ctime/mtime to set out output file to (0 means don't change)
        if not op_concat:                                       # NOTE: concatenation provides its own files
            new_ctime, new_mtime = self.get_new_file_timestamps(video, dest=dest)

        # NEVER directly save to our destination - always to a unique temp path. makes cleanup 100x easier
        intermediate_file = video                               # the path to the file that will be receiving all changes between operations
        final_dest = dest                                       # save the original dest so we can rename our temporary dest back later
        dest = self.util.add_path_suffix(dest, '_temp', unique=True)      # add _temp to dest, in case dest is the same as our base video

        logging.info(f'Saving file to "{final_dest}"')
        logging.debug(f'temp-dest={dest}, video={video}, delete={delete_mode}, operations={operations}')
        temp_paths = []                                         # some edits generate excess files we'll need to delete later

        # lock both temporary and actual destination in the player
        self.locked_files.add(dest)
        self.locked_files.add(final_dest)

        # open handle to our destination to lock it on the system
        DEST_ALREADY_EXISTED = self.util.exists(final_dest)
        dest_handle = open(final_dest, 'a')

    # --- Apply operations to media ---
        # TODO: GIFs should probably use Pillow for their operations
        # NOTE: ABSOLUTELY EXTREMELY IMPORTANT!!! update any relevant properties such as...
        # ...vheight/vwidth, is_gif/is_static_image, etc. as SOON as an operation is done!!!
        try:
            edit = self.widgets.Edit(final_dest)
            edit.frame_rate = frame_rate
            edit.frame_count = frame_count_raw
            edit.operation_count = len(operations)
            edit.audio_track_titles = audio_track_titles        # NOTE: ignored on edits that manually specify `-map`
            if op_trim_start and op_trim_end:                   # account for trimming taking up two keys
                edit.operation_count -= 1
            self.add_edit(edit)

            # static images are cached and can be deleted independent of pyplayer. if this happens, save the cached...
            # ...QPixmap to a temp file and delete it later (we'll assume the user wants the original to stay gone)
            # NOTE: we do this even if we're not sure the image will actually be used (like if we're concatenating)
            if is_static_image and video and not self.util.exists(video):
                temp_image_path = self.util.add_path_suffix(video, '_tempimage', unique=True)
                temp_paths.append(temp_image_path)
                intermediate_file = temp_image_path
                with self.util.get_PIL_Image().fromqpixmap(self.image_player.art) as image:
                    image.save(temp_image_path)

            # the code block formerly known as `self._concatenate()`
            if op_concat:
                log_noun = 'Concatenation'
                files = op_concat['files']
                open_after_save = op_concat['open']
                explore_after_save = op_concat['explore']
                delete_mode = op_concat['delete_mode']

                new_ctime, new_mtime = self.get_new_file_timestamps(*files, dest=dest)
                edit.frame_rate = op_concat['frame_rate_hint']
                edit.frame_count = op_concat['frame_count_hint']
                if op_concat['encode']:
                    if not self.constants.FFPROBE:                             # couldn't probe files -> use special text and indeterminate progress
                        edit.percent_format = '(re-encode requested, this will take a while)'
                        self.set_save_progress_max_signal.emit(0)

                    inputs = '-i "' + '" -i "'.join(files)      # ↓ "[0:v:0][0:a:0][1:v:0][1:a:0]", etc.
                    funnysquares = ''.join(f'[{i}:v:0][{i}:a:0]' for i in range(len(files)))
                    filtercmd = f'-filter_complex "{funnysquares}concat=n={len(files)}:v=1:a=1[outv][outa]"'
                    cmd = f'{inputs}" {filtercmd} -map "[outv]" -map "[outa]" -vsync 2 %out'
                    edit.ffmpeg(None, cmd, dest, 'Concatenating', 'Preparing files for concatenation...')

                # no re-encoding, concatenate (almost instantly) using stream copying
                else:
                    # immediately and directly set text while we do intermediate step
                    edit.start_text = edit.text = 'Preparing files for concatenation...'
                    edit.give_priority(conditional=True)        # update priority so the UI's text refreshes

                    # convert files to MPEG-TS for easier concatenation
                    intermediate_files = []
                    for file in files:
                        temp_filename = file.replace(':', '').replace('/', '').replace('\\', '') + '.ts'
                        intermediate_file = f'{self.constants.TEMP_DIR}{self.constants.sep}{temp_filename}'
                        try: os.remove(intermediate_file)
                        except: pass
                        intermediate_files.append(intermediate_file)
                        self.util.ffmpeg(f'-i "{file}" -c copy -bsf:v h264_mp4toannexb -f mpegts "{intermediate_file}"')

                    # concatentate with ffmpeg
                    if self.mime_type == 'audio': cmd = f'-i "concat:{"|".join(intermediate_files)}" -c copy %out'
                    else: cmd = f'-i "concat:{"|".join(intermediate_files)}" -c copy -video_track_timescale 100 -bsf:a aac_adtstoasc -movflags faststart -f mp4 %out'
                    edit.ffmpeg(None, cmd, dest, 'Concatenating', 'Preparing files for concatenation...')
                    for intermediate_file in intermediate_files:
                        try: os.remove(intermediate_file)
                        except: pass

            # we're overlaying text over the video/gif
            # HACK: For ~5 days, I tried to figure out how to consistently and accurately translate the preview generated with QPainter/QFontMetrics...
            # ...to what FFmpeg's drawtext filter expects. Modern (like so modern I don't think they're in public versions yet) releases of FFmpeg...
            # ...now have `y_align` and `text_align` parameters which fix most of my issues, but I didn't want to make an unstable beta branch...
            # ...a requirement. I assumed that doing this correctly was literally impossible with the arbitrarily limited infomation QFontMetrics...
            # ...exposes to you, so I gave up on that after an hour and decided on a pretty wild hack: Re-painting the preview onto a QPixmap...
            # ...before saving, then looping over the pixels to find the true coordinates of the text so that FFmpeg can place them correctly,...
            # ...on top of having to do a bunch of silly math with terrible numbers to get text alignment figured out. 5 days of trial-and-error...
            # ...later, I got everything mostly working at about 90% accuracy, before realizing that I could just use FFmpeg's image overlaying...
            # ...filter to overlay the QPixmap I'm already generating. All I have to do is apply some of these hacks to the preview image instead...
            # ...of the output, and it'll be 100% accurate no matter what AND we'll be able to do so much more, like overlaying actual images...
            # ...or doing outlines/blurs and stuff. Kinda sad with how close I was to getting this (almost) perfect, but it's 100% for the best.
            #
            # Anyways that's why this code is unfinished garbage, and also why I'm committing it regardless. Thanks for coming to my TED talk.
            #
            # -vf "drawtext=fontfile=/path/to/font.ttf:text='Text testing, here!':fontcolor=white:fontsize=24:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-text_w)/2:y=(h-text_h)/2"
            if op_add_text:                                     # 'ignore', 'start', 'end', 'both'
                # we are using the start marker for our text (NOTE: NOT IMPLEMENTED)
                #if op_add_text['markers'] in ('start', 'both'):
                #    if op_trim_start:
                #        del operations['trim start']
                #        op_trim_start = False
                #
                ## we are using the end marker for our text (NOTE: NOT IMPLEMENTED)
                #if op_add_text['markers'] in ('end', 'both'):
                #    if op_trim_end:
                #        del operations['trim start']
                #        op_trim_start = False
                filters = []
                pixmap = self.QtGui.QPixmap(self.vwidth, self.vheight)
                painter = self.QtGui.QPainter(pixmap)
                try:
                    for overlay in op_add_text['overlays']:
                        if not overlay.text.strip():
                            continue

                        top_line_adjusted_center = 0
                        text = overlay.text.strip('\n')
                        lines = text.split('\n')

                    # >>> see HACK above
                        # use manual labor to figure out font filepath that Qt refuses to expose
                        font = self.util.get_font_path(overlay.font.family())
                        if font:
                            font = font.replace('\\', '/')
                            font_param = f'fontfile=\'{font}\''
                        else:                                   # hope the user has a special build of ffmpeg that supports the "font" parameter
                            show_on_statusbar(f'(!) No font file found for "{overlay.font.family()}"')
                            font_param = f'font=\'{overlay.font.family()}\''

                        overlay.font.setPixelSize(overlay.size)
                        pixmap.fill(self.Qt.transparent)
                        painter.setFont(overlay.font)
                        painter.setPen(overlay.color)

                        font_metrics = painter.fontMetrics()
                        line_height = font_metrics.ascent() * 1.1
                        text_size = font_metrics.size(0, text)
                        text_rect = self.QtCore.QRect(overlay.pos.toPoint(), text_size)
                        #if overlay.centered_vertically:
                        #    text_rect.moveCenter(self.QtCore.QPoint(text_rect.x(), vheight / 2))

                        painter.drawText(text_rect, overlay.alignment | self.Qt.AlignTop, text)
                        image = self.util.get_PIL_Image().fromqpixmap(pixmap)
                        pixels = image.load()
                        local_pos = overlay.pos.toPoint()

                        # loop over pixels until visible one is found (start from Qt's coordinates to massively improve performance)
                        top_y = vheight * 2                     # use starting numbers outside the dimensions of the media
                        min_x = vwidth * 2
                        if len(lines) > 1 or not overlay.centered_vertically:
                            for y in range(local_pos.y(), min(image.height, local_pos.y() + text_size.height())):
                                for x in range(local_pos.x(), min(image.width, local_pos.x() + text_size.width())):
                                    if pixels[x, y][-1] != 0:
                                        logging.info(f'Overlay\'s first non-transparent pixel found at ({x}, {y}) -> {pixels[x, y]}')
                                        min_x = min(min_x, x)
                                        top_y = min(top_y, y)
                                        break
                                #else:                           # `else` means we didn't break the inner-loop (no pixels on this row)
                                #    continue
                                #break                           # break outer-loop if we broke the inner-loop
                            #else:                               # `else` means we didn't break the outer-loop either (no pixels at all)
                            if top_y > vheight:
                                logging.info(f'Overlay isn\'t actually visible on the screen (text: {text})')
                                continue                        # jump to the next overlay

                        text_rect.setLeft(min_x)
                        text_rect.setTop(top_y)
                        text_rect.setWidth(max(font_metrics.tightBoundingRect(line).width() for line in lines))
                        #text_rect.setWidth(font_metrics.size(0, text).width())
                        #text_bounding_rect = font_metrics.tightBoundingRect(text)
                        #text_rect.setWidth(text_bounding_rect.width())
                        #text_rect.setHeight(text_bounding_rect.height())
                        print('min_x, top_y, and text_rect', min_x, top_y, text_rect)
                    # >>> main part of HACK finished

                        for line_number, line in enumerate(lines):
                            if not line.strip():
                                continue

                            line_size = font_metrics.size(0, line)
                            #line_rect = self.QtCore.QRect(text_rect.topLeft(), line_size)
                            line_width = font_metrics.horizontalAdvance(line)

                            bounding_rect = font_metrics.tightBoundingRect(line)
                            print('ascent', line_height, 'size', line_size, 'width', line_width, 'tightBoundingRect', bounding_rect)

                            #bounding_rect.width

                            #line_rect = self.QtCore.QRect(text_rect.topLeft(), self.QtCore.QSize(line_size.width(), line_height))
                            #line_rect = self.QtCore.QRect(text_rect.topLeft(), self.QtCore.QSize(bounding_rect.width(), line_height))
                            line_rect = self.QtCore.QRect(text_rect.topLeft(), self.QtCore.QSize(bounding_rect.width(), bounding_rect.height()))

                            if line_number == 0:
                                #top_line_rect = line_rect
                                if overlay.centered_vertically:
                                    top_line_adjusted_center = (vheight / 2) - (line_height * len(lines) / 2) + (line_height / 4)
                                else:
                                    #top_line_adjusted_center = top_y + (bounding_rect.height() / 2)
                                    top_line_adjusted_center = top_y
                                #elif len(lines) == 1:
                                #    top_line_adjusted_center = top_y + (bounding_rect.height() / 2)
                                #else:
                                #    top_line_adjusted_center = line_rect.bottom() - (line_height / 2)
                            #    if overlay.centered_vertically:
                            #        if len(lines) == 1: y = '(h-text_h)/2'
                            #        else:               y = y - ((line_height * len(lines)) / 4)
                            #    else:                   y = y + 1
                            #else:
                            #    line_rect.moveCenter(self.QtCore.QPoint(
                            #        text_rect.center().x(),
                            #        top_line_rect.center().y() + (line_height * line_number)
                            #    ))
                            #    y = line_rect.y()

                            #if overlay.centered_vertically and len(lines) == 1:
                            if overlay.centered_vertically:
                                if len(lines) == 1:
                                    y = '(h-text_h)/2'
                                else:
                                    line_rect.moveCenter(self.QtCore.QPoint(
                                        text_rect.center().x(),
                                        #top_line_rect.center().y() + (line_height * line_number)
                                        int(top_line_adjusted_center + (line_height * line_number))
                                    ))
                                    y = line_rect.bottom() - bounding_rect.height()
                            else:
                                #line_rect.moveCenter(self.QtCore.QPoint(
                                #    text_rect.center().x(),
                                #    #top_line_rect.center().y() + (line_height * line_number)
                                #    int(top_line_adjusted_center + (line_height * line_number))
                                #))
                                #line_rect.moveTop(int(top_line_adjusted_center + (line_height * line_number)))
                                #y = line_rect.y()
                                #y = line_rect.bottom() - (line_height / 2)
                                #y = line_rect.bottom() - line_height
                                #y = line_rect.bottom() - line_size.height()
                                #y = line_rect.bottom() - bounding_rect.height()
                                #y = int(top_line_adjusted_center + (line_height * line_number))
                                y = int(top_line_adjusted_center + (line_height * line_number))

                            # attempt to manually align each line of text (FFmpeg only supports left-align)
                            if overlay.centered_horizontally:   # use FFmpeg's built-in variables to escape the garbage below if possible
                                x = '(w-text_w)/2'
                            else:
                                if overlay.alignment == self.Qt.AlignLeft:
                                    #x = overlay.pos.x()
                                    x = text_rect.left()
                                    print('ALIGNLEFT', x)
                                elif overlay.alignment == self.Qt.AlignHCenter:
                                    #x = text_rect.center().x() - (line_size.width() / 2)
                                    x = text_rect.center().x() - (bounding_rect.width() / 2)
                                    print('ALIGNHCENTER', text_rect, text_rect.center().x(), bounding_rect.width() / 2, x)
                                elif overlay.alignment == self.Qt.AlignRight:            # TODO: My right-align code just doesn't work and I don't understand why.
                                    #x = top_line_rect.right() - line_size.width()  # Thankfuly, now I don't HAVE to understand why. See you never, drawtext.
                                    #x = text_rect.right() - line_size.width()
                                    x = text_rect.right() - bounding_rect.width() - bounding_rect.left()
                                    print('ALIGNRIGHT', x)

                            # escape stuff drawtext doesn't like -> https://stackoverflow.com/a/71635094
                            line = (line.replace("\\", "\\\\")
                                        .replace('"', '""')
                                        .replace("'", "''")
                                        .replace("%", "\\%")
                                        .replace(":", "\\:"))

                            filter_params = [
                                f'text=\'{line}\'',
                                f'x={x}',
                                f'y={y}',
                                f'fontsize={overlay.size}',
                                f'fontcolor={overlay.color.name()}@{overlay.color.alpha() / 255}',
                                font_param
                                #'y_align=font'                 # see HACK comment above for why we can't use this
                            ]

                            # add background box
                            if overlay.bgcolor.alpha():
                                filter_params.append('box=1')
                                filter_params.append(f'boxcolor={overlay.bgcolor.name()}@{overlay.bgcolor.alpha() / 255}')
                                filter_params.append(f'boxborderw={overlay.bgwidth}')

                            # add drop-shadow
                            if overlay.shadowx or overlay.shadowy:
                                filter_params.append(f'shadowcolor={overlay.shadowcolor.name()}@{overlay.shadowcolor.alpha() / 255}')
                                filter_params.append(f'shadowx={overlay.shadowx}')
                                filter_params.append(f'shadowy={overlay.shadowy}')

                            # see HACK comment above for why we can't use this
                            #alignments = {
                            #    int(self.Qt.AlignLeft): 'L',
                            #    int(self.Qt.AlignHCenter): 'C',
                            #    int(self.Qt.AlignRight): 'R',
                            #}
                            #filter_params.append(f'text_align={alignments[overlay.alignment]}+M')

                            filters.append(f'drawtext={":".join(filter_params)}')
                finally:                                        # NOTE: IMPORTANT!!! we MUST close the painter manually...
                    painter.end()                               # ...or we'll crash to desktop when the thread closes!!!

                cmd = f'-i %in -vf "{",".join(filters)}" -codec:a copy %out'
                intermediate_file = edit.ffmpeg(intermediate_file, cmd, dest, 'Overlaying text')

            # trimming and fading (controlled using the same start/end points)
            # TODO: there are scenarios where cropping and/or resizing first is better
            #       - how should we handle reordering of operations?
            if op_trim_start or op_trim_end:

                # trim -> https://trac.ffmpeg.org/wiki/Seeking TODO: -vf trim filter should be used in here
                if self.is_trim_mode():
                    trim_duration = (maximum - minimum) / frame_rate

                    # animated GIFs don't need a lot of the extra bits
                    if is_gif:
                        cmd = '-i %in '
                        if minimum > 0:           cmd += f'-ss {minimum / frame_rate} '
                        if maximum < frame_count: cmd += f'-to {maximum / frame_rate} '

                    else:
                        if mime == 'audio':                     # audio re-encoding should probably be an option in the future
                            precise = False

                        else:
                            # see if we should use auto-precise mode regardless of user's preference
                            # (always use precise trimming for very short media or short clips on semi-short media)
                            if duration <= 10 or (duration <= 30 and trim_duration <= 5):
                                log_on_statusbar('Precise trim auto-detected (short trims on short media always use precise trimming).')
                                precise = True

                            # don't use auto-precise mode. either use preferred mode or show dialog for user to pick mode
                            else:
                                if self.actionTrimPickEveryTime.isChecked() or not self.cfg.trimmodeselected:
                                    self.trim_mode_selection_cancelled = False
                                    self.cfg.trimmodeselected = False
                                    self.show_trim_dialog_signal.emit()
                                    while not self.cfg.trimmodeselected:
                                        sleep(0.1)
                                    if self.trim_mode_selection_cancelled:
                                        successful = False      # user hit X on the trim dialog
                                        return log_on_statusbar('Trim cancelled.')

                            start_time = get_time()         # reset start_time to undo time spent waiting for dialog
                            requires_precision = extension in self.constants.SPECIAL_TRIM_EXTENSIONS and mime != 'audio'
                            precise = requires_precision or self.trim_mode_action_group.checkedAction() is self.actionTrimPrecise
                            if not precise: log_on_statusbar('Imprecise trim requested.')
                            else:           log_on_statusbar('Precise trim requested (this is a time-consuming task).')

                        # construct FFmpeg command based on starting/ending frame, precision mode, and mime type
                        cmd = ''
                        if minimum:
                            trim_start = minimum / frame_rate
                            cmd = f'-ss {trim_start} -i %in '
                        if maximum < frame_count:
                            if not precise:
                                maximum -= 1
                            if minimum: cmd += f' -to {(trim_duration)} '
                            else:       cmd += f' -i %in -to {(maximum / frame_rate)} '
                        if mime != 'audio':
                            if precise: cmd += ' -c:v libx264 -c:a aac'
                            else:       cmd += ' -c:v copy -c:a copy -avoid_negative_ts make_zero'
                        else:           cmd += ' -codec copy -avoid_negative_ts make_zero'

                    duration = trim_duration                                        # update duration
                    edit.frame_count = frame_count = maximum - minimum              # update frame count
                    intermediate_file = edit.ffmpeg(intermediate_file, cmd, dest, 'Trimming', 'Seeking to start of trim...')

                # fade (using trim buttons as fade points) -> https://dev.to/dak425/add-fade-in-and-fade-out-effects-with-ffmpeg-2bj7
                # TODO: ffmpeg fading is actually very versatile, this could be WAY more sophisticated
                else:
                    log_on_statusbar('Fade requested (this is a time-consuming task).')
                    mode = {self.actionFadeBoth: 'both', self.actionFadeVideo: 'video', self.actionFadeAudio: 'audio'}[self.trim_mode_action_group.checkedAction()]
                    fade_cmd_parts = []
                    if mode == 'video' or mode == 'both':                           # fade video to/from black
                        fade_parts = []
                        if minimum > 0:
                            seconds = minimum / frame_rate
                            fade_parts.append(f'fade=t=in:st=0:d={seconds}')        # `d` defaults to ~1 second
                        if maximum < frame_count:
                            seconds = maximum / frame_rate
                            delta = duration - seconds - 0.1                        # TODO: 0.1 offset since fade out sometimes doesn't finish on time
                            fade_parts.append(f'fade=t=out:st={seconds}:d={delta}')
                        if fade_parts:
                            fade_cmd_parts.append(f'-vf "{",".join(fade_parts)}{" -c:a copy" if mode != "both" else ""}"')
                    if mode == 'audio' or mode == 'both':                           # fade audio in/out
                        fade_parts = []
                        if minimum > 0:
                            seconds = minimum / frame_rate
                            fade_parts.append(f'afade=t=in:st=0:d={seconds}')       # `d` defaults to ~1 second
                        if maximum < frame_count:
                            seconds = maximum / frame_rate
                            delta = duration - seconds - 0.1                        # TODO: 0.1 offset since fade out sometimes doesn't finish on time
                            fade_parts.append(f'afade=t=out:st={seconds}:d={delta}')
                        if fade_parts:
                            fade_cmd_parts.append(f'-af "{",".join(fade_parts)}{" -c:v copy" if mode != "both" and mime == "video" else ""}"')
                    if fade_cmd_parts:
                        cmd = f'-i %in {" ".join(fade_cmd_parts)}'
                        intermediate_file = edit.ffmpeg(intermediate_file, cmd, dest, 'Fading')

            # crop -> https://video.stackexchange.com/questions/4563/how-can-i-crop-a-video-with-ffmpeg
            if op_crop:     # ffmpeg cropping is not 100% accurate, final dimensions may be off by ~1 pixel
                log_on_statusbar('Cropping...')                                     # -filter:v "crop=out_w:out_h:x:y"
                cmd = f'-i %in -filter:v "crop={crop_width}:{crop_height}:{round(crop_left)}:{round(crop_top)}"'
                if is_static_image:
                    with self.util.get_image_data(intermediate_file, extension) as image:
                        image = image.crop((round(lfp[0].x()), round(lfp[0].y()),   # left/top/right/bottom (crop takes a tuple)
                                            round(lfp[3].x()), round(lfp[3].y())))  # round QPointFs
                        image.save(dest, format=extension)                          # specify `format` in case `dest`'s extension is unexpected
                    intermediate_file = dest
                else:
                    cmd = f'-i %in -filter:v "crop={crop_width}:{crop_height}:{round(crop_left)}:{round(crop_top)}"'
                    intermediate_file = edit.ffmpeg(intermediate_file, cmd, dest, 'Cropping')
                vwidth = round(crop_width) - 1                                      # update dimensions
                vheight = round(crop_height) - 1

            # resize video/GIF/image, or change audio file's tempo
            # TODO: this is a relatively fast operation and SHOULD be done much sooner but that requires...
            # ...dynamic ordering of operations (see above) and adjusting `crop_selection`/`lfp` and I'm lazy
            if op_resize is not None:       # audio -> https://stackoverflow.com/q/25635941/13010956
                log_note = ' (this is a time-consuming task)' if mime == 'video' else ' (this should be a VERY quick operation)' if mime == 'audio' else ''
                log_on_statusbar(f'{mime.capitalize()} resize requested{log_note}.')
                if mime == 'audio':         # for audio: only duration (as a multiplier, e.g. 1.5x) is given
                    duration_factor = op_resize
                    edit.frame_count = (duration / duration_factor) * frame_rate
                    cmd = f'-i %in -filter:a atempo="{duration_factor}"'
                    intermediate_file = edit.ffmpeg(intermediate_file, cmd, dest, 'Adjusting tempo')
                else:                       # for videos/images: (width, height) tuple
                    vwidth, vheight = self.util.scale(vwidth, vheight, *op_resize)
                    if is_static_image:     # ^ pillow can't handle 0/-1 and ffmpeg is stupid (see below) -> scale right away
                        with self.util.get_image_data(intermediate_file, extension) as image:
                            image = image.resize((vwidth, vheight))                 # resize image
                            image.save(dest, format=extension)
                    else:
                        # ffmpeg cannot resize to dimensions that aren't divisible by 2 (for some reason)
                        # using -1 will STILL error out if the dimensions IT CHOOSES aren't divisible by 2
                        # this can technically be fixed using -2 (https://stackoverflow.com/a/72589591)...
                        # ...but we need to scale the dimensions ourselves anyways so it doesn't matter
                        vwidth -= int(vwidth % 2 != 0)
                        vheight -= int(vheight % 2 != 0)
                        cmd = f'-i %in -vf "scale={vwidth}:{vheight}" -crf 28 -c:a copy'
                        intermediate_file = edit.ffmpeg(intermediate_file, cmd, dest, 'Resizing')

            # rotate video/GIF/image
            # TODO: this should use Pillow for images/GIFs but I'm lazy
            # NOTE: ^ `get_PIL_safe_path` only still exists because of this
            if op_rotate_video is not None:
                log_on_statusbar('Video rotation/flip requested (this is a time-consuming task).')
                cmd = f'-i %in -vf "{op_rotate_video}" -crf 28 -c:a copy'
                if is_static_image:
                    with self.util.get_PIL_safe_path(original_path=video, final_path=dest) as temp_path:
                        edit.ffmpeg(intermediate_file, cmd, temp_path, 'Rotating')
                        intermediate_file = dest
                else:
                    intermediate_file = edit.ffmpeg(intermediate_file, cmd, dest, 'Rotating')
                if op_rotate_video == 'transpose=clock' or op_rotate_video == 'transpose=cclock':
                    vwidth, vheight = vheight, vwidth           # update dimensions

            # replace audio (entirely - TODO: track-by-track replacement)
            if op_replace_audio is not None:
                log_on_statusbar('Audio replacement requested.')
                audio = op_replace_audio    # TODO -shortest (before output) results in audio cutting out ~1 second before end of video despite the audio being longer
                cmd = f'-i %in -i "{audio}" -c:v copy -map 0:v:0 -map 1:a:0'
                intermediate_file = edit.ffmpeg(intermediate_file, cmd, dest, 'Replacing audio')

            # add audio track - adding audio to images or GIFs will turn them into videos
            # https://superuser.com/questions/1041816/combine-one-image-one-audio-file-to-make-one-video-using-ffmpeg
            if op_add_audio is not None:    # TODO :duration=shortest (after amix=inputs=2) has same issue as above
                audio = op_add_audio
                if is_static_image:         # static images
                    log_on_statusbar('Adding audio to static image.')
                    is_static_image = False                     # mark that this is no longer an image
                    if vwidth % 2 != 0 or vheight % 2 != 0:     # static image dimensions must be divisible by 2... for some reason
                        try:
                            with self.util.get_image_data(intermediate_file, extension) as image:
                                logging.info(f'Image dimensions aren\'t divisible by 2, cropping a pixel from the top and/or left and saving to {intermediate_file}.')
                                left = int(vwidth % 2 != 0)
                                top = int(vheight % 2 != 0)
                                image = image.crop((left, top, vwidth, vheight))    # left/top/right/bottom (crop takes a tuple)
                                image.save(intermediate_file, format=extension)     # specify `format` in case `intermediate_file`'s extension is unexpected
                                vwidth -= left
                                vheight -= top
                        except:
                            successful = False
                            return log_on_statusbar(f'(!) Failed to crop image that isn\'t divisible by 2: {format_exc()}')
                    edit.frame_count = int(self.util.get_audio_duration(audio) * 25)          # ffmpeg defaults to using 25fps for this
                    cmd = f'-loop 1 -i %in -i "{audio}" -c:v libx264 -tune stillimage -c:a aac -b:a 192k -pix_fmt yuv420p -shortest'
                    intermediate_file = edit.ffmpeg(intermediate_file, cmd, dest, 'Adding audio track')
                elif is_gif:                # gifs
                    log_on_statusbar('Adding audio to animated GIF (final video duration may not exactly line up with audio).')
                    is_gif = False                              # mark that this is no longer a gif
                    edit.frame_count = int(self.util.get_audio_duration(audio) * frame_rate)
                    cmd = f'-stream_loop -1 -i %in -i "{audio}" -filter_complex amix=inputs=1 -shortest'
                    intermediate_file = edit.ffmpeg(intermediate_file, cmd, dest, 'Adding audio track')
                else:                       # video/audio TODO: adding "-stream_loop -1" and "-shortest" sometimes cause endless videos because ffmpeg is garbage
                    log_on_statusbar('Additional audio track requested.')
                    the_important_part = '-map 0:v:0 -map 1:a:0 -c:v copy' if (mime == 'video' and audio_track_count == 0) else '-filter_complex amix=inputs=2'
                    cmd = f'-i %in -i "{audio}" {the_important_part}'               # ^ use special cmd for audio-less videos
                    intermediate_file = edit.ffmpeg(intermediate_file, cmd, dest, 'Adding audio track')

            # isolate audio or all video tracks (does not turn file into an image/GIF)
            if op_isolate_track is not None:                    # NOTE: This can degrade audio quality slightly.
                noun, track = op_isolate_track                  # NOTE: video can keep all its tracks, but audio MUST pick just one
                log_on_statusbar(f'{noun}-track removal requested.')
                cmd = f'-i %in -q:a 0 -map 0:a:{track}' if noun == 'Audio' else '-i %in -c copy -an'
                intermediate_file = edit.ffmpeg(intermediate_file, cmd, dest, f'Removing {noun.lower()} track')

            # amplify audio (TODO: do math to chain several of these together at once to circumvent the max volume limitation)
            if op_amplify_audio is not None:
                log_on_statusbar('Audio amplification requested.')
                cmd = f'-i %in -filter:a "volume={op_amplify_audio}"'
                intermediate_file = edit.ffmpeg(intermediate_file, cmd, dest, 'Amplifying audio')

        # the code block formerly known as `self.cleanup_edit_exception()`
        except Exception as error:
            successful = False
            self.qthelpers.deleteTempPath(dest, 'FFmpeg file')

            # ffmpeg had a memory error
            text = str(error)
            if 'malloc of size' in text:
                start_index = text.find('malloc of size') + 14
                size = int(text[start_index:text.find('failed', start_index)])
                if size < 1048576:      size_label = f'{size / 1024:.0f}kb'
                elif size < 1073741824: size_label = f'{size / 1048576:.2f}mb'
                else:                   size_label = f'{size / 1073741824:.2f}gb'
                msg = (f'FFmpeg failed to allocate {size_label} of RAM. Rarely, this'
                       '\nmay happen even when plenty of free RAM is available.'
                       '\n\nIf the issue persists, try the following:'
                       '\n • Check if the issue happens with other files'
                       '\n • Restart PyPlayer'
                       '\n • Restart your computer'
                       '\n • Reinstall FFmpeg'
                       '\n • Pray'
                       '\n\nNo changes have been made. Feel free to try again.')
                self.popup_signal.emit(                         # TODO it *might* be nice to have retry/cancel options
                    dict(
                        title='FFmpeg error',
                        text=msg,
                        icon='warning',
                        **self.get_popup_location_kwargs()
                    )
                )

            # we tried to concat videos with different dimensions (if we got this far, assume FFprobe isn't available)
            # -> start by reopening concat dialog with previous files (NOTE: state won't be fully restored)
            elif 'do not match the corresponding output link' in text:
                self.concatenate_signal.emit(None, op_concat['files'])
                header = ('All files must have the same dimensions for re-encoded concatenation.\n'
                          'You\'ll need to crop or resize the offending files individually.')
                self.popup_signal.emit(
                    dict(
                        title='Concatenation cancelled!',
                        text=header,
                        icon='warning',
                        flags=self.Qt.WindowStaysOnTopHint,          # needed so it appears over the concat dialog
                        **self.get_popup_location_kwargs()
                    )
                )

            # edit was intentionally cancelled by the user
            elif text == 'Cancelled.':
                if not start_time: log_on_statusbar(f'{log_noun or "Save"} cancelled.')
                else: log_on_statusbar(f'{log_noun or "Save"} cancelled after {self.util.get_verbose_timestamp(get_time() - start_time)}.')

            # edit failed for an unknown reason
            else:
                if not start_time: log_on_statusbar(f'(!) {log_noun.upper() or "SAVE"} FAILED: {format_exc()}')
                else: log_on_statusbar(f'(!) {log_noun.upper() or "SAVE"} FAILED AFTER {self.util.get_verbose_timestamp(get_time() - start_time).upper()}: {format_exc()}')

        # --- Post-edit cleanup & opening our newly edited media ---
        finally:
            try:
                # close handle to destination. if there wasn't already a...
                # ...file there, delete the temp file our handle created
                self.util.close_handle(dest_handle, delete=not DEST_ALREADY_EXISTED)

                # clean up temp paths if we have any
                for path in temp_paths:
                    if self.util.exists(path):
                        self.qthelpers.deleteTempPath(path, 'edit-path')

                # confirm/validate/cleanup our operations
                if operations and successful:
                    to_delete = video if not op_concat else op_concat['files']
                    true_dest = self._cleanup_edit_output(dest, final_dest, new_ctime, new_mtime, delete_mode, to_delete, log_noun)
                    if not true_dest:
                        self.qthelpers.deleteTempPath(dest, 'FFmpeg file')
                        return

                    # auto-open output if desired or we're watching the media that just got edited
                    if (open_after_save) if open_after_save is not None else (self.video == video):
                        remember_old_file = not op_concat and self.settings.checkCycleRememberOriginalPath.checkState() == 2
                        self.open_from_thread(
                            file=true_dest,
                            _from_cycle=True,           # skips unnecessary validation (like checking if `file` is locked)
                            _from_edit=True,
                            focus_window=self.settings.checkFocusOnEdit.isChecked(),
                            pause_if_focus_rejected=self.settings.checkEditFocusRejectedPause.isChecked(),
                            beep_if_focus_rejected=self.settings.checkEditFocusRejectedBeep.isChecked(),
                            update_original_video_path=not remember_old_file
                        )                               # gifs will often just... pause themselves after an edit
                        if is_gif:                      # -> this is the only way i've found to fix it
                            self.force_pause_signal.emit(False)

                    # handle what to do if the newly edited file is not auto-opened
                    else:
                        if self.settings.checkEditOpenRejectedBeep.isChecked():
                            self.app.beep()
                        if self.settings.checkEditOpenRejectedAddToRecents.isChecked():
                            recent_files = self.recent_files
                            if true_dest in recent_files:
                                recent_files.append(recent_files.pop(recent_files.index(true_dest)))
                            else:                       # ^ move pre-existing recent file to front
                                recent_files.append(true_dest)
                                max_len = self.settings.spinRecentFiles.value()
                                self.recent_files = recent_files[-max_len:]
                        if self.settings.checkTextOnSave.isChecked():
                            show_on_player(f'{log_noun or "Changes"} saved to {true_dest}.')

                        # our current file might have been marked -> manually update action/button
                        current_video_is_marked = self.video in self.marked_for_deletion
                        self.actionMarkDeleted.setChecked(current_video_is_marked)
                        self.buttonMarkDeleted.setChecked(current_video_is_marked)

                    # open output in explorer if desired
                    if explore_after_save:
                        self.qthelpers.openPath(true_dest, explore=True)

                    # add our successful edit to our recent list (max of 25)
                    recent_edits = self.recent_edits
                    if true_dest in recent_edits:       # move pre-existing recent file to front
                        recent_edits.append(recent_edits.pop(recent_edits.index(true_dest)))
                    else:
                        recent_edits.append(true_dest)
                        max_len = self.settings.spinRecentEdits.value()
                        self.recent_edits = recent_edits[-max_len:]

                    # clear out inactive save remnants from this edit or earlier in a thread-safe manner
                    # this way, we only clear out remnants that have had edits started and finished after they were created
                    logging.debug(f'Clearing any remnants older than {start_time}')
                    remnant_times = sorted(self.save_remnants.keys())
                    for remnant_time in remnant_times:
                        if remnant_time > start_time:
                            break
                        try:                            # ignore marker for this edit's remnant
                            if remnant_time == start_time or not self.save_remnants[remnant_time].get('_in_progress', False):
                                logging.debug(f'Removing remnant from {remnant_time}')
                                del self.save_remnants[remnant_time]
                        except:
                            logging.warning(f'(!) Failed to remove stale save remnant from {remnant_time}: {format_exc()}')

                    # log our changes or lack thereof
                    log_on_statusbar(f'{log_noun or "Changes"} saved to {true_dest} after {self.util.get_verbose_timestamp(get_time() - start_time)}.')
                elif successful:                        # log our lack of changes
                    return log_on_statusbar('No changes have been made.')

            except:
                log_on_statusbar(f'(!) Post-{log_noun.lower() or "save"} cleanup failed: {format_exc()}')
            finally:
                self.locked_files.discard(dest)         # unlock temp destination
                self.locked_files.discard(final_dest)   # unlock final destination
                self.setFocus(True)                     # restore keyboard focus so we can use hotkeys again
                self.remove_edit(edit)                  # remove `Edit` object and update priority
                if start_time in self.save_remnants:    # mark save remnant as safe to remove, if still present
                    try: self.save_remnants[start_time]['_in_progress'] = False
                    except: logging.warning('(!) Failed to mark save remnant as safe to remove: ' + format_exc())
                logging.info(f'Remaining locked files after {log_noun.lower() or "edit"}: {self.locked_files}')

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
        # See main.pyw for full implementation (lines 1965-2337)
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
