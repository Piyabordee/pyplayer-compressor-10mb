"""Keyboard shortcuts setup.

Extracted from qtstart.py connect_shortcuts().
"""
from __future__ import annotations

from PyQt5 import QtWidgets as QtW

from pyplayer import qthelpers


def connect_shortcuts(self: QtW.QMainWindow):
    """Connect keyboard shortcuts to their actions."""
    # TODO add standardShortcuts | TODO are these noticably slower than using keyPressEvent or am I crazy?
    def toggle_loop():
        self.marquee(f'Looping {"disabled" if self.actionLoop.isChecked() else "enabled"}', marq_key='Loop', log=False),
        self.actionLoop.trigger()

    settings = self.dialog_settings
    shortcut_actions = {      # NOTE: having empty rows in tabHotkeys's formLayout causes actions below empty rows to not work
        'pause':              self.pause,
        'stop':               self.stop,
        'plus1':              lambda: self.navigate(forward=True,  seconds_spinbox=settings.spinNavigation1),
        'minus1':             lambda: self.navigate(forward=False, seconds_spinbox=settings.spinNavigation1),
        'plus2':              lambda: self.navigate(forward=True,  seconds_spinbox=settings.spinNavigation2),
        'minus2':             lambda: self.navigate(forward=False, seconds_spinbox=settings.spinNavigation2),
        'plus3':              lambda: self.navigate(forward=True,  seconds_spinbox=settings.spinNavigation3),
        'minus3':             lambda: self.navigate(forward=False, seconds_spinbox=settings.spinNavigation3),
        'plus4':              lambda: self.navigate(forward=True,  seconds_spinbox=settings.spinNavigation4),
        'minus4':             lambda: self.navigate(forward=False, seconds_spinbox=settings.spinNavigation4),
        'plusframe':          self.spinFrame.stepUp,
        'minusframe':         self.spinFrame.stepDown,
        'plusspeed':          lambda: self.set_playback_rate(0.05, increment=True),
        'minusspeed':         lambda: self.set_playback_rate(-0.05, increment=True),
        'plusvolume1':        lambda: self.sliderVolume.setValue(self.sliderVolume.value() + settings.spinVolume1.value()),
        'minusvolume1':       lambda: self.sliderVolume.setValue(self.sliderVolume.value() - settings.spinVolume1.value()),
        'plusvolume2':        lambda: self.sliderVolume.setValue(self.sliderVolume.value() + settings.spinVolume2.value()),
        'minusvolume2':       lambda: self.sliderVolume.setValue(self.sliderVolume.value() - settings.spinVolume2.value()),
        'plusvolumeboost':    lambda: self.set_volume_boost(0.5, increment=True),
        'minusvolumeboost':   lambda: self.set_volume_boost(-0.5, increment=True),
        'mute':               self.toggle_mute,
        'fullscreen':         self.actionFullscreen.trigger,
        'maximize':           self.toggle_maximized,
        'crop':               self.actionCrop.trigger,
        'loop':               toggle_loop,
        'nextmedia':          self.cycle_media,
        'nextmediamime':      lambda: self.cycle_media(valid_mime_types=(self.mime_type,)),
        'previousmedia':      lambda: self.cycle_media(next=False),
        'previousmediamime':  lambda: self.cycle_media(next=False, valid_mime_types=(self.mime_type,)),
        'randommedia':        self.shuffle_media,
        'randommediamime':    lambda: self.shuffle_media(valid_mime_types=(self.mime_type,)),
        'forward':            lambda: self.cycle_recent_files(forward=True),
        'back':               lambda: self.cycle_recent_files(forward=False),
        'plussubtitledelay':  lambda: self.set_subtitle_delay(50, increment=True),
        'minussubtitledelay': lambda: self.set_subtitle_delay(-50, increment=True),
        'plusaudiodelay':     lambda: self.set_audio_delay(50, increment=True),
        'minusaudiodelay':    lambda: self.set_audio_delay(-50, increment=True),
        'cyclesubtitles':     lambda: self.cycle_track('subtitle'),
        'cycleaudio':         lambda: self.cycle_track('audio'),
        'cyclevideo':         lambda: self.cycle_track('video'),
        'snapshot':           lambda: self.snapshot(mode='full'),
        'quicksnapshot':      self.snapshot,
        'properties':         lambda: self.open_properties(self.video),
    }
    self.shortcuts = {action_name: (QtW.QShortcut(self, context=3), QtW.QShortcut(self, context=3)) for action_name in shortcut_actions}
    #self.shortcuts = {action_name: (Qtself.QKeySequence(), Qtself.QKeySequence()) for action_name in shortcut_actions}

    get_refresh_shortcuts_lambda = lambda widget: lambda: self.refresh_shortcuts(widget)        # lambda-in-iterable workaround
    for layout in qthelpers.formGetItemsInColumn(self.dialog_settings.formKeys, 1):
        for keySequenceEdit in qthelpers.layoutGetItems(layout):
            name = keySequenceEdit.objectName()
            index = 0 if name[-1] != '_' else 1
            name = name.rstrip('_')
            self.shortcuts[name][index].activated.connect(shortcut_actions[name])
            keySequenceEdit.editingFinished.connect(get_refresh_shortcuts_lambda(keySequenceEdit))
