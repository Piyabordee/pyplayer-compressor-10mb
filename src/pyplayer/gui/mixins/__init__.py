"""PyPlayer GUI mixins.

This package contains mixin classes that provide functionality for the main window.
Each mixin groups related methods together for better code organization.

Mixins:
    PlaybackMixin: Playback controls — volume, tracks, rate, navigation
    EditingMixin: Editing operations — trim, crop, edit priority, compression
    SavingMixin: Saving operations — save, save_as, concatenate, resize, audio operations
    FileManagementMixin: File management — open, close, cycle, copy, rename, delete, snapshot
    MenuMixin: Menu and context menu handling
    ThemeMixin: Theme management
    EventMixin: Qt event handlers
    DialogMixin: Dialog helpers and popup windows
    UIStateMixin: UI state management
"""

from .playback import PlaybackMixin
from .editing import EditingMixin
from .saving import SavingMixin
from .file_management import FileManagementMixin
from .menus import MenuMixin
from .themes import ThemeMixin
from .events import EventMixin
from .dialogs import DialogMixin
from .ui_state import UIStateMixin

__all__ = [
    'PlaybackMixin',
    'EditingMixin',
    'SavingMixin',
    'FileManagementMixin',
    'MenuMixin',
    'ThemeMixin',
    'EventMixin',
    'DialogMixin',
    'UIStateMixin',
]
