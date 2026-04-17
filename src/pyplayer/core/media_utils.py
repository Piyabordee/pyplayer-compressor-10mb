"""Media processing utilities and helper functions."""
from __future__ import annotations

import os
import sys
import logging
from traceback import format_exc

from pyplayer import constants

logger = logging.getLogger('pyplayer.core.media_utils')


def get_hms(seconds: float) -> tuple[int, int, int, int]:
    ''' Converts `seconds` to the hours, minutes,
        seconds, and milliseconds it represents. '''
    h_remainder = seconds % 3600
    h = int(seconds // 3600)
    m = int(h_remainder // 60)
    s = int(h_remainder % 60)
    ms = int(round((seconds - int(seconds)) * 100, 4))  # round to account for floating point imprecision
    return h, m, s, ms


def get_PIL_Image():
    ''' An over-the-top way of hiding PIL's folder. The PIL folder cannot be
        avoided due to the required from-import, and conventional means of
        hiding it do not seem to work, so instead we hide the folder at first,
        then move (NOT copy) it to the root folder so we can import PIL, then
        immediately move the folder back. All this, just to have one less item
        in the root folder. Honestly worth it. '''

    try:    # prepare PIL for importing if it hasn't been imported yet (once imported, it's imported for good)
        PIL_already_imported = 'PIL.Image' in sys.modules
        if not PIL_already_imported and constants.IS_COMPILED:
            logger.info('Importing PIL for the first time...')
            files_moved = []

            # identify new PIL path and check if it already exists
            new_path = f'{constants.CWD}{os.sep}PIL'
            new_path_already_existed = os.path.exists(new_path)
            new_path_renamed = False

            # identify expected PIL path and a backup for it, assert existence of at least one PIL path
            old_path = f'{constants.BIN_DIR}{os.sep}PIL'
            backup_path = old_path + '.bak'
            backup_path_already_existed = os.path.exists(backup_path)
            if backup_path_already_existed:     # backup already exists (likely from error in previous session)
                logger.warning(f'PIL backup path {backup_path} already exists, using it...')
                old_path, backup_path = backup_path, old_path   # swap backup and old paths
            assert os.path.exists(old_path) or new_path_already_existed, 'PIL folder not found at ' + old_path

            # backup old PIL path and create new PIL path. if it already exists (for some reason), rename it temporarily
            if os.path.exists(old_path):        # if old PIL path doesn't exist, just hope the new PIL path is correct
                import shutil
                shutil.copytree(old_path, backup_path)
                if new_path_already_existed:
                    try:
                        from pyplayer.core.file_ops import get_unique_path
                        new_path_temp_name = get_unique_path(new_path + '_temp')
                        os.rename(new_path, new_path_temp_name)
                        new_path_renamed = True
                    except:
                        logger.warning(f'Could not rename {new_path} to {new_path}_temp: {format_exc()}')
                try: os.makedirs(new_path)
                except: logger.warning(f'Could not make {new_path}: {format_exc()}')

            # move (NOT copy) each file from the normal PIL path to the new PIL path and append each move to files_moved
            for file in os.listdir(old_path):
                if file[-4:] != '.pyd': continue
                old_file = f'{old_path}{os.sep}{file}'
                new_file = f'{new_path}{os.sep}{file}'
                os.rename(old_file, new_file)
                files_moved.append((old_file, new_file))

        from PIL import Image                   # actually import PIL.Image (this is what hangs in the script)

        # return files to their original spots, delete/restore new PIL path, and return PIL.Image
        if not PIL_already_imported and constants.IS_COMPILED:
            import shutil
            for source, dest in files_moved:
                try: os.rename(dest, source)
                except: logger.warning(f'Could not move {dest} to {source}: {format_exc()}')
            if not (new_path_already_existed and not new_path_renamed):
                try: shutil.rmtree(new_path)
                except: logger.warning(f'Could not delete {new_path}: {format_exc()}')
            if new_path_renamed:            os.rename(new_path_temp_name, new_path)
            if os.path.exists(backup_path): shutil.rmtree(backup_path)
            if backup_path_already_existed: os.rename(old_path, backup_path)
            logger.info('First-time PIL import successful.')
        return Image                            # return PIL.Image
    except:
        logger.error(f'(!) PIL IMPORT FAILED: {format_exc()}')
        try:        # in the event of an error, attempt to restore backup if one exists
            if os.path.exists(backup_path):
                import shutil
                shutil.rmtree(old_path)
                os.rename(backup_path, old_path)
            elif not os.path.exists(old_path) and not os.path.exists(new_path):
                raise Exception('None of the following candidates for a PIL folder were found:'
                                f'\nOld: {old_path}\nNew: {new_path}\nBackup: {backup_path}')
        except NameError:                       # NameError -> error occurred before the paths were even defined
            pass
        except:     # PIL is seemingly unrecoverable. hopefully this is extremely unlikely outside of user-tampering
            logger.critical(f'(!!!) COULD NOT RESTORE PIL FOLDER: {format_exc()}')
            logger.critical('\n\n  WARNING -- You may need to reinstall PyPlayer to restore snapshotting capabilities.'
                            '\n             If you cannot find the PIL folder within your installation, please report '
                            '\n             this error (along with this log file) on Github.\n')


def get_ratio_string(width: int, height: int) -> str:
    ''' Calculates the ratio between two numbers.
        https://gist.github.com/Integralist/4ca9ff94ea82b0e407f540540f1d8c6c '''
    if width == 0:
        return '0:0'
    gcd = lambda w, h: w if h == 0 else gcd(h, w % h)   # GCD is the highest number that evenly divides both W and H
    r = gcd(width, height)
    return f'{int(width / r)}:{int(height / r)}'


def get_verbose_timestamp(seconds: float) -> str:
    ''' - Example: "3 hours, 12 minutes, and 57 seconds"
        - Example: "15 minutes, 1 second"
        - Example: "5.3 seconds" '''
    if seconds < 10.0:
        seconds = round(seconds, 1)
        int_seconds = int(seconds)
        if seconds == int_seconds:
            return f'{int_seconds} second{"s" if int_seconds != 1 else ""}'
        return f'{seconds:.1f} second{"s" if seconds != 1 else ""}'
    else:
        h, m, s, _ = get_hms(seconds)
        deltaFormat = []
        if h: deltaFormat.append(f'{h} hour{"s" if h > 1 else ""}')
        if m: deltaFormat.append(f'{m} minute{"s" if m > 1 else ""}')
        if s: deltaFormat.append(f'{s} second{"s" if s > 1 else ""}')
        if len(deltaFormat) == 3: deltaFormat.insert(-1, 'and')
        return ', '.join(deltaFormat).replace('and,', 'and')


def remove_dict_value(dictionary: dict, value):
    ''' Safely removes `value` from `dictionary`.
        Returns as soon as `value` is found. '''
    to_remove = None
    for key, other_value in dictionary.items():
        if other_value is value:
            to_remove = key
            break

    try: del dictionary[to_remove]
    except: pass


def remove_dict_values(dictionary: dict, *values):
    ''' Safely removes all `values` from `dictionary`. Casts `values` to a set,
        loops over the dictionary exactly once, and does not return early. '''
    value_set = set(values)
    to_remove = [key for key, value in dictionary.items() if value in value_set]
    for key in to_remove:
        try: del dictionary[key]
        except: pass


def scale(x: float, y: float, new_x: float = -1, new_y: float = -1) -> tuple[int | float, int | float]:
    ''' Returns (`x`, `y`) scaled to either `new_x` or `new_y`, if
        either is >=0. If both are provided, `new_y` is ignored. '''
    if new_x <= 0:   new_x = round((float(new_y) / y) * x)
    elif new_y <= 0: new_y = round((float(new_x) / x) * y)
    return new_x, new_y
