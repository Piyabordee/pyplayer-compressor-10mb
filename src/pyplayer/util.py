"""Backward-compatibility shim — re-exports from core modules.

The original util.py was split into:
  - pyplayer.core.file_ops
  - pyplayer.core.ffmpeg
  - pyplayer.core.media_utils

This module re-unifies them under the `pyplayer.util` namespace so that
code using `self.util.xxx()` continues to work during the migration.
"""
from pyplayer.core.file_ops import *        # noqa: F401,F403
from pyplayer.core.ffmpeg import *           # noqa: F401,F403
from pyplayer.core.media_utils import *      # noqa: F401,F403

# Re-export specific names that may not be covered by __all__
from pyplayer.core.file_ops import (         # noqa: F401
    add_path_suffix, get_from_PATH, get_unique_path,
    open_properties, sanitize, setctime,
)
from pyplayer.core.ffmpeg import (           # noqa: F401
    ffmpeg, ffmpeg_async, suspend_process, kill_process,
)
from pyplayer.core.media_utils import (      # noqa: F401
    get_hms, get_PIL_Image, get_ratio_string, get_verbose_timestamp,
    remove_dict_value, remove_dict_values, scale,
)
