''' Runtime hook that takes the place of launcher.pyw. Runtime hooks run before
    the actual script runs. Communicates with active PyPlayer instances through
    their PID files, typically by sending the most recently opened instance a
    file that the user wants to open and then exiting the current instance, so
    as to skip re-opening PyPlayer. Also cleans temp folder and uses sys.path
    magic to hide our .dll, .pyd, and libvlc files in alternate directories.

    Updated for PyInstaller 6.x compatibility (_internal folder structure).

    thisismy-github -> launcher.pyw: 2/1/22, hook.py: 4/8/22, combined: 4/13/22
    PyInstaller 6.x update: 2025-03-25 '''

import sys
import os


# ============================================================
# Path Detection - Compatible with PyInstaller 5.x and 6.x
# ============================================================
IS_FROZEN = getattr(sys, 'frozen', False)

if IS_FROZEN:
    # PyInstaller 6.x uses _internal folder
    # sys._MEIPASS points to the internal directory
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 6.x: sys._MEIPASS = .../release/_internal
        INTERNAL_DIR = sys._MEIPASS
        # CWD is the directory containing the exe
        CWD = os.path.dirname(sys.executable)
    else:
        # PyInstaller 5.x or older
        CWD = os.path.dirname(sys.argv[0])
        INTERNAL_DIR = CWD
else:
    # Development mode
    CWD = os.path.dirname(os.path.abspath(__file__))
    INTERNAL_DIR = CWD

# Determine temp directory location
if IS_FROZEN:
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 6.x: temp inside _internal
        TEMP_DIR = os.path.join(INTERNAL_DIR, 'temp')
    else:
        # PyInstaller 5.x: temp in PyQt5 or bin folder
        TEMP_DIR = os.path.join(CWD, 'PyQt5', 'temp')
else:
    # Development mode
    TEMP_DIR = os.path.join(CWD, 'bin', 'temp')

IS_WINDOWS = sys.platform in ('win32', 'cygwin', 'msys')


''' If an argument is specified, check for running instances. If one is found,
    encode the argument within a text file named after the PID of the latest
    instance, then signal to our current instance that it should exit. '''
try:
    filepath = sys.argv[1]
    # Create temp directory if it doesn't exist
    os.makedirs(TEMP_DIR, exist_ok=True)

    pids = (os.path.join(TEMP_DIR, file) for file in os.listdir(TEMP_DIR) if file[-4:] == '.pid')   # get all .pid files
    for file in reversed(sorted(pids, key=os.path.getctime)):   # sort by age, then reverse (newest first)
        try:    # check if PID file is valid
            pid = os.path.basename(file)[:-4]
            if not IS_WINDOWS:
                os.kill(int(pid), 0)                # Linux/Mac, sending signal-0 to non-existent PID = ProcessLookupError
                raise PermissionError               # no error -> PID file is valid -> manually raise PermissionError
            os.remove(file)                         # Windows, removing a valid PID file = PermissionError
        except ValueError: os.remove(file)          # ValueError means a PID file had letters in it (likely user-created)
        except PermissionError:                     # PermissionError means pid file in use -> send path to its instance
            cmdpath = os.path.join(TEMP_DIR, f'cmd.{pid}.txt')
            with open(cmdpath, 'wb') as txt: txt.write(filepath.encode())
            sys.argv.append('--exit')               # add --exit argument so our instance exits

            # if cmd-file sent, clean excess files in temp folder (if any) while user waits for pre-existing instance
            import time
            now = time.time()
            max_age = 30                            # NOTE: Values < 15 seconds causes unusual behavior on Windows
            for file in os.listdir(TEMP_DIR):
                file = os.path.join(TEMP_DIR, file)
                if not os.path.isfile(file): continue
                stat = os.stat(file)
                if now > stat.st_atime + max_age:   # check if file is > max_age seconds old using "last accessed" time
                    try: os.remove(file)            # delete outdated file
                    except: pass
            break                                   # break out of pid-loop
        except OSError:                             # handle AFTER PermissionError (it's a type of OSError)
            if not IS_WINDOWS:                      # on Linux/Mac, this is likely a ProcessLookupError -> remove PID file
                os.remove(file)
except (IndexError, FileNotFoundError): pass        # no file specified, or temp folder doesn't exist
except:                                             # unexpected serious error -> setup logging and log error
    import logging
    from traceback import format_exc
    logging.basicConfig(filename=os.path.join(CWD, 'LAUNCHER_ERROR.log'),
                        filemode='a', datefmt='%m/%d/%y | %I:%M:%S%p', style='{',
                        format='{asctime} {lineno:<3} {levelname} {funcName}: {message}')
    message = '(!) Unexpected error while launching -'
    logging.error(f'{message} {format_exc()}')


##############################################################################
''' Add PyQt5 to sys.path and create VLC environment variables (if needed)
    so we can hide our .dll, .pyd, and libvlc files in alternate folders. '''

# PyQt5 path handling for PyInstaller 6.x
if IS_FROZEN and hasattr(sys, '_MEIPASS'):
    # PyInstaller 6.x: PyQt5 is in _internal, already in sys.path
    pass
else:
    # PyInstaller 5.x or development mode
    sys.path.append(os.path.join(CWD, 'PyQt5'))

# VLC path handling - compatible with both PyInstaller versions
if IS_FROZEN and hasattr(sys, '_MEIPASS'):
    # PyInstaller 6.x structure:
    # _internal/libvlccore.dll (may exist at root level)
    # _internal/plugins/vlc/libvlc.dll
    # _internal/plugins/vlc/plugins/
    VLC_PATH = os.path.join(INTERNAL_DIR, 'plugins', 'vlc')
    LIB_PATH = os.path.join(VLC_PATH, 'libvlc.dll')
    MODULE_PATH = os.path.join(VLC_PATH, 'plugins')

    # Fallback: try root level if not in plugins/vlc
    if not os.path.exists(LIB_PATH):
        LIB_PATH = os.path.join(INTERNAL_DIR, 'libvlc.dll')
        VLC_PATH = INTERNAL_DIR
        MODULE_PATH = os.path.join(INTERNAL_DIR, 'plugins')
else:
    # PyInstaller 5.x or development mode
    VLC_PATH = os.path.join(CWD, 'plugins', 'vlc')
    LIB_PATH = os.path.join(VLC_PATH, 'libvlc.dll')
    MODULE_PATH = os.path.join(VLC_PATH, 'plugins')

# Set VLC environment variables if not already set
if 'PYTHON_VLC_LIB_PATH' not in os.environ and os.path.exists(LIB_PATH):
    os.environ['PYTHON_VLC_LIB_PATH'] = LIB_PATH
if 'PYTHON_VLC_MODULE_PATH' not in os.environ and os.path.exists(MODULE_PATH):
    os.environ['PYTHON_VLC_MODULE_PATH'] = MODULE_PATH
