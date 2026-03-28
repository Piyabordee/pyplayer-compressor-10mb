"""Video player backends — VLC and Qt multimedia implementations."""
from __future__ import annotations

import time
import logging
from traceback import format_exc
from threading import Thread

from PyQt5 import QtGui, QtCore, QtMultimedia, QtMultimediaWidgets
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets as QtW

import vlc
from vlc import State

import qtstart

from pyplayer import constants
from pyplayer.constants import SetProgressContext
from pyplayer.core.ffmpeg import ffmpeg
from pyplayer.widgets.helpers import gui, app, cfg, settings


logger = logging.getLogger('widgets.py')


class PyPlayerBackend:

    __name__ = 'Undefined'
    SUPPORTS_PARSING = False                                # Can this player parse and return critical media info (fps, duration, etc.)?
    SUPPORTS_VIDEO_TRACK_MANIPULATION = False               # Can this player return video track info AND set video tracks?
    SUPPORTS_AUDIO_TRACK_MANIPULATION = False               # Can this player return audio track info AND set audio tracks?
    SUPPORTS_SUBTITLE_TRACK_MANIPULATION = False            # Can this player return subtitle track info AND set subtitle tracks?
    SUPPORTS_AUTOMATIC_SUBTITLE_ENABLING = False            # Does this player auto-enable subtitle tracks when present?
    ENABLE_AUTOMATIC_TRACK_RESTORATION = True               # Should PyPlayer restore its saved tracks/delays when opening/restoring? NOTE: Avoid this if possible!!
    ENABLE_AUTOMATIC_TRACK_RESET = True                     # Should PyPlayer reset its saved tracks/delays to None when opening new files?

    def __init__(self, parent, *args, **kwargs):
        self.parent = parent
        self.enabled = False
        self.menu: QtW.QMenu = None

        self.last_file = ''
        self.file_being_opened = ''
        self.open_cleanup_queued = False
        self.last_text_settings: tuple[str, int, int] = None

    # ---

    def __getattr__(self, name: str):
        ''' Allows access to undefined player-specific properties.
            This is mainly intended for testing purposes. '''
        logger.info(f'Attempting to access undefined player-specific property `player.{name}`')
        return getattr(self._player, name)

    # ---

    def enable(self) -> bool:
        ''' Called upon enabling the backend. When starting PyPlayer, this is
            called immediately after `gui.setup()` and loading the config, but
            before showing the window. '''
        self.enabled = True
        self.open_cleanup_queued = False
        return True

    def disable(self, wait: bool = True):
        ''' Called upon disabling the backend. Stop playing, set `self.enabled`
            to False, perform cleanup, disconnect signals, and end all threads.
            NOTE: If `wait` is False, do not wait for cleanup unless absolutely
            necessary. Instead, have `self.enable()` wait for unfinished cleanup
            before re-enabling. '''
        self.enabled = False
        self.open_cleanup_queued = False
        self.stop()

    def show(self):
        pass

    # ---

    def on_show(self, event: QtGui.QShowEvent):
        ''' Called in `gui.showEvent()`, before the window's
            state has been fully restored/validated. '''
        self.show()

    def on_resize(self, event: QtGui.QResizeEvent):
        ''' Called at the end of `QVideoPlayer.resizeEvent()`. '''
        pass

    def on_fullscreen(self, fullscreen: bool):
        ''' Called at the end of `gui.set_fullscreen()`, just before calling
            `gui.showFullScreen()`/`gui.showMaximized()`/`gui.showNormal()`. '''
        pass

    def on_parse(self, file: str, base_mime: str, mime: str, extension: str):
        ''' Called at the end of `gui.parse_media_file()`. All probe-related
            properties will be up-to-date when this event fires. Rarely, `mime`
            may mutate - `base_mime` is what `file` was initially parsed as.
            NOTE: This event MUST emit `gui._open_cleanup_signal` in some way.
            If you do not emit it directly, set `self.open_cleanup_queued` to
            True until the cleanup signal is emitted so PyPlayer understands
            that it's waiting for cleanup.
            NOTE: This event fires even if FFprobe finishes first, and the UI
            will begin updating immediately afterwards. If you wish to override
            probe properties, you must decide between waiting for the player
            to finish parsing or using `self.on_open_cleanup()` instead. '''
        gui._open_cleanup_signal.emit()

    def on_open_cleanup(self):
        ''' Called at the end of `gui._open_cleanup_slot()`. All opening-related
            properties (aside from `gui.open_in_progress`) will be up-to-date
            when this even fires. '''
        pass

    def on_restart(self):
        ''' Called in `gui.restart()`, immediately after confirming the restart
            is valid. `gui.restarted` will be False. After this event, the UI
            be updated and the player will be force-paused. This event should
            do any extraneous cleanup that must be urgently completed to ensure
            finished media is immediately/seamlessly ready to play again. '''
        gui.update_progress_signal.emit(gui.frame_count)    # ensure UI snaps to final frame

    # ---

    def play(self, file: str, will_restore: bool = False) -> bool:
        ''' Opens the provided `file`, and begins *asynchronously* parsing
            the media if supported by the player. `will_restore` will be
            True if we're intending to set the progress to an arbitrary value
            immediately afterwards (e.g. after a renaming or restart). '''
        raise NotImplementedError()

    def pause(self):
        ''' Toggles the pause state. '''
        raise NotImplementedError()

    def stop(self):
        ''' Stops the player, releasing any locks. '''
        raise NotImplementedError()

    def loop(self):
        ''' Loops the player back to `gui.minimum` after the media *completes*.
            This is not called when there is an ending marker. '''
        self.set_and_update_progress(gui.minimum, SetProgressContext.RESET_TO_MIN)
        return gui.force_pause(False)

    def snapshot(self, path: str, frame: int, width: int, height: int):
        ''' Saves the desired `frame` to `path`, resized to `width`x`height`.
            NOTE: Do not return until the snapshot is complete and saved.
            NOTE: You should probably override this. FFmpeg sucks. '''
        w = width or -1                                     # -1 uses aspect ratio in ffmpeg
        h = height or -1                                    # using `-ss` is faster but even less accurate
        ffmpeg(f'-i "{gui.video}" -frames:v 1 -vf "select=\'eq(n\\,{frame})\', scale={w}:{h}" "{path}"')

    # ---

    def set_pause(self, paused: bool):
        ''' Sets the pause state to `paused`. '''
        raise NotImplementedError()

    def get_mute(self) -> bool:
        ''' Returns the mute state. '''
        raise NotImplementedError()

    def set_mute(self, muted: bool):
        ''' Sets the mute state to `muted`. '''
        raise NotImplementedError()

    def get_volume(self) -> int:
        ''' Returns the volume between 0-100. '''
        raise NotImplementedError()

    def set_volume(self, volume: int):
        ''' Sets the `volume` between 0-100 (or above). '''
        raise NotImplementedError()

    def get_playback_rate(self) -> float:
        ''' Returns the playback rate relative to 1.0. '''
        return 1.0

    def set_playback_rate(self, rate: float):
        ''' Sets the playback `rate` relative to 1.0. '''
        self.show_text('Playback speed is not supported by the selected player.')

    def get_position(self) -> float:
        ''' Returns the media's progress as a value between 0.0-1.0. '''
        raise NotImplementedError()

    def set_position(self, percent: float):
        ''' Sets media progress to a `percent` between 0.0-1.0. '''
        raise NotImplementedError()

    def set_frame(self, frame: int):
        ''' Called while frame-seeking (or entering an exact frame).
            Use this if you have anything special you'd like to do
            (e.g. libVLC's `next_frame()`). '''
        self.set_and_update_progress(frame)

    def set_and_update_progress(self, frame: int = 0, context: int = SetProgressContext.NONE):
        ''' Sets player position to `frame` and updates the UI accordingly.
            `context` is useful if you need to do additional work depending
            on the specific reason we're manually setting the position.
            NOTE: Don't forget to update GIF progress.
            NOTE: This method should update the player's non-GIF progress
            ASAP, so the player feels "snappier" on the user's end. '''
        self.set_position(frame / gui.frame_count)
        gui.update_progress(frame)
        gui.gifPlayer.gif.jumpToFrame(frame)

    # ---

    def get_state(self) -> int:                             # TODO
        return State.NothingSpecial

    def can_restart(self) -> bool:
        ''' Called at the start of `gui.restart()`.
            Returns False if a restart should be skipped. '''
        return True

    def is_parsed(self) -> bool:
        ''' Returns True if the player has finished its own
            parsing of the current media, independent of FFprobe. '''
        return False

    def is_playing(self) -> bool:
        ''' Semi-convenience method. Returns True if
            we are actively playing unpaused media. '''
        raise NotImplementedError()

    def get_fps(self) -> float:
        ''' Returns the frame rate of the current
            media if possible, otherwise 0.0. '''
        return 0.0

    def get_duration(self) -> float:
        ''' Returns the duration (in seconds) of the
            current media if possible, otherwise 0.0. '''
        return 0.0

    def get_dimensions(self) -> tuple[int, int]:
        ''' Returns the dimensions of the current media as a tuple if possible,
            otherwise `(0, 0)`. This method may raise an exception. '''
        return 0, 0

    # ---

    def get_audio_delay(self) -> int:
        return 0

    def set_audio_delay(self, msec: int):
        self.show_text('Audio delays are not supported by the selected player.')

    def get_subtitle_delay(self) -> int:
        return 0

    def set_subtitle_delay(self, msec: int):
        self.show_text('Subtitle delays are not supported by the selected player.')

    def get_video_track(self) -> int:
        return -1

    def get_audio_track(self) -> int:
        return -1

    def get_subtitle_track(self) -> int:
        return -1

    def get_video_tracks(self, raw: bool = False) -> tuple[int, str]:
        ''' Generator that yields each video track's ID and title as a
            tuple. If `raw` is True, the title should be yielded as-is. '''
        yield -1, 'The selected player does not support tracks'

    def get_audio_tracks(self, raw: bool = False) -> tuple[int, str]:
        ''' Generator that yields each audio track's ID and title as a
            tuple. If `raw` is True, the title should be yielded as-is. '''
        yield -1, 'The selected player does not support tracks'

    def get_subtitle_tracks(self, raw: bool = False) -> tuple[int, str]:
        ''' Generator that yields each subtitle track's ID and title as a
            tuple. If `raw` is True, the title should be yielded as-is. '''
        yield -1, 'The selected player does not support tracks'

    def get_video_track_count(self) -> int:
        return 1

    def get_audio_track_count(self) -> int:
        return 1

    def get_subtitle_track_count(self) -> int:
        return 1

    def set_video_track(self, index: int):
        self.show_text('Track manipulation is not supported by the selected player.')

    def set_audio_track(self, index: int):
        self.show_text('Track manipulation is not supported by the selected player.')

    def set_subtitle_track(self, index: int):
        self.show_text('Track manipulation is not supported by the selected player.')

    def add_audio_track(self, url: str, enable: bool = False) -> bool:
        self.show_text('Dynamically adding audio tracks is not supported by the selected player.')

    def add_subtitle_track(self, url: str, enable: bool = False) -> bool:
        self.show_text('Dynamically adding subtitle tracks is not supported by the selected player.')

    # ---

    def show_text(self, text: str, timeout: int = 350, position: int = None):
        ''' Displays marquee `text` (overlaying the player),
            overriding the default `position` if desired. '''
        if not settings.groupText.isChecked(): return       # marquees are completely disabled -> return
        gui.statusbar.showMessage(text.replace('%%', '%'), max(timeout, 1000))

    def set_text_position(self, button: QtW.QRadioButton):
        ''' Sets marquee text's position to one of 9 pre-defined values
            represented by a `button` on the settings dialog. Use
            `int(button.objectName()[17:])` to get a number between
            1-9 representing top-left to bottom-right. '''
        self.parent._text_position = int(button.objectName()[17:])

    def set_text_height(self, percent: int):
        ''' Sets marquee text's size (specifically its height) to a `percent`
            between 0-100 that is relative to the current media. '''
        self.parent._text_height_percent = percent / 100

    def set_text_x(self, percent: float):
        ''' Sets marquee text's x-offset from the nearest edge to a `percent`
            between 0-100 that is relative to the current media. '''
        self.parent._text_x_percent = percent / 100

    def set_text_y(self, percent: float):
        ''' Sets marquee text's y-offset to a `percent` between
            0-100 that is relative to the current media. '''
        self.parent._text_y_percent = percent / 100

    def set_text_max_opacity(self, percent: int):
        ''' Sets and scales marquee text's max opacity as a
            `percent` between 0-100 to a value between 0-255. '''
        self.parent._text_max_opacity = round(255 * (percent / 100))

    # ---

    def __repr__(self) -> str:
        return self.__name__




class PlayerVLC(PyPlayerBackend):
    ''' TODO: vlc.Instance() arguments to check out:
        --align={0 (Center), 1 (Left), 2 (Right), 4 (Top), 8 (Bottom), 5 (Top-Left), 6 (Top-Right), 9 (Bottom-Left), 10 (Bottom-Right)}
        --audio-time-stretch, --no-audio-time-stretch   Enable time stretching audio (default enabled) <- disabled = pitch changes with playback speed
        --gain=<float [0.000000 .. 8.000000]>           Audio gain
        --volume-step=<float [1.000000 .. 256.000000]>  Audio output volume step
        --marq-marquee, --sub-source=marq '''

    __name__ = 'VLC'
    SUPPORTS_PARSING = True
    SUPPORTS_VIDEO_TRACK_MANIPULATION = True
    SUPPORTS_AUDIO_TRACK_MANIPULATION = True
    SUPPORTS_SUBTITLE_TRACK_MANIPULATION = True
    SUPPORTS_AUTOMATIC_SUBTITLE_ENABLING = True
    ENABLE_AUTOMATIC_TRACK_RESTORATION = False
    ENABLE_AUTOMATIC_TRACK_RESET = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._media: vlc.Media = None
        self._instance: vlc.Instance = None
        self._player: vlc.MediaPlayer = None
        self._event_manager = None

        self.opening = False
        self.ui_delay = 0.0
        self.is_pitch_sensitive_audio = False
        self.is_bad_with_vlc = False
        self.add_to_progress_offset = 0.0
        self.reset_progress_offset = False
        self.swap_slider_styles_queued = False

        self.text_fade_start_time = 0.0
        self.text_fade_end_time = 0.0
        self.text_fade_thread_open = False
        self.metronome_thread_open = False
        self.slider_thread_open = False

        self.context_offsets = {
            SetProgressContext.RESTORE:             None,
            SetProgressContext.RESTART:             0.0,
            SetProgressContext.RESET_TO_MIN:        None,   # `QVideoSlider.mouseReleaseEvent()` had this as 0.01
            SetProgressContext.RESET_TO_MAX:        None,   # `QVideoSlider.mouseReleaseEvent()` had this as 0.01
            SetProgressContext.NAVIGATION_RELATIVE: 0.1,
            SetProgressContext.NAVIGATION_EXACT:    0.075,  # `manually_update_current_time()` had this as 0.01
            SetProgressContext.SCRUB:               None
        }


    def enable(self) -> bool:
        while self.metronome_thread_open or self.slider_thread_open or self.text_fade_thread_open:
            time.sleep(0.02)
        super().enable()

        # setup VLC instance
        logger.debug(f'VLC arguments: {qtstart.args.vlc}')
        self._instance = vlc.Instance(qtstart.args.vlc)     # VLC arguments can be passed through the --vlc argument
        player = self._player = self._instance.media_player_new()
        event_manager = self._event_manager = player.event_manager()

        # NOTE: cannot use .emit as a callback
        event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, lambda event: gui.restart_signal.emit())
        event_manager.event_attach(vlc.EventType.MediaPlayerOpening, lambda event: setattr(self, 'opening', True))
        event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_play)

        self.get_playback_rate = player.get_rate
        self.set_playback_rate = player.set_rate
        self.get_position = player.get_position
        self.set_position = player.set_position
        self.get_volume = player.audio_get_volume
        self.set_volume = player.audio_set_volume
        self.get_mute = player.audio_get_mute
        self.set_mute = player.audio_set_mute
        self.pause = player.pause
        self.set_pause = player.set_pause
        self.stop = player.stop
        self.snapshot = lambda path, frame, w, h: player.video_take_snapshot(0, psz_filepath=path, i_width=w, i_height=h)
        self.get_state = player.get_state
        self.is_playing = player.is_playing
        self.get_fps = player.get_fps                       # TODO: self.vlc.media.get_tracks() might be more accurate, but I can't get it to work
        self.get_duration = lambda: player.get_length() / 1000
        self.get_dimensions = player.video_get_size         # ↓ VLC uses microseconds for delays for some reason
        self.get_audio_delay = lambda: player.audio_get_delay() / 1000
        self.set_audio_delay = lambda msec: player.audio_set_delay(msec * 1000)
        self.get_subtitle_delay = lambda: player.video_get_spu_delay() / 1000
        self.set_subtitle_delay = lambda msec: player.video_set_spu_delay(msec * 1000)
        self.get_audio_track = player.audio_get_track
        self.get_video_track = player.video_get_track
        self.get_subtitle_track = player.video_get_spu
        self.get_audio_tracks = lambda raw = False: self._get_tracks(player.audio_get_track_description, raw)
        self.get_video_tracks = lambda raw = False: self._get_tracks(player.video_get_track_description, raw)
        self.get_subtitle_tracks = lambda raw = False: self._get_tracks(player.video_get_spu_description, raw)
        self.get_audio_track_count = lambda: player.audio_get_track_count() - 1
        self.get_video_track_count = lambda: player.video_get_track_count() - 1
        self.get_subtitle_track_count = lambda: player.video_get_spu_count() - 1
        self.set_audio_track = player.audio_set_track
        self.set_video_track = player.video_set_track
        self.set_subtitle_track = player.video_set_spu

        player.stop()                                       # stopping the player at any point fixes the audio-cutoff bug
        player.video_set_key_input(False)                   # pass VLC key events to widget
        player.video_set_mouse_input(False)                 # pass VLC mouse events to widget
        player.video_set_marquee_int(vlc.VideoMarqueeOption.Enable, 1)

        # manually refresh text-related settings
        self.set_text_height(settings.spinTextHeight.value())
        self.set_text_x(settings.spinTextX.value())
        self.set_text_y(settings.spinTextY.value())

        # start slider-related threads (these are safe to do before showing window)
        self.swap_slider_styles_queued = False
        self.metronome_thread_open = False
        self.slider_thread_open = False
        Thread(target=self.update_slider_thread, daemon=True).start()
        Thread(target=self.high_precision_slider_accuracy_thread, daemon=True).start()
        return True


    def disable(self, wait: bool = True):                   # TODO do we need `gui.frame_override` in here for smooth transitions?
        super().disable()
        self.text_fade_thread_open = False
        self.open_cleanup_queued = False
        if wait:
            while self.metronome_thread_open or self.slider_thread_open:
                time.sleep(0.02)
            self._media = None
            self._instance = None
            self._player = None
            self._event_manager = None


    def show(self):
        if constants.IS_WINDOWS: self._player.set_hwnd(self.parent.winId())
        elif constants.IS_MAC:   self._player.set_nsobject(int(self.parent.winId()))
        else:                    self._player.set_xwindow(self.parent.winId())


    def _on_play(self, event: vlc.Event):
        ''' VLC event. '''
        if self.opening:
            self.opening = False

            # HACK: for some files, VLC will always default to the wrong audio track (NO idea...
            # ...why, nothing unusal in any media-parsing tool i've used and no other player...
            # ...does it) -> when opening a new file, immediately set all tracks to track 1
            if self.last_file != self.file_being_opened:
                self.last_file = self.file_being_opened
                gui.last_video_track = 1
                gui.last_audio_track = 1
                gui.last_subtitle_track = 1 if settings.checkAutoEnableSubtitles.isChecked() else -1
                gui.last_audio_delay = 0
                gui.last_subtitle_delay = 0
            gui.tracks_were_changed = True                  # we can ignore this since the tracks are always set
            gui.restore_tracks()


    def on_parse(self, file: str, base_mime: str, mime: str, extension: str):
        if base_mime == 'image':
            gui._open_cleanup_signal.emit()                 # manually emit _open_cleanup_signal for images/gifs (slider thread will be idle)
            self.is_pitch_sensitive_audio = False
            self.is_bad_with_vlc = False
        else:
            self.open_cleanup_queued = True                 # `open_cleanup_queued` + `open_in_progress` and `frame_override` work...
            gui.frame_override = 0                          # ...together to halt `update_slider_thread()` and trigger cleanup safely

            # TODO: we should really be tracking the codec instead of the container here
            # TODO: can this be fixed with a different demuxer or something? (what we COULD have done to fix pitch-shifting)
            if extension == 'ogg':                          # TODO: flesh out a list of unresponsive media types
                self.is_bad_with_vlc = True
                self.is_pitch_sensitive_audio = False
            else:
                self.is_bad_with_vlc = False
                self.is_pitch_sensitive_audio = mime == 'audio'

            # update marquee size and offset relative to video's dimensions
            if mime == 'video':
                height = gui.vheight
                parent = self.parent
                set_marquee_int = self._player.video_set_marquee_int
                set_marquee_int(vlc.VideoMarqueeOption.Size, int(height * parent._text_height_percent))
                set_marquee_int(vlc.VideoMarqueeOption.X,    int(height * parent._text_x_percent))
                set_marquee_int(vlc.VideoMarqueeOption.Y,    int(height * parent._text_y_percent))


    def on_open_cleanup(self):
        # warn users that the current media will not scrub/navigate very well
        # TODO: what else needs to be here (and set as not `self.is_pitch_sensitive_audio`)?
        if self.is_bad_with_vlc:
            gui.statusbar.showMessage(f'Note: Files of this mime type/encoding ({gui.mime_type}/{gui.extension}) may be laggy or unresponsive while scrubbing/navigating on some systems (libVLC issue).')


    def on_restart(self):
        self.play(gui.video)
        frame = gui.frame_count
        self.set_position((frame - 2) / frame)              # reset position (-2 frames to ensure visual update for VLC)
        gui.update_progress_signal.emit(frame)              # ensure UI snaps to final frame
        while self.get_state() == State.Ended:              # wait for VLC to update the player's state
            time.sleep(0.005)


    def play(self, file: str, will_restore: bool = False, _error: bool = False) -> bool:
        ''' Open, parse, and play a `file` in libVLC, returning True if
            successful. If `file` cannot be played, the currently opened file
            is reopened if possible. NOTE: Parsing is started asynchronously.
            This function returns immediately upon playing the file. '''
        try:
            self._media = self._instance.media_new(file)    # combines media_new_path (local files) and media_new_location (urls)
            self._player.set_media(self._media)             # TODO: this line has a HUGE delay when opening first file after opening extremely large video
            #self._player.set_mrl(self.media.get_mrl())     # not needed? https://www.olivieraubert.net/vlc/python-ctypes/doc/vlc.MediaPlayer-class.html#set_mrl
            self._player.play()

            # NOTE: parsing normally is still relatively fast, but libVLC is not as effective/compatible as FFprobe
            #       additionally, reading an already-created probe file is MUCH faster (relatively) than parsing with libVLC
            self._media.parse_with_options(0x0, 0)          # https://www.olivieraubert.net/vlc/python-ctypes/doc/vlc.Media-class.html#parse_with_options
            self.file_being_opened = file
            return True
        except:
            logger.warning(f'VLC failed to play file {file}: {format_exc()}')
            if not _error and file != gui.video:            # `_error` ensures we only attempt to play previous video once
                if not gui.video: self._player.stop()       # no previous video to play, so just stop playing
                else: self.play(gui.video, _error=True)     # attempt to play previous working video
            return False


    def loop(self):
        self.play(gui.video)
        # TODO just in case doing `set_and_update_progress` causes hitches or delays, we're...
        # ...doing an if-statement instead to ensure normal loops are slightly more seamless
        #set_and_update_progress(self.minimum)              # <- DOES this cause hitches?
        if gui.buttonTrimStart.isChecked():
            return gui.update_progress(0)
        return self.set_and_update_progress(gui.minimum, SetProgressContext.RESET_TO_MIN)


    def can_restart(self) -> bool:
        # HACK: sometimes VLC will double-restart -> replay/restore position ASAP
        if gui.restarted:
            logging.info('Double-restart detected. Ignoring...')
            gui.restarted = False                           # set this so we don't get trapped in an infinite restart-loop
            return gui.restore(gui.sliderProgress.value())

        # reset frame_override in case it's set
        gui.frame_override = -1

        # HACK: skip this restart if needed and restore actual progress
        if gui.ignore_imminent_restart:
            gui.ignore_imminent_restart = False
            gui.restarted = True
            return gui.restore(gui.sliderProgress.value())

        # we're good to go. continue with restart
        return True


    def is_parsed(self) -> bool:
        _player = self._player
        return (
            self._media.get_parsed_status() == 4
            and _player.get_fps() != 0
            and _player.get_length() != 0
            and _player.video_get_size() != (0, 0)
        )


    def set_playback_rate(self, rate: float):
        self._player.set_playback_rate(rate)
        if rate == 1.0 or gui.playback_rate == 1.0:         # TODO: for now, lets just force the VLC-progress for non-standard speeds
            self.reset_progress_offset = True
            self.swap_slider_styles_queued = True


    def set_and_update_progress(self, frame: int = 0, context: int = SetProgressContext.NONE):
        ''' Simultaneously sets VLC/gif player position to `frame`, avoids the
            pitch-shift-bug for unpaused audio, and adjusts the high-precision
            progress offset by `offset` seconds (if provided) to account for
            VLC buffering. `offset` is ignored if `self.is_paused` is True. '''

        # don't touch progress if we're currently opening a file
        if gui.open_in_progress:
            return

        offset = self.context_offsets.get(context, None)
        if offset is None:
            return super().set_and_update_progress(frame, context)

        is_paused = gui.is_paused
        is_pitch_sensitive_audio = self.is_pitch_sensitive_audio

        # HACK: "replay" audio file to correct VLC's pitch-shifting bug
        # https://reddit.com/r/VLC/comments/i4m0by/pitch_changing_on_seek_only_some_audio_file_types/
        # https://reddit.com/r/VLC/comments/b0i9ff/music_seems_to_pitch_shift_all_over_the_place/
        if is_pitch_sensitive_audio and not is_paused:
            self._player.set_media(self._media)
            self._player.play()

        #self.set_player_time(round(frame * (1000 / gui.frame_rate)))
        self.set_position(frame / gui.frame_count)
        gui.update_progress(frame)                          # necessary while paused and for a snappier visual update
        gui.gifPlayer.gif.jumpToFrame(frame)

        # NOTE: setting `frame_override` here on videos can cause high-precision progress...
        # ...to desync by a few frames, but prevents extremely rare timing issues that...
        # ...stop the slider from updating to its new position. is this trade-off worth it?
        # NOTE: `frame_override` sets `add_to_progress_offset` to 0.1 if it's 0
        #       -> add 0.001 to `offset` to ensure it doesn't get ignored
        if settings.checkHighPrecisionProgress.isChecked() and not is_pitch_sensitive_audio:
            self.add_to_progress_offset = -0.075 if is_paused else offset + 0.001
        gui.frame_override = frame                          # ^ set offset BEHIND current time while paused. i don't understand why, but it helps


    def _get_tracks(self, get_description, raw: bool = False) -> tuple[int, str]:
        if raw:
            for id, title in get_description():
                yield id, title.decode()

        # VLC may add tags to track titles, like "Track 1 - [English]" -> try to detect and remove these
        else:
            for id, title in get_description():
                fake_tags = []
                parts = title.decode().split(' - ')
                title = parts[0]
                for tag in reversed(parts[1:]):
                    if fake_tags:                           # if we found a non-tag, don't look for tags before it in...
                        fake_tags.append(tag)               # ...the title, e.g. "Track 1 - [Don't Detect Me] - Yippee"
                        continue
                    tag = tag.strip()
                    if tag[0] != '[' or tag[-1] != ']':
                        fake_tags.append(tag)
                if fake_tags:                               # reapply all valid nontags
                    title = f'{title} - {" - ".join(reversed(fake_tags))}'
                yield id, title


    def add_audio_track(self, url: str, enable: bool = False) -> bool:
        if self._player.add_slave(1, url, enable) == 0:     # slaves can be subtitles (0) or audio (1)
            gui.log_on_statusbar_signal.emit(f'Audio file {url} added and enabled.')
            if settings.checkTextOnSubtitleAdded.isChecked():
                self.show_text('Audio file added and enabled')
            return True
        else:                                               # returns 0 on success
            gui.log_on_statusbar_signal.emit(f'Failed to add audio file {url} (VLC does not report specific errors for this).')
            if settings.checkTextOnSubtitleAdded.isChecked():
                self.show_text('Failed to add audio file')


    def add_subtitle_track(self, url: str, enable: bool = False) -> bool:
        if self._player.add_slave(0, url, enable) == 0:     # slaves can be subtitles (0) or audio (1)
            gui.log_on_statusbar_signal.emit(f'Subtitle file {url} added and enabled.')
            if settings.checkTextOnSubtitleAdded.isChecked():
                self.show_text('Subtitle file added and enabled')
            return True
        else:                                               # returns 0 on success
            gui.log_on_statusbar_signal.emit(f'Failed to add subtitle file {url} (VLC does not report specific errors for this).')
            if settings.checkTextOnSubtitleAdded.isChecked():
                self.show_text('Failed to add subtitle file')


    def set_text_position(self, button: QtW.QRadioButton):
        self.parent._text_position = (                      # libVLC uses wacky position values, so map them accordingly
            5, 4, 6,
            1, 0, 2,
            9, 8, 10
        )[int(button.objectName()[17:]) - 1]
        self._player.video_set_marquee_int(vlc.VideoMarqueeOption.Position, self.parent._text_position)


    def set_text_height(self, percent: int):
        self.parent._text_height_percent = percent / 100
        new_size = int(gui.vheight * self.parent._text_height_percent)
        self._player.video_set_marquee_int(vlc.VideoMarqueeOption.Size, new_size)


    def set_text_x(self, percent: float):
        self.parent._text_x_percent = percent / 100         # ↓ offset is relative to media's height for both X and Y
        new_x = int(gui.vheight * self.parent._text_x_percent)
        self._player.video_set_marquee_int(vlc.VideoMarqueeOption.X, new_x)


    def set_text_y(self, percent: float):
        self.parent._text_y_percent = percent / 100         # ↓ offset is relative to media's height for both X and Y
        new_y = int(gui.vheight * self.parent._text_y_percent)
        self._player.video_set_marquee_int(vlc.VideoMarqueeOption.Y, new_y)


    def show_text(self, text: str, timeout: int = 350, position: int = None):
        ''' Displays marquee `text` on the player, for at least `timeout` ms at
            `position`: 0 (Center), 1 (Left), 2 (Right), 4 (Top), 5 (Top-Left),
            6 (Top-Right), 8 (Bottom), 9 (Bottom-Left), 10 (Bottom-Right).

            NOTE: If `timeout` is 0, `text` will stay visible indefinitely.

            TODO: marquees are supposed to be chainable -> https://wiki.videolan.org/Documentation:Modules/marq/
            NOTE: vlc.py claims "Marquee requires '--sub-source marq' in the Instance() call" <- not true?
            NOTE: VLC supports %-strings: https://wiki.videolan.org/Documentation:Format_String/
                  Escape isolated % characters with %%. Use VideoMarqueeOption.Refresh to auto-update text on
                  an interval. See the bottom of vlc.py for an example implementation of an on-screen clock. '''
        if not settings.groupText.isChecked(): return       # marquees are completely disabled -> return

        try:
            # calculate when the text should start and complete its fading animation
            delay = max(timeout / 1000, settings.spinTextFadeDelay.value())
            self.text_fade_start_time = time.time() + delay
            if timeout == 0:                                # `timeout` of 0 -> leave the text up indefinitely
                self.text_fade_end_time = self.text_fade_start_time
            else:
                fade_duration = settings.spinTextFadeDuration.value()
                if fade_duration < 0.1:                     # any lower than 0.1 seconds -> disappear instantly
                    fade_duration = -0.1
                self.text_fade_end_time = self.text_fade_start_time + fade_duration

            # reset opacity to default (repetitive but sometimes necessary)
            self._player.video_set_marquee_int(vlc.VideoMarqueeOption.Opacity, self.parent._text_max_opacity)

            # see if we actually need to update the text/position
            if position is None:                            # reuse last position if needed
                position = self.parent._text_position
            new_settings = (text, timeout, position)
            unique_settings = new_settings != self.last_text_settings

            # actually set text and position if they're unique
            if (timeout == 0 and not unique_settings) or not gui.video:
                return                                      # avoid repetitive + pointless calls
            if unique_settings:
                self._player.video_set_marquee_int(vlc.VideoMarqueeOption.Position, position)
                self._player.video_set_marquee_string(vlc.VideoMarqueeOption.Text, text)
                self.last_text_settings = new_settings

            # start fading thread if it hasn't been started already
            if not self.text_fade_thread_open:
                Thread(target=self.text_fade_thread, daemon=True).start()
                self.text_fade_thread_open = True
        except:
            logger.warning(f'(!) Unexpected error while showing text overlay: {format_exc()}')


    def text_fade_thread(self):
        ''' A thread for animating libVLC's `VideoMarqueeOption.Opacity`
            property. TODO: Should this be a `QTimer` instead? '''
        _player = self._player
        while self.enabled:
            now = time.time()
            if now >= self.text_fade_start_time:
                end = self.text_fade_end_time
                fade_duration = end - self.text_fade_start_time
                if fade_duration == 0:                      # don't fade at all, leave text up until told otherwise
                    time.sleep(0.1)
                elif now <= end:
                    alpha = ((end - now) / fade_duration) * self.parent._text_max_opacity
                    _player.video_set_marquee_int(vlc.VideoMarqueeOption.Opacity, round(alpha))
                    time.sleep(0.025)                       # fade out at 40fps
                else:                                       # if we just finished fading, make sure no text is visible
                    #_player.video_set_marquee_string(vlc.VideoMarqueeOption.Text, '')
                    _player.video_set_marquee_int(vlc.VideoMarqueeOption.Opacity, 0)
                    self.text_fade_start_time = 9999999999  # set start_time to extreme number to stop the loop
            else:                                           # sleep as long as possible (but < the shortest possible delay)
                time.sleep(0.25 if self.text_fade_start_time - now > 0.5 else 0.01)

        self.text_fade_thread_open = False
        return logging.info('VLC player disabled. Ending text_fade thread.')


    def high_precision_slider_accuracy_thread(self):
        ''' A thread for monitoring the accuracy of `self.update_slider_thread`
            compared to the real-world time it's been active. Once per second,
            the current UI frame is compared to how many actual seconds it's
            been since play was last started/resumed as well as the frame it
            started from to see how far we've deviated from reality. The inter-
            frame delay (`self.delay`) is then adjusted using `self.ui_delay`
            speed up or slow down the UI so that it lines up exactly right, one
            second from now.

            If the UI desyncs by more than one second from actual time or more
            than two seconds from libVLC's native progress, the UI is reset.

            Accuracy loop loops indefinitely until `self.reset_progress_offset`
            is set to True, then it breaks from the loop and resets its values.

            HACK: `self.add_to_progress_offset` is a float added to the initial
            starting time in order to account for microbuffering within libVLC
            (which is NOT reported or detectable anywhere, seemingly). A better
            solution is needed, but I'm not sure one exists. Even libVLC's media
            stats (read_bytes, displayed_pictures, etc.) are updated at the same
            awful, inconsistent rate that its native progress is updated, making
            them essentially useless. At the very least, most mid-high range
            systems "buffer" at the same speed (~0.05-0.1 seconds, is that also
            partially tied to libVLC's update system?). Only low-end systems
            will fall slightly behind (but (probably) never desync). '''

        play_started = 0.0
        frame_started = 0
        current_frame = 0
        vlc_frame = 0.0
        seconds_elapsed = 0.0
        frames_elapsed = 0.0
        frame_desync = 0.0
        time_desync = 0.0
        vlc_desync = 0.0

        # re-define global aliases -> having them as locals is even faster
        _gui = gui
        get_ui_frame = _gui.sliderProgress.value
        is_playing = self.is_playing
        _sleep = time.sleep
        _get_time = time.time

        check_interval = 1
        intercheck_count = 20
        delay_per_intercheck = check_interval / intercheck_count
        vlc_desync_counter_limit = 2                    # how many times in a row VLC must be desynced before we care

        while self.enabled:
            # stay relatively idle while minimized, nothing is active, or we're waiting for something
            while not _gui.isVisible() and self.enabled:                  _sleep(0.25)
            while _gui.isVisible() and not is_playing() and self.enabled: _sleep(0.02)
            while _gui.open_in_progress or _gui.frame_override != -1:     _sleep(0.01)

            start = _get_time()
            play_started = start + self.add_to_progress_offset
            frame_started = get_ui_frame()
            self.reset_progress_offset = False
            self.add_to_progress_offset = 0.0
            vlc_desync_limit = _gui.frame_rate * 2
            vlc_desync_counter = 0

            while is_playing() and not self.reset_progress_offset and not _gui.open_in_progress:
                seconds_elapsed = (_get_time() - play_started) * _gui.playback_rate
                frames_elapsed = seconds_elapsed * _gui.frame_rate
                current_frame = get_ui_frame()
                vlc_frame = self.get_position() * _gui.frame_count
                frame_desync = current_frame - frames_elapsed - frame_started
                time_desync = frame_desync / _gui.frame_rate
                absolute_time_desync = abs(time_desync)
                vlc_desync = current_frame - vlc_frame

                # if we're greater than 1 second off our expected time or 2 seconds off VLC's time...
                # ...something is wrong -> reset to just past VLC's frame (VLC is usually a bit behind)
                # NOTE: VLC can be deceptive - only listen to VLC if it's been desynced for a while
                vlc_is_desynced = vlc_frame > 0 and abs(vlc_desync) > vlc_desync_limit
                if vlc_is_desynced: vlc_desync_counter += 1
                else:               vlc_desync_counter = 0
                if absolute_time_desync >= 1 or vlc_desync_counter >= vlc_desync_counter_limit:
                    self.ui_delay = _gui.delay
                    true_frame = (self.get_position() * _gui.frame_count) + (_gui.frame_rate * 0.2)
                    logging.info(f'(?) High-precision progress desync: {time_desync:.2f} real seconds, {vlc_desync:.2f} VLC frames. Changing frame from {current_frame} to {true_frame}.')

                    # double-check our conditions in case of extremely unlucky timing
                    if not is_playing() or self.reset_progress_offset or _gui.open_in_progress:
                        break

                    # if frame_override is already set, it will be resetting for us anyways
                    # don't break - just let things run their course
                    if _gui.frame_override == -1:
                        _gui.frame_override = int(true_frame)

                # otherwise, adjust delay accordingly to stay on track
                else:
                    if time_desync >= 0: self.ui_delay = _gui.delay * (1 + absolute_time_desync)    # we're ahead (need to slow down)
                    else:                self.ui_delay = _gui.delay / (1 + absolute_time_desync)    # we're behind (need to speed up)

                # TODO: have setting or debug command line argument that actually logs these every second?
                #logging.debug(f'VLC\'s frame: {vlc_frame:.1f}, Our frame: {current_frame} (difference of {vlc_desync:.1f} frames, or {vlc_desync / _gui.frame_rate:.2f} seconds)')
                #logging.debug(f'New delay: {self.ui_delay} (delta_frames={delta_frames:.1f}, delta_seconds={delta_seconds:2f})')

                # wait for next check, but account for the time it took to actually run through the loop
                time_elapsed = 0.0
                while time_elapsed < check_interval:
                    if not is_playing() or self.reset_progress_offset or _gui.open_in_progress:
                        break
                    _sleep(delay_per_intercheck)
                    time_elapsed = _get_time() - start
                start = _get_time()

        # all loops broken, player backend disabled
        self.metronome_thread_open = False
        return logging.info('VLC player disabled. Ending high_precision_slider_accuracy thread.')


    def update_slider_thread(self):
        ''' Handles updating the progress bar. This includes both slider-types
            and swapping between them. Set `_gui.frame_override` to override the
            next pending frame (preventing timing-related bugs). If set while
            `_gui.open_in_progress` is True, this thread halts before signalling
            `_gui._open_cleanup_slot()` once `self.open_cleanup_queued` is True,
            then halts again until the opening process is fully complete. While
            not playing, the slider is manually updated at 20fps to keep
            animations working smoothly without draining resources.
            While minimized, resource-usage is kept to a minimum. '''

        logging.debug('Slider-updating thread started.')

        # re-define global aliases -> having them as locals is even faster
        _gui = gui
        get_ui_frame = _gui.sliderProgress.value
        repaint_slider = _gui.sliderProgress.update
        is_playing = self.is_playing
        is_high_precision = _gui.dialog_settings.checkHighPrecisionProgress.isChecked
        emit_open_cleanup_signal = _gui._open_cleanup_signal.emit
        _emit_update_progress_signal = _gui.update_progress_signal.emit
        _sleep = time.sleep
        _get_time = time.time

        # set the minimum fps the slider MUST update at to ensure...
        # ...animations tied to the slider continue to work (smoothly)
        # NOTE: this number must match the `fps` variable that...
        #       ...appears twice in `QVideoSlider.paintEvent()`
        min_fps = 20                                    # TODO this is applied even for non-fullscreen images
        min_fps_delay = 1 / min_fps

        while self.enabled:
            # window is NOT visible, stay relatively idle and do not update
            while not _gui.isVisible() and self.enabled:
                _sleep(0.25)

            # window is visible, but nothing is actively playing (NOTE: `is_playing()` will be False for images)
            while _gui.isVisible() and not is_playing() and self.enabled:
                repaint_slider()                        # force `QVideoSlider` to keep painting
                _sleep(min_fps_delay)                   # update at `min_fps`

            # reset queued slider-swap (or the slider won't update anymore after a swap)
            self.swap_slider_styles_queued = False

            # high-precision option enabled -> fake a smooth slider based on media's frame rate (simulates what libvlc SHOULD have)
            # TODO: for now, lets just force the VLC-progress for non-standard speeds
            if is_high_precision() and _gui.playback_rate == 1.0:
                start = _get_time()
                now = start
                min_fps_delay_threshold_factor = 2      # if we're too close to `min_fps_delay`, split up sleep this many times
                min_fps_delay_threshold = min_fps_delay * min_fps_delay_threshold_factor

                # playing, not buffering, not locked, and not about to swap styles
                while is_playing() and not _gui.lock_progress_updates and not self.swap_slider_styles_queued:
                    if _gui.frame_override != -1:
                        if _gui.open_in_progress:       # opening -> wait for signal to start cleanup
                            while _gui.open_in_progress and not self.open_cleanup_queued:
                                _sleep(0.01)
                            emit_open_cleanup_signal()  # _open_cleanup_signal uses _gui._open_cleanup_slot()
                            self.open_cleanup_queued = False
                            while _gui.open_in_progress and not self.open_cleanup_queued:
                                _sleep(0.01)            # wait for media opening to finish
                        else:
                            _emit_update_progress_signal(_gui.frame_override)
                        _gui.frame_override = -1        # reset frame_override

                        # force high-precision progress bar to reset its starting offset
                        if not self.add_to_progress_offset:
                            self.add_to_progress_offset = 0.1
                        self.reset_progress_offset = True

                    # (TODO: unfinished) no frame override -> increment `playback_rate` frames forward (i.e. at 1x speed -> 1 frame)
                    #elif (next_frame := get_ui_frame() + _gui.playback_rate) <= _gui.frame_count:   # do NOT update progress if we're at the end
                    elif (next_frame := get_ui_frame() + 1) <= _gui.frame_count:            # do NOT update progress if we're at the end
                        _emit_update_progress_signal(next_frame)                            # update_progress_signal -> _update_progress_slot

                    # low FPS media confuses the accuracy thread when switching media
                    # -> always update/repaint high-precision slider at >= `min_fps`
                    if _gui.frame_rate < min_fps:
                        try:
                            _sleep(0.0001)              # sleep to force-update get_time()
                            now = _get_time()
                            execution_time = now - start
                            time_elapsed = execution_time
                            while time_elapsed < self.ui_delay:
                                to_sleep = self.ui_delay - time_elapsed

                                # if we're too close to `min_delay`, split up sleep calls
                                # otherwise, sleep for whichever delay is smaller
                                if to_sleep > min_fps_delay:
                                    if to_sleep < min_fps_delay_threshold:
                                        _sleep(to_sleep / min_fps_delay_threshold_factor)
                                    else:
                                        _sleep(min_fps_delay)
                                else:
                                    _sleep(to_sleep)

                                # manually repaint slider to keep animations running smoothly
                                repaint_slider()

                                # check our conditions while we're awaiting the next frame
                                if not is_playing() or _gui.lock_progress_updates or self.swap_slider_styles_queued or _gui.frame_override != -1:
                                    break

                                now = _get_time()
                                time_elapsed = now - start
                        except Exception as error:
                            logging.debug(f'update_slider_thread bottleneck - {type(error)}: {error} -> delay={self.ui_delay} execution-time={_get_time() - start}')
                        finally:
                            start = now

                    # for normal FPS media, just sleep normally, accounting for the loop's execution time
                    else:
                        try:
                            _sleep(0.0001)              # sleep to force-update get_time()
                            _sleep(self.ui_delay - (_get_time() - start))
                        except Exception as error:
                            logging.debug(f'update_slider_thread bottleneck - {type(error)}: {error} -> delay={self.ui_delay} execution-time={_get_time() - start}')
                        finally:
                            start = _get_time()

            # high-precision option disabled -> use libvlc's native progress and manually paint QVideoSlider
            else:
                vlc_offset = _gui.frame_rate * 0.15     # VLC's progress is usually a bit behind, so use this to make sure we stay somewhat lined up with reality

                # not playing, not locked, and not about to swap styles
                while is_playing() and not _gui.lock_progress_updates and not self.swap_slider_styles_queued:
                    if _gui.frame_override != -1:
                        if _gui.open_in_progress:       # opening -> wait for signal to start cleanup
                            while _gui.open_in_progress and not self.open_cleanup_queued:
                                _sleep(0.01)
                            emit_open_cleanup_signal()  # _open_cleanup_signal uses _gui._open_cleanup_slot()
                            self.open_cleanup_queued = False
                            while _gui.open_in_progress and not self.open_cleanup_queued:
                                _sleep(0.01)            # wait for media opening to finish
                        else:
                            _emit_update_progress_signal(_gui.frame_override)
                        _gui.frame_override = -1        # reset frame_override

                        # force high-precision progress bar to reset its starting offset
                        if not self.add_to_progress_offset:
                            self.add_to_progress_offset = 0.1
                        self.reset_progress_offset = True

                    # no frame override -> set slider to VLC's progress if VLC has actually updated
                    else:
                        new_frame = (self.get_position() * _gui.frame_count) + vlc_offset   # convert VLC position to frame
                        if new_frame >= get_ui_frame():         # if progress is updated (and didn't go backwards), update UI
                            _emit_update_progress_signal(new_frame)
                        #else:                          # if VLC literally went backwards (common) -> simulate a non-backwards update
                        #    interpolated_frame = int(new_frame + (_gui.frame_rate / 5))
                        #    _emit_update_progress_signal(interpolated_frame)               # TODO can this snowball and keep jumping forward forever?

                        # NOTE: for some reason, putting this as an `else` above...
                        # ...just... doesn't work. it repaints very inconsistently
                        repaint_slider()                # manually repaint slider for various animations to work
                        _sleep(min_fps_delay)           # update position at 15FPS (every ~0.0667 seconds -> libvlc updates every ~0.2-0.35 seconds)

        # all loops broken, player backend disabled
        self.slider_thread_open = False
        return logging.info('VLC player disabled. Ending update_slider thread.')




class PlayerQt(PyPlayerBackend):
    ''' Two years later, I finally came back to finish this. It's hard to forget.
        I don't forget. What were we talking about? 3/1/22 - 3/9/24. '''

    __name__ = 'Qt'
    SUPPORTS_PARSING = True
    SUPPORTS_VIDEO_TRACK_MANIPULATION = False
    SUPPORTS_AUDIO_TRACK_MANIPULATION = False
    SUPPORTS_SUBTITLE_TRACK_MANIPULATION = False
    SUPPORTS_AUTOMATIC_SUBTITLE_ENABLING = False
    ENABLE_AUTOMATIC_TRACK_RESTORATION = False          # False because we don't support tracks in the first place
    ENABLE_AUTOMATIC_TRACK_RESET = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._metadata_available = False
        self._media_status = QtMultimedia.QMediaPlayer.MediaStatus.NoMedia
        self._null_media = QtMultimedia.QMediaContent()

        self._player: QtMultimedia.QMediaPlayer = None
        self._video_widget: QtMultimediaWidgets.QVideoWidget = None
        self.player_and_widget_paired = False

        self._frame_timer = QtCore.QTimer()
        self._frame_timer.timeout.connect(self._on_timer)
        self.ignore_zero_progress = False
        self.lock_timer = False

        # TODO: add this to menu
        #for key in player.availableMetaData():
        #    try: print(key, player.metaData(key))
        #    except: print(format_exc())


    def enable(self) -> bool:
        super().enable()

        # TODO: should we be reusing this instead of creating new ones? no, right?
        player = self._player = QtMultimedia.QMediaPlayer(None, QtMultimedia.QMediaPlayer.VideoSurface)

        self.get_playback_rate = player.playbackRate
        self.set_playback_rate = player.setPlaybackRate
        self.get_position = lambda: (player.position() / 1000) / gui.duration
        self.set_position = lambda pos: player.setPosition(int((pos * gui.duration) * 1000))
        self.get_volume = player.volume
        self.set_volume = player.setVolume
        self.get_mute = player.isMuted
        self.set_mute = player.setMuted
        self.pause = lambda: player.pause() if player.state() == QtMultimedia.QMediaPlayer.PlayingState else player.play()
        self.set_pause = lambda paused: player.pause() if paused else player.play()
        self.stop = lambda: player.setMedia(self._null_media)   # NOTE: `player.stop()` does not actually release file locks
        self.is_parsed = lambda: self._metadata_available       # minor optimization (isMetaDataAvailable() is slightly more involved)
        self.is_playing = lambda: player.state() == QtMultimedia.QMediaPlayer.PlayingState
        self.get_fps = lambda: player.metaData('VideoFrameRate') or 0.0
        self.get_duration = lambda: player.duration() / 1000

        # signals (NOTE: `positionChanged`/`setNotifyInterval()` is not used...
        # ...since we need to consistently repaint the slider regardless)
        player.error.connect(self._on_error)
        player.metaDataAvailableChanged.connect(lambda available: setattr(self, '_metadata_available', available))
        player.mediaStatusChanged.connect(self._on_media_status_changed)

        # create video surface to render our media onto (multiple choices here)
        video_widget = self._video_widget = QtMultimediaWidgets.QVideoWidget(self.parent)
        video_widget.setAspectRatioMode(Qt.KeepAspectRatio)     # TODO make IgnoreAspectRatio a player-specific setting

        # QVideoWidget defaults to looking like a flashbang
        p = QtGui.QPalette()
        p.setColor(QtGui.QPalette.Window, Qt.transparent)
        video_widget.setPalette(p)
        video_widget.setAttribute(Qt.WA_OpaquePaintEvent, True)

        # QVideoWidget really loves eating mouse events no matter how hard you try to stop it
        video_widget.setMouseTracking(True)
        video_widget.mousePressEvent = self.parent.mousePressEvent
        video_widget.mouseMoveEvent = self.parent.mouseMoveEvent
        video_widget.mouseReleaseEvent = self.parent.mouseReleaseEvent
        video_widget.mouseDoubleClickEvent = self.parent.mouseDoubleClickEvent
        video_widget.wheelEvent = self.parent.wheelEvent
        video_widget.enterEvent = self.parent.enterEvent
        video_widget.leaveEvent = self.parent.leaveEvent

        # start ui-updating timer
        if gui.mime_type == 'image':
            interval = 50 if gui.isFullScreen() else 200        # update at 5fps for images (or 20fps if we're fullscreen)
        else:
            interval = max(17, min(50, gui.delay * 1000))       # clamp interval to 17-50ms (~59-20fps)
        self._frame_timer.start(interval)
        return True


    def disable(self, wait: bool = True):
        super().disable()
        self.player_and_widget_paired = False
        self._frame_timer.stop()
        self._player.deleteLater()
        self._video_widget.deleteLater()


    def show(self):
        if not self.player_and_widget_paired:
            self._player.setVideoOutput(self._video_widget)
            if gui.mime_type == 'video':
                self._video_widget.show()
            else:
                self._video_widget.hide()
            self.player_and_widget_paired = True
        self._video_widget.resize(self.parent.size())


    def _on_timer(self):
        ''' Qt event. '''
        if not gui.is_paused and not self.lock_timer:
            frame = int((self._player.position() / 1000) * gui.frame_rate)
            if frame:                                       # sometimes Qt will try to reset UI to 0 when we don't want it to
                gui.update_progress(frame)
                self.ignore_zero_progress = False           # reset flag now that Qt is reporting the correct progress
            elif not self.ignore_zero_progress:             # only allow a `frame` of 0 if we're not ignoring it
                gui.update_progress(0)
        else:                                               # continue painting hover timestamp/fullscreen UI while paused
            gui.sliderProgress.update()


    def _on_error(self, error: QtMultimedia.QMediaPlayer.Error):
        ''' Qt event. '''
        logger.error(f'(!) PlayerQt reported an error: {error}')
        if error == QtMultimedia.QMediaPlayer.Error.FormatError:
            gui.log_on_statusbar_signal.emit('(!) You do not have the proper codecs install to correctly play this file.')


    def _on_media_status_changed(self, status: QtMultimedia.QMediaPlayer.MediaStatus):
        ''' Qt event. '''
        logger.debug(f'Media status changed to {status} (restarted={gui.restarted}, ui_frame={gui.sliderProgress.value()})')

        # HACK: QMediaPlayer likes to just... go longer than the video? like the frame it reports is often...
        # ...impossible, so to ensure that the frame doesn't visually change when we're restarting...
        # ...(QMediaPlayer resets to frame 0 on media finish), we set the progress to 200%
        # TODO: this unfortunately has HORRIBLE side effects when resizing. we can go over 100%...
        # ...progress, as long as it conforms to whatever fake frame Qt thinks the media can go...
        # ...to, but I have no idea how to determine this value
        if status == QtMultimedia.QMediaPlayer.MediaStatus.BufferedMedia and gui.restarted:
            self.set_and_update_progress(gui.frame_count * 2)
        elif status == QtMultimedia.QMediaPlayer.MediaStatus.EndOfMedia and not gui.is_paused and not gui.restarted:
            self._media_status = QtMultimedia.QMediaPlayer.MediaStatus.LoadingMedia
            gui.restart_signal.emit()
        else:
            self._media_status = status


    def on_resize(self, event: QtGui.QResizeEvent):
        self._video_widget.resize(event.size())
        #self._video_widget.resize(1920, 1080)              # TODO this can be used for video zooming


    def on_fullscreen(self, fullscreen: bool):
        if gui.mime_type == 'image':                        # use 20fps for images in fullscreen
            self._frame_timer.setInterval(50 if fullscreen else 200)


    def on_parse(self, file: str, base_mime: str, mime: str, extension: str):
        if mime == 'video':
            self._video_widget.show()
        else:
            self._video_widget.hide()

        if mime == 'image':
            self.lock_timer = True
            interval = 50 if gui.isFullScreen() else 200    # update at 5fps for images (or 20fps if we're fullscreen)
        else:
            self.lock_timer = False                         # ↓ clamp interval to 17-50ms (~59-20fps) TODO: `int()` or `round()` here?
            interval = max(17, min(50, int(gui.delay * 1000)))

        gui._open_cleanup_signal.emit()
        self._frame_timer.setInterval(interval)
        logger.info(f'PlayerQt timer set to {interval:.2f}ms')


    def on_restart(self):
        ''' Called in `gui.restart()`, immediately after confirming the restart
            is valid. `gui.restarted` will be False. After this event, the UI
            be updated and the player will be force-paused. This event should
            do any extraneous cleanup that must be urgently completed to ensure
            finished media is immediately/seamlessly ready to play again. '''
        frame = gui.sliderProgress.value()
        #if frame == gui.frame_count:
        #    #frame = int((self._player.position() / 1000) * gui.frame_rate)
        #    frame = int((self._player.position() / 1000) * self._player.metaData('VideoFrameRate'))
        self.play(gui.video, will_restore=True)             # Qt will report the frame as 0 for a bit -> ignore this
        self.set_and_update_progress(frame, SetProgressContext.RESTART)


    def play(self, file: str, will_restore: bool = False, _error: bool = False):
        try:
            self.ignore_zero_progress = will_restore
            self._player.setMedia(QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(file)))
            self._player.play()
            self.file_being_opened = file
            return True
        except:
            logger.warning(f'QMediaPlayer failed to play video {file}: {format_exc()}')
            if not _error:                                  # `_error` ensures we only attempt to play previous video once
                if not gui.video: self._player.stop()       # no previous video to play, so just stop playing
                else: self.play(gui.video, _error=True)     # attempt to play previous working video
            return False


    def get_state(self):
        if self._media_status == QtMultimedia.QMediaPlayer.EndOfMedia:
            return State.Ended
        return {
            QtMultimedia.QMediaPlayer.PlayingState: State.Playing,
            QtMultimedia.QMediaPlayer.PausedState:  State.Paused,
            QtMultimedia.QMediaPlayer.StoppedState: State.Stopped,
        }.get(self._player.state(), State.Playing)


    def get_dimensions(self) -> tuple[int, int]:            # it's okay if we throw an exception here
        size: QtCore.QSize = self._player.metaData('Resolution') or self._video_player.sizeHint()
        return size.width(), size.height()


    def set_and_update_progress(self, frame: int = 0, context: int = SetProgressContext.NONE):
        # don't touch progress if we're currently opening a file
        if gui.open_in_progress:
            return

        if context == SetProgressContext.NAVIGATION_RELATIVE:
            self.lock_timer = True
            gui.update_progress(frame)
            self._player.setPosition(int((frame / gui.frame_rate) * 1000))
            self.lock_timer = False
        else:
            self._player.setPosition(int((frame / gui.frame_rate) * 1000))
            gui.update_progress(frame)
            if context == SetProgressContext.RESTORE:       # HACK: this helps fix flickering on the slider when switching from a...
                gui.frame_override = frame                  # ...player that uses `update_progress_signal`, but otherwise does nothing
        gui.gifPlayer.gif.jumpToFrame(frame)

