"""Custom Qt widgets for PyPlayer — re-exports all public classes."""
from pyplayer.widgets.player_backend import PyPlayerBackend, PlayerVLC, PlayerQt
from pyplayer.widgets.player_widget import QVideoPlayer
from pyplayer.widgets.player_label import QVideoPlayerLabel
from pyplayer.widgets.video_slider import QVideoSlider
from pyplayer.widgets.video_list import QVideoListItemWidget, QVideoList
from pyplayer.widgets.overlays import QTextOverlayPreview, QTextOverlay, QColorPickerButton
from pyplayer.widgets.inputs import (
    QKeySequenceFlexibleEdit,
    QWidgetPassthrough,
    QDockWidgetPassthrough,
    QLineEditPassthrough,
    QSpinBoxPassthrough,
    QSpinBoxInputSignals,
)
from pyplayer.widgets.draggable import QDraggableWindowFrame
from pyplayer.widgets.helpers import (
    gui, app, cfg, settings,
    set_aliases,
    ZOOM_DYNAMIC_FIT, ZOOM_NO_SCALING, ZOOM_FIT, ZOOM_FILL,
)

__all__ = [
    'PyPlayerBackend', 'PlayerVLC', 'PlayerQt',
    'QVideoPlayer', 'QVideoPlayerLabel', 'QVideoSlider',
    'QVideoListItemWidget', 'QVideoList',
    'QTextOverlayPreview', 'QTextOverlay', 'QColorPickerButton',
    'QKeySequenceFlexibleEdit',
    'QWidgetPassthrough', 'QDockWidgetPassthrough',
    'QLineEditPassthrough', 'QSpinBoxPassthrough', 'QSpinBoxInputSignals',
    'QDraggableWindowFrame',
]
