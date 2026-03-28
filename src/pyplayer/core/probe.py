"""Media probing and utility functions for file inspection and metadata.

Extracted from main.pyw. Contains probe_files, get_audio_duration,
get_image_data, get_PIL_safe_path, splitext_media, and close_handle.
"""
from __future__ import annotations

import os
import json
import subprocess
import logging
from os.path import exists, sep
from time import sleep
from traceback import format_exc
from contextlib import contextmanager

from pyplayer import constants


# ---------------------------------------------------------------------------
# Runtime globals — set by the application entry point at startup.
# ---------------------------------------------------------------------------

def _make_placeholder(name: str):
    """Return a callable that raises ``RuntimeError`` when accessed."""
    def _raise(*args, **kwargs):
        raise RuntimeError(
            f'{name} has not been initialised. '
            f'Call pyplayer.core.probe.init_globals() from the application entry point.'
        )
    return _raise


# Module-level references populated at startup
show_on_statusbar = _make_placeholder('probe.show_on_statusbar')
log_on_statusbar = _make_placeholder('probe.log_on_statusbar')
parse_json = _make_placeholder('probe.parse_json')
FFPROBE = _make_placeholder('probe.FFPROBE')
image_player = _make_placeholder('probe.image_player')
get_PIL_Image = _make_placeholder('probe.get_PIL_Image')


def init_globals(
    show_on_statusbar_fn,
    log_on_statusbar_fn,
    parse_json_fn,
    ffprobe_path,
    image_player_obj,
    get_PIL_Image_fn,
):
    """Populate module-level globals needed by probe functions.

    This must be called once during application startup.
    """
    global show_on_statusbar, log_on_statusbar, parse_json
    global FFPROBE, image_player, get_PIL_Image
    show_on_statusbar = show_on_statusbar_fn
    log_on_statusbar = log_on_statusbar_fn
    parse_json = parse_json_fn
    FFPROBE = ffprobe_path
    image_player = image_player_obj
    get_PIL_Image = get_PIL_Image_fn


def probe_files(*files: str, refresh: bool = False, write: bool = True, retries: int = 0) -> dict[str, dict]:
    ''' Probes an indeterminant number of `files` and returns a dictionary of
        `{path: probe_dictionary}` pairs. All files are probed concurrently, but
        this function does not return until all probes are completed. Files that
        fail are simply not included.

        This function is similar to the probing process in `self.open()`
        (but is not used there for performance reasons) - by default, it will
        create/validate/reuse probe files. However, if `refresh` is True, a new
        probe will always be generated even if the probe file already exists.
        If `write` is False, any new probes will not be written to a file. '''

    try:
        logging.info(f'Manually probing files: {files} (refresh={refresh})')
        probes: dict[str, dict] = {}
        processes: list[tuple[str, str, subprocess.Popen]] = []

        is_windows = constants.IS_WINDOWS
        if not is_windows:
            import shlex                                # have to pass commands as list for linux/macos (stupid)
            cmd_parts = shlex.split(f'"{FFPROBE}" -show_format -show_streams -of json "output"')

        # begin probe-process for each file and immediately jump to the next file
        for file in files:
            if file in probes or not exists(file):
                continue

            stat = os.stat(file)
            probe_file = f'{constants.PROBE_DIR}{sep}{os.path.basename(file)}_{stat.st_mtime}_{stat.st_size}.txt'
            probe_exists = exists(probe_file)
            if probe_exists:
                if refresh:                             # NOTE: if `refresh` is True and `write` is False, existing...
                    try: os.remove(probe_file)          # ...probe files will be deleted without being replaced
                    except: logging.warning('(!) FAILED TO DELETE UNWANTED PROBE FILE: ' + format_exc())
                    probe_exists = False
                else:
                    with open(probe_file, 'r', encoding='utf-8') as probe:
                        try:
                            probe_data = parse_json(probe.read())
                            if not probe_data:
                                raise AssertionError('probe returned no data')
                            probes[file] = probe_data
                        except:
                            probe.close()
                            logging.info('(?) Deleting potentially invalid probe file: ' + probe_file)
                            try: os.remove(probe_file)
                            except: logging.warning('(!) FAILED TO DELETE POTENTIALLY INVALID PROBE FILE: ' + format_exc())
                            probe_exists = False

            if not probe_exists:
                if is_windows:
                    cmd = f'"{FFPROBE}" -show_format -show_streams -of json "{file}"'
                else:                                   # ^ do NOT use ">" here since we need to read stdout
                    cmd = cmd_parts[:]                  # copy list and replace final element with our destination
                    cmd[-1] = file                      # do NOT put quotes around this
                processes.append(
                    (
                        file,
                        probe_file,
                        subprocess.Popen(
                            cmd,
                            text=True,                  # decodes stdout into text rather than a byte stream
                            encoding='utf-8',           # use ffmpeg/ffprobe's encoding so `text=True` doesn't crash for paths w/ scary characters
                            errors='ignore',            # drop bad characters when there's an encoding error (which won't matter for our usecase)
                            stdout=subprocess.PIPE,     # don't use `shell=True` for the same reason as above
                            startupinfo=constants.STARTUPINFO
                        )                               # ^ hides the command prompt that appears w/o `shell=True`
                    )
                )

        # for any files that did not have pre-existing probe files, wait until...
        # ...their processes are complete and read output directly from the process
        for file, probe_file, process in processes:
            try:
                out, err = process.communicate()        # NOTE: this is where errors happen on filenames with the wrong encoding above
                probe_data = parse_json(out)
                if not probe_data:
                    raise AssertionError('probe returned no data')
                probes[file] = probe_data
                if write:                               # manually write probe to file
                    with open(probe_file, 'w', encoding='utf-8') as probe:
                        probe.write(out)                    # ^ DON'T use `errors='ignore'` here. if we somehow error out here, i'd rather know why
            except:
                logging.warning(f'(!) {file} could not be correctly parsed by FFprobe: {format_exc()}')
                show_on_statusbar(f'{file} could not be correctly parsed by FFprobe.')
        return probes

    # if we're low on RAM, wait one second and try again
    except OSError:                                     # "[WinError 1455] The paging file is too small for this operation to complete"
        logging.warning(f'(!) OSError while probing files: {format_exc()}')
        if retries:
            show_on_statusbar('(!) Not enough RAM to probe files. Trying again...')
            sleep(1)
            return probe_files(*files, refresh, write, retries - 1)
        else:
            show_on_statusbar('(!) Not enough RAM to probe files. Giving up.')
            return {}


def get_audio_duration(file: str) -> float:
    ''' Lightweight way of getting the duration of an audio `file`.
        Used for instances where we need ONLY the duration. '''
    try:
        try:                                            # https://pypi.org/project/tinytag/0.18.0/
            from tinytag import TinyTag
            return TinyTag.get(file, tags=False).duration
        except:                                         # TinyTag is lightweight but cannot handle everything
            import music_tag                            # only import music_tag if we absolutely need to
            return music_tag.load_file(file)['#length'].value
    except:                                             # this is to handle things that wrongly report as audio, like .ogv files
        log_on_statusbar('(?) File could not be read as an audio file (not recognized by TinyTag or music_tag)')
        return 0.0


@contextmanager
def get_image_data(path: str, extension: str = None):
    # TODO I don't need this anymore and should probably avoid using it at all.
    try:
        if exists(path): image_data = get_PIL_Image().open(path, formats=(extension,) if extension else None)
        else:            image_data = get_PIL_Image().fromqpixmap(image_player.art)
        yield image_data
    finally:
        try: image_data.close()
        except: logging.warning('(?) Image pointer could not be closed (it likely was never open in the first place).')


@contextmanager
def get_PIL_safe_path(original_path: str, final_path: str):
    # TODO Like the above, this is a holdover from when I was reworking
    #      operation ordering/chaining for 0.6.0 and is not actually needed
    #      anymore, save for one spot where I was too lazy to implement Pillow.
    try:
        temp_path = ''
        if splitext_media(final_path, constants.IMAGE_EXTENSIONS)[-1] == '':
            good_ext = splitext_media(original_path, constants.IMAGE_EXTENSIONS)[-1]
            if good_ext == '':
                good_ext = '.png'
            temp_path = final_path + good_ext
            yield temp_path
        else:
            yield final_path
    finally:
        if temp_path != '':
            try: os.replace(temp_path, final_path)
            except: logging.warning('(!) FAILED TO RENAME TEMPORARY IMAGE PATH' + format_exc())


def splitext_media(
    path: str,
    valid_extensions: tuple[str] = constants.ALL_MEDIA_EXTENSIONS,
    invalid_extensions: tuple[str] = constants.ALL_MEDIA_EXTENSIONS,
    *,
    strict: bool = True,
    period: bool = True
) -> tuple[str, str]:
    ''' Split the extension from a `path` if the extension is within a
        list of `valid_extensions`. If not, the basename is returned with an
        empty extension. The extension will be lowercase. If `period` is True,
        the preceding period will be included (i.e. ".mp4"). If `strict` is
        False, an unknown extension can still be returned intact if:

        1. It is not within a list of `invalid_extensions`
        2. It is 6 characters or shorter
        3. It contains at least one letter
        4. It does not contain anything other than letters and numbers

        NOTE: `strict` must be provided as a keyword argument.

        NOTE: `valid_extensions` is evaluated first. `invalid_extensions` should
        rarely be changed, but may be passed as None/False/"" if desired. '''

    base, ext = os.path.splitext(path)
    ext = ext.lower()

    # if no ext to begin with, return immediately
    if not ext:
        return path, ''

    # if `strict` is False and ext is invalid, only return if ext is >6 characters
    if ext not in valid_extensions:
        if strict or len(ext) > 6 or ext in (invalid_extensions or tuple()):
            return base, ''

        # verify ext has at least one letter and no symbols
        has_letters = False
        for c in ext[1:]:
            if c.isalpha():
                has_letters = True
            elif not c.isdigit():
                return base, ''
        if not has_letters:
            return base, ''

    # return extension with or without preceding period (".mp4" vs "mp4")
    if period:
        return base, ext
    return base, ext[1:]


def close_handle(handle, delete: bool):                 # i know they're not really handles but whatever
    ''' Closes a file-object `handle` and attempts
        to `delete` its associated path. '''
    handle.close()
    if delete and exists(handle.name):
        try: os.remove(handle.name)
        except: logging.warning(f'(!) Failed to delete dummy file at final destination ({handle.name}): {format_exc()}')
