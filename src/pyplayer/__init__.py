"""PyPlayer — A powerful video player and editor built on VLC and PyQt5."""

__version__ = '0.6.0'
__author__ = 'thisismy-github'

# Import modules that need to be accessible from the pyplayer namespace
# These are imported from parent directory for backward compatibility during migration
import sys
import os

# Add parent of src to path to import root-level modules during migration
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)


def __getattr__(name: str):
    """Lazy import root-level modules for backward compatibility.

    This avoids import-time VLC initialization errors when the package is imported.
    The actual modules are imported when first accessed.
    """
    import importlib

    module_map = {
        'qthelpers': ('qthelpers', None),
        'util': ('util', None),
        'widgets': ('widgets', None),
        'qtstart': ('qtstart', None),
        'constants': ('constants', None),
        'config': ('config', None),
    }

    if name in module_map:
        module_name, _ = module_map[name]
        module = importlib.import_module(module_name)
        # Cache the imported module
        globals()[name] = module
        return module

    raise AttributeError(f"module 'pyplayer' has no attribute '{name}'")
