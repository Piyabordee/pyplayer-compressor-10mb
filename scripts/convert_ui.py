"""Converts all .ui files to .py files using pyuic5.
Run after editing .ui files in ui_sources/."""
import os
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
UI_DIR = os.path.join(ROOT, 'ui_sources')
OUT_DIR = os.path.join(ROOT, 'src', 'pyplayer', 'ui')

for ui_file in glob.glob(os.path.join(UI_DIR, '*.ui')):
    basename = os.path.basename(ui_file)
    py_file = os.path.join(OUT_DIR, basename.replace('.ui', '.py'))
    os.system(f'pyuic5 -x "{ui_file}" -o "{py_file}"')
    print(f'Converted: {basename} -> src/pyplayer/ui/{basename.replace(".ui", ".py")}')
