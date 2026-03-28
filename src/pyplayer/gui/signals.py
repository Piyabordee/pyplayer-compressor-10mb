"""Widget signal/slot connections.

Extracted from qtstart.py connect_widget_signals().
"""
from __future__ import annotations

import os

from PyQt5 import QtWidgets as QtW
from PyQt5.QtCore import Qt

from pyplayer import config, constants, qthelpers


def connect_widget_signals(self: QtW.QMainWindow):
    """Connect all widget signals and slots."""
    def set_save_progress_value_and_format(value: int, format: str):
        ''' This ensures the edit progress bar's value and
            text change at the same time. For aesthetics. '''
        self.save_progress_bar.setValue(value)
        self.save_progress_bar.setFormat(format)

    def save_or_rename_or_open():
        ''' If Shift is held, the currently entered output text is opened if it
            points to an existing file. Otherwise, `self.save()` is called. '''
        if self.app.keyboardModifiers() & Qt.ShiftModifier:
            output, _, _ = self.get_output()
            if output and os.path.exists(output):
                self.open(file=output)
            elif output:
                self.statusbar.showMessage('Entered filename does not exist.')
        else:
            self.save()

    self._open_cleanup_signal.connect(self._open_cleanup_slot)
    self._open_signal.connect(lambda kwargs: self.open(**kwargs))
    self._open_external_command_signal.connect(self._open_external_command_slot)
    self.restart_signal.connect(self.restart)
    self.force_pause_signal.connect(self.force_pause)
    self.restore_tracks_signal.connect(self.restore_tracks, type=Qt.QueuedConnection)           # `Qt.QueuedConnection` fixes `self.restart()` not unpausing
    self.concatenate_signal.connect(self.concatenate, type=Qt.QueuedConnection)                 # `Qt.QueuedConnection` fixes dropEvents freezing explorer windows
    self.show_ffmpeg_warning_signal.connect(constants._display_ffmpeg_warning)
    self.show_trim_dialog_signal.connect(self.show_trim_dialog)
    self.update_progress_signal.connect(self._update_progress_slot)
    self.refresh_title_signal.connect(self._refresh_title_slot)
    self.set_save_progress_visible_signal.connect(self.save_progress_bar.setVisible)
    self.set_save_progress_max_signal.connect(self.save_progress_bar.setMaximum)
    self.set_save_progress_value_signal.connect(self.save_progress_bar.setValue)
    self.set_save_progress_format_signal.connect(self.save_progress_bar.setFormat)
    self.set_save_progress_value_and_format_signal.connect(set_save_progress_value_and_format)
    self.disable_crop_mode_signal.connect(self.disable_crop_mode)
    self.handle_updates_signal.connect(self.handle_updates)
    self._handle_updates_signal.connect(self._handle_updates)
    self.popup_signal.connect(lambda kwargs: qthelpers.getPopup(**kwargs).exec())
    self.log_on_statusbar_signal.connect(self._log_on_statusbar_slot)

    self.sliderVolume.valueChanged.connect(self.set_volume)
    self.buttonPause.clicked.connect(self.pause)
    self.actionOpen.triggered.connect(self.open)
    self.menuFile.aboutToShow.connect(self.refresh_copy_image_action)
    self.menuRecent.aboutToShow.connect(self.refresh_recent_menu)
    self.actionClearRecent.triggered.connect(lambda: self.recent_files.clear())                 # TODO why won't `.clear` work on its own?
    self.actionExploreMediaPath.triggered.connect(self.explore)
    self.actionCopyMediaPath.triggered.connect(self.copy)
    self.actionCopyFile.triggered.connect(self.copy_file)
    self.actionCutFile.triggered.connect(lambda: self.copy_file(cut=True))
    self.actionCopyImage.triggered.connect(self.copy_image)
    self.actionSave.triggered.connect(self.save)
    self.actionSaveAs.triggered.connect(self.save_as)
    self.actionStop.triggered.connect(self.stop)
    self.actionMinimize.triggered.connect(self.close)
    self.actionExit.triggered.connect(lambda: exit(self))
    self.actionSettings.triggered.connect(self.dialog_settings.exec)
    self.menuUndo.aboutToShow.connect(self.refresh_undo_menu)
    self.actionLoop.triggered.connect(self.buttonLoop.setChecked)
    self.actionAutoplay.triggered.connect(self.refresh_autoplay_button)
    self.actionAutoplayShuffle.triggered.connect(self.refresh_autoplay_button)
    self.actionSnapshot.triggered.connect(lambda: self.snapshot(mode='full'))
    self.actionQuickSnapshot.triggered.connect(self.snapshot)
    self.actionSnapshotOpenLast.triggered.connect(lambda: self.snapshot(mode='open'))
    self.actionSnapshotOpenLastInDefault.triggered.connect(lambda: self.snapshot(mode='view'))
    self.actionSnapshotExploreLastPath.triggered.connect(lambda: self.explore(config.cfg.last_snapshot_path, 'Last snapshot'))
    self.actionSnapshotCopyLastPath.triggered.connect(lambda: self.copy(config.cfg.last_snapshot_path, 'Last snapshot'))
    self.actionSnapshotCopyLastFile.triggered.connect(lambda: self.copy_file(config.cfg.last_snapshot_path))
    self.actionSnapshotCutLastFile.triggered.connect(lambda: self.copy_file(config.cfg.last_snapshot_path, cut=True))
    self.actionSnapshotCopyLastImage.triggered.connect(lambda: self.copy_image(config.cfg.last_snapshot_path))
    self.actionSnapshotUndo.triggered.connect(lambda: self.snapshot(mode='undo'))
    self.menuDelete.aboutToShow.connect(lambda: self.actionClearMarked.setText(f'Clear marked files ({len(self.marked_for_deletion)})'))
    self.actionMarkDeleted.triggered.connect(self.buttonMarkDeleted.setChecked)
    self.actionMarkDeleted.triggered.connect(lambda checked: self.mark_for_deletion(mark=checked))
    self.actionClearMarked.triggered.connect(self.clear_marked_for_deletion)
    self.actionShowDeletePrompt.triggered.connect(self.show_delete_prompt)
    self.actionDeleteImmediately.triggered.connect(lambda: self.delete())
    self.actionEditFileTimestamps.triggered.connect(self.show_timestamp_dialog)
    self.menuVideo.aboutToShow.connect(lambda: self.actionResize.setText('&Resize'))
    self.menuVideo.aboutToShow.connect(lambda: self.actionResize.setEnabled(self.mime_type != 'audio'))
    self.menuVideoTracks.aboutToShow.connect(lambda: self.refresh_track_menu(self.menuVideoTracks))
    self.menuSubtitles.aboutToShow.connect(lambda: self.refresh_track_menu(self.menuSubtitles))
    self.actionAddSubtitleFile.triggered.connect(self.browse_for_subtitle_files)
    self.menuConcatenate.triggered.connect(self.concatenate)
    self.menuRotate.triggered.connect(self.rotate_video)
    self.actionCrop.triggered.connect(self.set_crop_mode)
    self.actionAddText.triggered.connect(self.add_text)
    self.actionResize.triggered.connect(self.resize_media)
    self.menuAudio.aboutToShow.connect(lambda: self.actionResize.setText('&Change tempo'))
    self.menuAudio.aboutToShow.connect(lambda: self.actionResize.setEnabled(self.mime_type == 'audio'))
    self.menuAudioTracks.aboutToShow.connect(lambda: self.refresh_track_menu(self.menuAudioTracks))
    self.actionIsolateVideo.triggered.connect(lambda: self.isolate_track(audio=False))
    self.actionIsolateAudio.triggered.connect(self.isolate_track)
    self.actionAmplifyVolume.triggered.connect(self.amplify_audio)
    self.actionReplaceAudio.triggered.connect(self.replace_audio)
    self.actionAddAudioTrack.triggered.connect(self.add_audio)
    self.actionShowMenuBar.triggered.connect(self.set_menubar_visible)
    self.actionShowStatusBar.triggered.connect(self.set_statusbar_visible)
    self.actionShowProgressBar.triggered.connect(self.set_progressbar_visible)
    self.actionShowAdvancedControls.triggered.connect(self.set_advancedcontrols_visible)
    self.actionFullscreen.triggered.connect(self.set_fullscreen)
    self.actionSnapSize.triggered.connect(self.snap_to_native_size)
    self.actionSnapRatio.triggered.connect(self.snap_to_player_size)
    self.actionSnapRatioShrink.triggered.connect(lambda: self.snap_to_player_size(shrink=True))
    self.actionCheckForUpdates.triggered.connect(self.handle_updates)
    self.actionViewLog.triggered.connect(lambda: qthelpers.openPath(constants.LOG_PATH))
    self.actionViewLastDirectory.triggered.connect(lambda: qthelpers.openPath(config.cfg.lastdir))
    self.actionViewInstallFolder.triggered.connect(lambda: qthelpers.openPath(constants.CWD))
    self.actionViewProbeFile.triggered.connect(self.open_probe_file)
    self.actionDeleteProbeFile.triggered.connect(lambda: self.open_probe_file(delete=True))
    self.actionAboutQt.triggered.connect(lambda: QtW.QMessageBox.aboutQt(None, 'About Qt'))
    self.actionAbout.triggered.connect(self.show_about_dialog)
    #self.check_clamp.stateChanged.connect(self.clamp)
    self.lineOutput.returnPressed.connect(save_or_rename_or_open)
    self.lineCurrentTime.returnPressed.connect(self.manually_update_current_time)
    self.spinHour.valueEdited.connect(self.update_time_spins)
    self.spinMinute.valueEdited.connect(self.update_time_spins)
    self.spinSecond.valueEdited.connect(self.update_time_spins)
    self.spinFrame.valueEdited.connect(self.update_frame_spin)
    self.spinHour.valueStepped.connect(self.update_time_spins)
    self.spinMinute.valueStepped.connect(self.update_time_spins)
    self.spinSecond.valueStepped.connect(self.update_time_spins)
    self.spinFrame.valueStepped.connect(self.update_frame_spin)

    self.buttonTrim.toggled.connect(lambda checked: self.set_trim(checked))
    self.buttonTrimSave.clicked.connect(self.save_from_trim_button)
    self.setup_trim_button_custom_handler()
    self.buttonNext.clicked.connect(self.handle_cycle_buttons)
    self.buttonPrevious.clicked.connect(lambda: self.handle_cycle_buttons(next=False))
    self.buttonExploreMediaPath.clicked.connect(self.actionExploreMediaPath.trigger)
    self.buttonMarkDeleted.clicked.connect(self.actionMarkDeleted.trigger)
    self.buttonSnapshot.clicked.connect(self.handle_snapshot_button)
    self.buttonLoop.clicked.connect(self.actionLoop.trigger)
    self.buttonAutoplay.clicked.connect(self.actionAutoplay.trigger)

    self.trim_mode_action_group = QtW.QActionGroup(self.menuTrimMode)
    self.trim_mode_action_group.addAction(self.actionTrimAuto)
    self.trim_mode_action_group.addAction(self.actionTrimPrecise)
    self.trim_mode_action_group.addAction(self.actionFadeBoth)
    self.trim_mode_action_group.addAction(self.actionFadeVideo)
    self.trim_mode_action_group.addAction(self.actionFadeAudio)
    self.trim_mode_action_group.triggered.connect(self.set_trim_mode)

    self.autoplay_direction_group = QtW.QActionGroup(self)
    self.autoplay_direction_group.addAction(self.actionAutoplayDirectionForwards)
    self.autoplay_direction_group.addAction(self.actionAutoplayDirectionBackwards)
    self.autoplay_direction_group.addAction(self.actionAutoplayDirectionDynamic)
    self.autoplay_direction_group.triggered.connect(self.refresh_autoplay_button)

    settings = self.dialog_settings
    settings.accepted.connect(self._refresh_title_slot)
    settings.comboThemes.currentTextChanged.connect(self.set_theme)
    settings.buttonRefreshThemes.clicked.connect(self.refresh_theme_combo)
    settings.buttonBrowseDefaultOutputPath.clicked.connect(lambda: self.browse_for_directory(lineEdit=settings.lineDefaultOutputPath, noun='default output'))
    settings.checkHighPrecisionProgress.toggled.connect(lambda: setattr(self.player, 'swap_slider_styles', True))
    settings.checkRecycleBin.toggled.connect(self.refresh_recycle_tooltip)      # ^ TODO: lol
    settings.checkFocusOnEdit.toggled.connect(lambda state: settings.checkFocusIgnoreFullscreenEditsOnly.setEnabled(state and settings.checkFocusIgnoreFullscreen.isChecked()))
    settings.checkFocusIgnoreFullscreen.toggled.connect(lambda state: settings.checkFocusIgnoreFullscreenEditsOnly.setEnabled(state and settings.checkFocusOnEdit.isChecked()))
    settings.checkScaleFiltering.toggled.connect(self.gifPlayer.update)
    settings.checkShowCoverArt.toggled.connect(self.refresh_cover_art)
    settings.checkTaskbarControls.toggled.connect(self.enable_taskbar_controls)
    settings.buttonHoverFontColor.clicked.connect(lambda: setattr(self.sliderProgress, 'hover_font_color', self.show_color_picker(button=settings.buttonHoverFontColor)))
    settings.checkZoomPrecise.toggled.connect(self.gifPlayer._updatePreciseZoom)
    settings.spinZoomMinimumFactor.valueChanged.connect(lambda v: settings.checkZoomAutoDisable1x.setEnabled(v == 1))
    settings.spinZoomMinimumFactor.valueChanged.connect(self.refresh_confusing_zoom_setting_tooltip)
    settings.spinZoomSmoothFactor.valueChanged.connect(self.gifPlayer._updateSmoothZoomFactor)
    settings.buttonBrowseDefaultSnapshotPath.clicked.connect(lambda: self.browse_for_directory(lineEdit=settings.lineDefaultSnapshotPath, noun='default snapshot'))
    settings.comboSnapshotDefault.currentIndexChanged.connect(self.refresh_snapshot_button_controls)
    settings.comboSnapshotShift.currentIndexChanged.connect(self.refresh_snapshot_button_controls)
    settings.comboSnapshotCtrl.currentIndexChanged.connect(self.refresh_snapshot_button_controls)
    settings.comboSnapshotAlt.currentIndexChanged.connect(self.refresh_snapshot_button_controls)
    settings.buttonCheckForUpdates.clicked.connect(self.handle_updates)

    self.position_button_group = QtW.QButtonGroup(settings)
    for button in (settings.radioTextPosition1, settings.radioTextPosition2, settings.radioTextPosition3,
                   settings.radioTextPosition4, settings.radioTextPosition5, settings.radioTextPosition6,
                   settings.radioTextPosition7, settings.radioTextPosition8, settings.radioTextPosition9):
        self.position_button_group.addButton(button)
    self.position_button_group.buttonToggled.connect(self.player.set_text_position)

    settings.spinTextHeight.valueChanged.connect(lambda value: self.player.set_text_height(value))
    settings.spinTextX.valueChanged.connect(lambda value: self.player.set_text_x(value))
    settings.spinTextY.valueChanged.connect(lambda value: self.player.set_text_y(value))
    settings.spinTextOpacity.valueChanged.connect(lambda value: self.player.set_text_max_opacity(value))
    settings.comboScaleImages.currentIndexChanged.connect(self.gifPlayer._updateImageScale)
    settings.comboScaleArt.currentIndexChanged.connect(self.gifPlayer._updateArtScale)
    settings.comboScaleGifs.currentIndexChanged.connect(self.gifPlayer._updateGifScale)

    def refresh_navigation_labels():
        for label, spinbox in (
            (settings.labelNavigation1, settings.spinNavigation1),
            (settings.labelNavigation2, settings.spinNavigation2),
            (settings.labelNavigation3, settings.spinNavigation3),
            (settings.labelNavigation4, settings.spinNavigation4),
        ):
            seconds = spinbox.value()
            suffix = ' second' if seconds == 1 else ' seconds'
            label.setText(f'-{seconds}{suffix}')
            spinbox.setSuffix(suffix)

    settings.spinNavigation1.valueChanged.connect(refresh_navigation_labels)
    settings.spinNavigation2.valueChanged.connect(refresh_navigation_labels)
    settings.spinNavigation3.valueChanged.connect(refresh_navigation_labels)
    settings.spinNavigation4.valueChanged.connect(refresh_navigation_labels)
    settings.spinVolume1.valueChanged.connect(lambda v: settings.labelVolume1.setText(f'-{v} volume'))
    settings.spinVolume2.valueChanged.connect(lambda v: settings.labelVolume2.setText(f'-{v} volume'))

    # NOTE: this looks weird if the gif has custom frame-by-frame delays, but it's perfectly fine
    self.gifPlayer.gif.frameChanged.connect(self.update_gif_progress)
