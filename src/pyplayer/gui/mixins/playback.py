"""Playback controls — volume, tracks, rate, navigation."""
from __future__ import annotations

import logging
import os
from time import time as get_time

from PyQt5 import QtCore, QtGui, QtWidgets as QtW
from vlc import State

from pyplayer.core.constants import APP_RUNNING, IS_WINDOWS


logger = logging.getLogger(__name__)


class PlaybackMixin:
    """Methods: pause, stop, volume, tracks, rate, fullscreen, navigation."""

    def pause(self) -> bool:
        ''' Pauses/unpauses the media. Handles updating GUI, cleaning
            up/restarting, clamping progress to current trim, displaying
            the pause state on-screen, wrapping around the progress bar. '''
        will_pause = False

        # images/gifs
        if self.mime_type == 'image':
            if self.is_gif:                         # check if gif's filename is correct. if not, restart the gif and restore position
                old_state = image_player.gif.state()
                was_paused = old_state != QtGui.QMovie.Running          # ↓ .fileName() is formatted wrong -> fix with `abspath`
                if was_paused and abspath(image_player.gif.fileName()) != image_player.filename:
                    image_player.gif.setFileName(image_player.filename)
                    set_gif_position(get_ui_frame())
                image_player.gif.setPaused(not was_paused)
                will_pause = not was_paused
                frame = image_player.gif.currentFrameNumber()
            else:                                                       # just return if it's a static image
                return True

        # videos/audio
        else:
            frame = get_ui_frame()
            old_state = player.get_state()
            if old_state == State.Stopped:
                if self.restart() == -1:                                # restart media if currently stopped
                    return True                                         # -1 means media doesn't exist anymore
                set_and_update_progress(frame, SetProgressContext.RESTORE)

            if frame >= self.maximum or frame < self.minimum:           # play media from beginning if media is over
                self.lock_progress_updates = True
                set_and_update_progress(self.minimum, SetProgressContext.RESTART)
                self.lock_progress_updates = False
            player.pause()                                              # actually pause underlying player
            will_pause = True if old_state == State.Playing else False  # prevents most types of pause-bugs...?

        # update internal property as soon as we safely can
        self.is_paused = will_pause

        # update pause button
        self.buttonPause.setIcon(self.icons['play' if will_pause else 'pause'])
        if settings.checkTextOnPause.isChecked():
            pause_text = '𝗜𝗜' if will_pause else '▶'                    # ▷ ▶ ⏵︎
            show_on_player(pause_text)

        # update titlebar and taskbar icon
        refresh_title()
        self.refresh_taskbar()
        self.restarted = False
        logging.debug(f'Pausing: is_paused={will_pause} old_state={old_state} frame={frame} maxframe={self.maximum}')
        return will_pause

    def force_pause(self, paused: bool):
        ''' Immediately set pause-state to `paused`, without
            clamping, wrapping, restarting, or showing marquees. '''
        if self.is_gif: image_player.gif.setPaused(paused)
        else: player.set_pause(paused)
        self.is_paused = paused

        icon = self.icons['play' if paused else 'pause']
        self.buttonPause.setIcon(icon)

        refresh_title()
        self.refresh_taskbar()
        logging.debug(f'Force-pause: paused={paused}')
        return paused

    def stop(self, *, icon: str = 'stop'):          # * to capture unused signal args
        ''' A more robust way of stopping - stop the player while also force-
            pausing. `icon` specifies what icon to use on the pause button. '''
        player.stop()
        image_player.gif.setFileName('')

        if self.is_gif: image_player.gif.setPaused(True)
        else: player.set_pause(True)
        self.is_paused = True
        self.buttonPause.setIcon(self.icons[icon])

        # if the media is over, mark ourselves as having NOT restarted yet -> this...
        # ...keeps us from getting confused if the media file is renamed/deleted
        if get_ui_frame() == self.frame_count:
            self.restarted = False

        refresh_title()
        self.refresh_taskbar()
        if IS_WINDOWS and settings.checkTaskbarIconPauseMinimized.isChecked():
            self.taskbar.clearOverlayIcon()

        logging.debug('Player stopped.')

    def set_volume(self, volume: int, verbose: bool = True) -> int:
        ''' Sets and displays `volume`, multiplied by `self.volume_boost`.
            Quietly unmutes player if necessary. Refreshes UI and displays
            a marquee (if `verbose`). Returns the new boosted volume,
            or -1 if unsuccessful. '''
        try:
            boost = self.volume_boost
            boosted_volume = int(volume * boost)
            player.set_volume(boosted_volume)
            player.set_mute(False)
            self.sliderVolume.setEnabled(True)

            if settings.checkTextOnVolume.isChecked() and verbose:
                show_on_player(f'{boosted_volume}%%', 200)
            refresh_title()
            self.refresh_volume_tooltip()
            return boosted_volume
        except:
            if APP_RUNNING:                   # `show_on_player` errors out when the config triggers this on launch
                logging.error(f'(!) Failed to set volume: {format_exc()}')
            return -1

    def set_volume_boost(self, value: float = 1.0, increment: bool = False):
        ''' Sets `self.volume_boost` to `value`, or increments it by `value`
            if `increment` is True. Refreshs UI and displays marquee.
            NOTE: Cancels if a file was opened in the last 0.35 seconds. '''
        cancel_delta = get_time() - self.last_open_time
        if cancel_delta < 0.35:
            logging.info(f'Blocking possibly accidental volume boost (triggered {cancel_delta:.2f} seconds after opening a file)')
            return

        base_volume = self.sliderVolume.value()
        if increment: boost = max(0.5, min(5, self.volume_boost + value))
        else:         boost = max(0.5, min(5, value))

        self.volume_boost = boost
        if not player.get_mute(): self.set_volume(base_volume)
        else: self.refresh_volume_tooltip()

        if boost == 1.0: marq = f'{boost:.1f}x volume boost ({base_volume}%%)'
        else:            marq = f'{boost:.1f}x volume boost ({base_volume}%% -> {base_volume * boost:.0f}%%)'
        self.marquee(marq, marq_key='VolumeBoost', log=False)

    def set_mute(self, muted: bool, verbose: bool = True) -> int:
        ''' Sets mute-state to `muted`, updates UI, and shows a marquee (if
            `verbose`). Returns the player's new internal mute-state value. '''
        try:
            player.set_mute(muted)
            self.sliderVolume.setEnabled(not muted)     # disabled if muted, enabled if not muted
            base_volume = get_volume_slider()
            boost = self.volume_boost

            if muted:          marq = f'Muted{self.get_hotkey_full_string("mute")}'
            elif boost == 1.0: marq = f'Unmuted ({base_volume}%%)'
            else:              marq = f'Unmuted ({base_volume}%% -> {base_volume * boost:.0f}%%)\n{boost:.1f}x volume boost'

            if settings.checkTextOnMute.isChecked() and verbose:
                show_on_player(marq)
            self.refresh_volume_tooltip()
        except: logging.error(f'(!) Failed to set mute state: {format_exc()}')
        finally: return player.get_mute()

    def toggle_mute(self):
        ''' Toggles mute-state to the opposite of
            `self.sliderVolume`'s enable-state. '''
        self.set_mute(self.sliderVolume.isEnabled())

    def set_playback_rate(self, rate: float, increment: bool = False):
        ''' Sets the playback `rate` for the media, or increments it by
            `rate` if `increment` is True. Displays a marquee if desired. '''
        if increment:
            rate += self.playback_rate
        rate = round(rate, 4)                           # round `rate` to 4 places to avoid floating point imprecision

        player.set_playback_rate(rate)
        image_player.gif.setSpeed(int(rate * 100))
        self.playback_rate = rate

        if settings.checkTextOnSpeed.isChecked():
            show_on_player(f'{rate:.2f}x', 1000)
        log_on_statusbar(f'Playback speed set to {rate:.2f}x')

    def set_subtitle_delay(self, msec: int = 50, increment: bool = False, marq: bool = True):
        ''' Sets the subtitle delay to `msec`, or increments it by `msec` if
            `increment` is True. Displays a marquee if `marq` is True. '''
        if player.get_subtitle_track_count() <= 0:
            if marq:
                self.marquee('No subtitles available', marq_key='SubtitleDelay', log=False)
            return

        if increment:
            msec += player.get_subtitle_delay()
        player.set_subtitle_delay(int(msec))

        if marq:
            suffix = ' (later)' if msec > 0 else ' (sooner)' if msec < 0 else ''
            self.marquee(f'Subtitle delay {msec / 1000:.2f}s{suffix}', marq_key='SubtitleDelay', log=False)
        self.last_subtitle_delay = msec
        self.tracks_were_changed = True

    def set_audio_delay(self, msec: int = 50, increment: bool = False, marq: bool = True):
        ''' Sets the audio delay to `msec`, or increments it by `msec` if
            `increment` is True. Displays a marquee if `marq` is True. '''
        if player.get_audio_track_count() <= 0:
            if marq:
                self.marquee('No audio tracks available', marq_key='SubtitleDelay', log=False)
            return

        if increment:
            msec += player.get_audio_delay()
        player.set_audio_delay(int(msec))

        if marq:
            suffix = ' (later)' if msec > 0 else ' (sooner)' if msec < 0 else ''
            self.marquee(f'Audio delay {msec / 1000:.2f}s{suffix}', marq_key='SubtitleDelay', log=False)

        self.last_audio_delay = msec
        self.tracks_were_changed = True

    def set_fullscreen(self, fullscreen: bool):
        ''' Toggles fullscreen-mode on and off. Saves window-state to
            `self.was_maximized` to remember if the window is maximized
            or not and restore the window accordingly. '''

        # FramelessWindowHint and WindowStaysOnTopHint not needed
        self.dockControls.setFloating(fullscreen)

        # entering fullscreen
        if fullscreen:  # TODO: figure out why dockControls won't resize in fullscreen mode -> strange behavior when showing/hiding control-frames
            current_screen = app.screenAt(self.mapToGlobal(self.rect().center()))   # fullscreen destination is based on center of window
            screen_size = current_screen.size()
            screen_geometry = current_screen.geometry()

            width_factor = settings.spinFullScreenWidth.value() / 100
            width = int(screen_size.width() * width_factor)
            height = sum(frame.height() for frame in (self.frameProgress, self.frameAdvancedControls) if frame.isVisible())
            x = int(screen_geometry.right() - ((screen_size.width() + width) / 2))  # adjust x/y values for screen's actual global position
            y = screen_geometry.bottom() - height

            self.dockControls.resize(width, height)
            #self.dockControls.setFixedWidth(width)     # TODO this is bad for DPI/scale and doesn't even fully get rid of the horizontal separator cursors. bandaid fix
            self.dockControls.move(x, y)
            self.dockControls.setWindowOpacity(settings.spinFullScreenMaxOpacity.value() / 100)     # opacity only applies while floating

            self.statusbar.setVisible(False)
            self.menubar.setVisible(False)              # TODO should this be like set_crop_mode's version? this requires up to 2 alt-presses to open
            self.was_maximized = self.isMaximized()     # remember if we're maximized or not

            # don't fade UI if we're hovering over the pending dockControls rect, the media...
            # ...is not playing (but not because we're paused), or the media is an image/GIF
            if settings.checkHideIdleCursor.isChecked():
                always_lock_ui = not player.is_playing() and not self.is_paused and not self.mime_type == 'image'
                if always_lock_ui or QtCore.QRect(x, y, width, height).contains(QtGui.QCursor.pos()):
                    self.vlc.idle_timeout_time = 0.0
                else:                                   # set timer to act like we JUST stopped moving the mouse
                    self.vlc.idle_timeout_time = get_time() + settings.spinHideIdleCursorDuration.value()

            player.on_fullscreen(fullscreen)
            self.ignore_next_fullscreen_move_event = True
            self.showFullScreen()                       # FullScreen with a capital S

        # leaving fullscreen
        else:
            self.statusbar.setVisible(self.actionShowStatusBar.isChecked())
            self.menubar.setVisible(self.actionShowMenuBar.isChecked())
            #self.dockControls.setFixedWidth(QWIDGETSIZE_MAX)

            player.on_fullscreen(fullscreen)
            self.showMaximized() if self.was_maximized else self.showNormal()

    def toggle_maximized(self):
        if self.isFullScreen():
            self.actionFullscreen.trigger()
        if self.isMaximized():
            self.showNormal()
        else:
            self.invert_next_move_event = True
            self.invert_next_resize_event = True
            self.showMaximized()

    def set_track(self, track_type: str, track: int = -1, index_hint: int = None, title: str = None):
        ''' Sets `track_type` ("video", "audio", or "subtitle") to `track`,
            which can be either the `track`'s index or its associated
            `QtW.QAction`. If provided, `index_hint` is the index to
            show in the marquee instead of the garbage nonsense number
            that it probably was. `title` is the custom title to use in
            the marquee. This must be provided manually.'''
        logging.debug(f'Setting "{track_type}" track to {track} (hint={index_hint}, title={title})')
        types = {'video':    (-1, player.set_video_track),      # -1 = disabled, 0 = track 1
                 'audio':    (0,  player.set_audio_track),      # -1 = disabled, 1 = track 1
                 'subtitle': (1,  player.set_subtitle_track)}   # -1 = disabled, 2 = track 1
        offset_from_1, _set_track = types[track_type]           # TODO check back on this when more track-supporting players are added

        if isinstance(track, QtW.QAction):                      # `track` is actually a QAction
            index_hint = int(track.toolTip())                   # true index is stored in the action's tooltip
            #title = title or track.text()                      # TODO: should we still show the title even though the user literally clicked on it?
            track = track.data()                                # track index is stored in the action's `data` property

        # actually set the track, then choose what number we're going to show in the marquee
        _set_track(track)
        setattr(self, f'last_{track_type}_track', track)        # remember the track we've chosen so we can restore it
        track_index = index_hint if index_hint is not None else (track - offset_from_1)

        # check if `title` is actually unique and not something like "Track 1"
        if title is not None:
            parts = title.split()
            if len(parts) > 1 and parts[0].lower() == 'track':  # ↓ detect things like 'Track "2"' or 'Track 2)'
                if parts[1].strip('"\'()[]{}<>;:-').isnumeric():
                    if len(parts) > 2:                          # ↓ skip third "word" if it's just a hyphen or something
                        start = 2 if parts[2].strip('"\'()[]{}<>;:-') else 3
                        title = ' '.join(parts[start:])
                    else: title = None
                else: title = None

        # if `title` is (or has become) None, use generic marquee, i.e. "Audio track 2 enabled"
        # otherwise, use something like "Audio track 2 'Microphone' enabled"
        if track != -1:
            prefix = f'{track_type.capitalize()} track {track_index}'
            if title: title = f'{prefix}  \'{title}\' enabled'
            else:     title = f'{prefix} enabled'
            marquee(title, marq_key='TrackChanged', log=False)
        else:
            if getattr(player, f'SUPPORTS_{track_type.upper()}_TRACK_MANIPULATION'):
                if track_type == 'subtitle':
                    track_type = 'subtitles'                    # prefer "Subtitles disabled" over "Subtitle disabled"
                marquee(f'{track_type.capitalize()} disabled', marq_key='TrackChanged', log=False)
            else:
                marquee(f'The selected player does not support {track_type} track manipulation', marq_key='TrackChanged', log=False)

        self.tracks_were_changed = True
        gc.collect(generation=2)

    def cycle_track(self, track_type: str):
        ''' Cycles to the next valid `track_type` ("video", "audio", or
            "subtitle"), if one is available. Depending on settings, this
            may loop back around to either "Disabled" or track #1. Displays
            a marquee if cycle could not play a new track. '''
        types = {'video':    (player.get_video_tracks,    player.get_video_track_count,    player.get_video_track),
                 'audio':    (player.get_audio_tracks,    player.get_audio_track_count,    player.get_audio_track),
                 'subtitle': (player.get_subtitle_tracks, player.get_subtitle_track_count, player.get_subtitle_track)}
        get_ids_and_titles, get_count, get_current_id = types[track_type]

        track_count = get_count() - 1
        if track_count > 0:
            current_track_id = get_current_id()
            first_track_parameters = (-1, None, None)
            show_title = settings.checkTrackCycleShowTitle.isChecked()
            for index, (track_id, track_title) in enumerate(get_ids_and_titles(raw=True)):
                track_title = track_title if show_title else None
                if first_track_parameters[0] == -1 and track_id > -1:
                    first_track_parameters = (track_id, index, track_title)
                if track_id > current_track_id:                 # ^ mark the first valid track
                    self.set_track(track_type, track_id, index, track_title)
                    break

            # `else` is reached if we didn't break the for-loop (we ran out of tracks to cycle through)
            # loop back to either the first valid track or to "disabled", depending on user settings
            else:
                if settings.checkTrackCycleCantDisable.isChecked():
                    if first_track_parameters[0] != current_track_id:
                        self.set_track(track_type, *first_track_parameters)
                    else:                                       # display special message if there's nothing else to cycle to
                        marquee(f'No other {track_type} tracks available', marq_key='TrackChanged', log=False)
                else:
                    self.set_track(track_type, -1)
        else:
            if getattr(player, f'SUPPORTS_{track_type.upper()}_TRACK_MANIPULATION'):
                marquee(f'No {track_type} tracks available', marq_key='TrackChanged', log=False)
            else:
                marquee(f'The selected player does not support {track_type} track manipulation', marq_key='TrackChanged', log=False)

    def restore_tracks(self, safely: bool = False):
        ''' Restores the previously selected audio/subtitle/video track/delays.
            This is needed because some players reset all track selections after
            they're stopped. If `safely` is True, safeguards are used to prevent
            infinite loops, even in the event of a corrupted file being opened.
            `safely` should only be used for players that cannot do not emit
            their own events for opening/playing media. '''

        video = self.video                                      # remember what video we were trying to open
        if not self.tracks_were_changed:
            return

        if safely:
            # tracks cannot be consistently set or read properly while in the `Opening` state
            # NOTE: this mostly affects keeping tracks disabled since the track numbers default...
            # ...to disabled so we can't tell if the track is actually disabled yet or not
            timeout = get_time() + 3.0
            while (player.get_state() == State.NothingSpecial or player.get_state() == State.Opening) and video == self.video and get_time() < timeout:
                if get_time() > timeout:
                    return log_on_statusbar('(!) Could not restore track selections, libVLC failed to leave the "Opening" state after 3 seconds.')
                sleep(0.002)

            # make sure we didn't open a new file just now. this SHOULD be impossible, but just in case
            if video != self.video:
                return logging.info('(?) Track restoration cancelled, file is changing.')

        # most to least important: audio -> subtitles -> subtitle delay -> audio delay -> video
        logging.info('Restoring tracks to their previous selections...')
        try: player.set_audio_track(self.last_audio_track)
        except: pass
        try: player.set_subtitle_track(self.last_subtitle_track)
        except: pass
        try: self.set_subtitle_delay(self.last_subtitle_delay, marq=False)
        except: pass
        try: self.set_audio_delay(self.last_audio_delay, marq=False)
        except: pass
        try: player.set_video_track(self.last_video_track)
        except: pass

        # clear marquee if needed
        player.show_text('')

    def page_step(self, step: float = 0.1, forward: bool = True, scaled: bool = True):
        ''' Page-steps through the progress slider by `step`, a percentage from
            0-1, `forward` or backwards. If `step` is negative, `forward` is
            inverted. If `scaled` is True, `step` is scaled to `self.minimum`
            and `self.maximum`, otherwise `self.frame_count`. Page-steps are
            clamped to `self.minimum`/`self.maximum` regardless. '''

        old_frame = get_ui_frame()
        maximum = self.maximum
        minimum = self.minimum
        if scaled: step = int((maximum - minimum) * step)
        else:      step = int(self.frame_count * step)

        if forward and step > 0:
            if old_frame == maximum:
                return set_progress_slider(old_frame)   # visually clamp slider to maximum if we can't go forward
            new_frame = min(maximum, old_frame + step)
        else:
            new_frame = max(minimum, old_frame - step)

        set_and_update_progress(new_frame, SetProgressContext.NAVIGATION_RELATIVE)
        if self.restarted and settings.checkNavigationUnpause.isChecked():
            self.force_pause(False)                     # auto-unpause after restart if desired
            self.restarted = False

    def navigate(self, forward: bool, seconds_spinbox: QtW.QSpinBox):   # slightly longer than it could be, but cleaner/more readable
        ''' Navigates `forward` or backwards through the current
            media by the value specified in `seconds_spinbox`.

            NOTE: `seconds` has been replaced by `seconds_spinbox`
            since the former was never explicitly used. '''

        # cycle images with basic navigation keys
        if self.is_static_image: return self.cycle_media(next=forward)
        old_frame = get_ui_frame()
        seconds = seconds_spinbox.value()

        # calculate and update to new frame as long as it's within our bounds
        if forward:                                     # media will wrap around cleanly if it goes below 0/above max frames
            if old_frame == self.frame_count and settings.checkNavigationWrap.isChecked(): new_frame = 0
            else: new_frame = min(self.maximum, int(old_frame + self.frame_rate_rounded * seconds))
        else:                                           # NOTE: only wrap start-to-end if we're paused
            if old_frame == 0 and self.is_paused and settings.checkNavigationWrap.isChecked(): new_frame = self.frame_count
            else: new_frame = max(self.minimum, int(old_frame - self.frame_rate_rounded * seconds))

        # set progress to new frame while doing necessary adjustments/corrections/overrides
        set_and_update_progress(new_frame, SetProgressContext.NAVIGATION_RELATIVE)

        # HACK: if navigating away from end of media while unpaused and we HAVEN'T restarted...
        # ...yet -> ignore the restart we're about to do (does this only apply to VLC?)
        self.ignore_imminent_restart = old_frame == self.frame_count and not self.is_paused and not self.restarted

        # auto-unpause after restart if desired
        if self.restarted and settings.checkNavigationUnpause.isChecked():
            self.force_pause(False)
            self.restarted = False

        # show new position as a marquee if desired
        if self.isFullScreen() and settings.checkTextOnFullScreenPosition.isChecked():
            h, m, s, _ = get_hms(self.current_time)
            current_text = f'{m:02}:{s:02}' if h == 0 else f'{h}:{m:02}:{s:02}'
            max_text = self.labelMaxTime.text()[:-3] if self.duration_rounded < 3600 else self.labelMaxTime.text()
            show_on_player(f'{current_text}/{max_text}')

        logging.debug(f'Navigated {"forwards" if forward else "backwards"} {seconds} second(s), going from frame {old_frame} to {new_frame}')

    def update_gif_progress(self, frame: int):
        ''' Updates animated GIF progress by manually looping
            the GIF when outside the designated trim markers. '''
        if self.is_gif:
            slider = self.sliderProgress
            if self.minimum <= frame <= self.maximum:
                update_progress(frame)                  # HACK: literally, forcibly repaint to stop slider from...
                if frame != self.minimum:               # ...eventually freezing on animated GIFs in fullscreen...
                    slider.repaint()                    # ...(no idea why it happens)
            elif not slider.grabbing_clamp_minimum and not slider.grabbing_clamp_maximum:
                set_gif_position(self.minimum)          # reset to minimum if we're not dragging the markers

    def update_progress(self, frame: int):
        ''' Updates every section of the UI to reflect the
            current `frame`. Clamps playback to desired trims.
            Loops if necessary. Locks spinboxes while updating. '''
        # When trim is active, update maximum (END) to follow current position
        # But minimum (START) stays locked at where Trim was clicked
        if self.buttonTrim.isChecked() and frame > self.maximum:
            self.maximum = frame

        # Allow playback beyond minimum - START is locked, but playback continues
        # Only stop if we reach the actual end of video
        if frame >= self.sliderProgress.maximum():
            if self.buttonTrim.isChecked():
                if not self.actionLoop.isChecked():
                    self.force_pause(True)
                    set_and_update_progress(self.minimum, SetProgressContext.RESET_TO_MIN)
                else:
                    return set_and_update_progress(self.minimum, SetProgressContext.RESET_TO_MIN)

        current_time = round(self.duration_rounded * (frame / self.frame_count), 2)
        self.current_time = current_time

        # this is `util.get_hms` but inlined, for optimization
        h_remainder = current_time % 3600
        h = int(current_time // 3600)
        m = int(h_remainder // 60)
        s = int(h_remainder % 60)
        ms = int(round((current_time - int(current_time)) * 100, 4))

        set_progress_slider(frame)
        if not current_time_lineedit_has_focus():       # use cleaner format for time-strings on videos > 1 hour
            set_current_time_text(f'{m:02}:{s:02}.{ms:02}' if h == 0 else f'{h}:{m:02}:{s:02}')

        set_hour_spin(h)
        set_minute_spin(m)
        set_second_spin(s)
        set_frame_spin(frame)

    def _update_progress_slot(self, frame: int):
        ''' A slot for updating the UI in a thread-safe manner. Because of the
            possible delay, this slot also checks for `self.frame_override`. '''
        if self.frame_override != -1:
            update_progress(self.frame_override)
        else:
            update_progress(frame)
