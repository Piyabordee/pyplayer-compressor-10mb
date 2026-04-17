"""Root conftest — fixes import path so src/pyplayer/ takes priority over pyplayer.pyw."""
import sys
import os


def pytest_configure(config):
    """Runs before test collection — fix sys.path to prevent pyplayer.pyw shadowing."""
    root = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(root, 'src')

    # Remove CWD/root from sys.path to prevent pyplayer.pyw from being found
    sys.path = [p for p in sys.path if p not in ('', root)]

    # Ensure src/ is at the front
    if src not in sys.path:
        sys.path.insert(0, src)

    # Clear any cached pyplayer module from the wrong source
    if 'pyplayer' in sys.modules:
        mod = sys.modules['pyplayer']
        if not hasattr(mod, '__path__'):
            del sys.modules['pyplayer']
