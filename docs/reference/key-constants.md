# Key Constants

> Important global constants defined in `src/pyplayer/constants.py`.

---

## Application Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `VERSION` | `'pyplayer 0.6.0 beta'` | Application version string |
| `REPOSITORY_URL` | `'https://github.com/Piyabordee/pyplayer-compressor-10mb'` | Repo URL for update checks |
| `IS_COMPILED` | `getattr(sys, 'frozen', False)` | Detects if running as PyInstaller exe |

## Path Constants

| Constant | Location | Purpose |
|----------|----------|---------|
| `CONFIG_PATH` | `config.ini` in CWD | User settings file |
| `LOG_PATH` | `pyplayer.log` in CWD | Application log file |
| `FFMPEG` | Dynamic path | FFmpeg executable path |
| `THEME_DIR` | Dynamic path | Qt theme files directory |
| `RESOURCE_BASE` | Dynamic | Base for resource resolution (dev vs compiled) |

## Path Resolution Logic

```
IS_COMPILED?
├── No (dev mode)
│   ├── CWD = directory of sys.argv[0]
│   └── RESOURCE_BASE = CWD
│
└── Yes (compiled)
    ├── PyInstaller 6.x
    │   ├── RESOURCE_BASE = sys._MEIPASS (→ _internal/)
    │   └── VLC_PATH = _internal/plugins/vlc/
    │
    └── PyInstaller 5.x
        ├── RESOURCE_BASE = CWD
        └── VLC_PATH = CWD/plugins/vlc/
```

## Version Bump Locations

When changing version, update all 4 files:

1. `src/pyplayer/constants.py` — `VERSION` string
2. `executable/version_info_main.txt` — Windows version metadata
3. `executable/version_info_updater.txt` — Updater version metadata
4. `executable/installer.iss` — `AppVersion` define

See [[docs/build/release-process]] for the full version bump checklist.

---

Related: [[docs/reference/config-and-paths]] | [[docs/build/release-process]] | [[docs/build/packaging-guide]] | [[docs/architecture/app-flow]]
