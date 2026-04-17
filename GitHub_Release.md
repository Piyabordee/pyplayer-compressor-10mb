# GitHub Release Guide - PyPlayer Compressor 10MB

> ไฟล์นี้สำหรับ AI agent ใช้อ้างอิงเมื่อต้องการ build และ release PyPlayer Compressor
> อัปเดตล่าสุด: 2026-03-28

---

## 0. ข้อมูลโปรเจกต์

```
ชื่อ:           PyPlayer Compressor 10MB
Repo:           https://github.com/Piyabordee/pyplayer-compressor-10mb
Entry Point:    run.pyw (or main.pyw / python -m pyplayer)
Version:        0.6.0 beta
Python:         3.13+
UI Framework:   PyQt5
Media Backend:  VLC (libvlc) + FFmpeg
Platform:       Windows (primary)
```

---

## 1. โครงสร้างไฟล์สำคัญ

```
pyplayer-master/
├── run.pyw                           # Entry point (backward-compatible)
├── main.pyw                          # Legacy entry (thin wrapper)
├── constants.py                      # Version + REPOSITORY_URL + path resolution
├── config.py                         # Config load/save
├── util.py                           # FFmpeg wrappers
├── qthelpers.py                      # Qt utility functions
├── qtstart.py                        # Startup + signal connections
├── widgets.py                        # QVideoPlayer, QVideoSlider
├── update.py                         # Update checking logic
├── resource_helper.py                # Resource path helper (PyInstaller 6.x)
│
├── bin/
│   ├── window_pyplayer.py            # Main window UI (generated)
│   ├── window_*.py                   # Other UI files
│   ├── configparsebetter.py          # Config parser
│   └── updater.py                    # Update utility
│
├── themes/
│   ├── midnight.txt                  # Theme stylesheets
│   ├── blueberry_breeze.txt
│   └── resources/
│       ├── logo.ico                  # App icon (102KB)
│       ├── logo_filled.ico
│       └── updater.ico
│
├── executable/
│   ├── main.spec                     # ⭐ PyInstaller spec (onedir)
│   ├── updater.spec                  # ⭐ PyInstaller spec (onefile)
│   ├── hook.py                       # ⭐ Runtime hook (VLC path + PID management)
│   ├── installer.iss                 # ⭐ Inno Setup installer script
│   ├── build.py                      # Original build script (legacy)
│   ├── exclude.txt                   # Files to exclude from build
│   ├── version_info_main.txt         # Windows version metadata for exe
│   ├── version_info_updater.txt      # Windows version metadata for updater
│   ├── main_onefile.spec             # Optional: onefile spec
│   │
│   └── include/
│       ├── ffmpeg-windows/
│       │   ├── ffmpeg.exe            # 355KB
│       │   ├── ffprobe.exe           # 192KB
│       │   └── *.dll                 # avcodec-59, avformat-59, etc.
│       └── vlc-windows/
│           ├── libvlc.dll            # 191KB
│           ├── libvlccore.dll        # 2.8MB
│           └── plugins/              # VLC codec plugins
```

---

## 2. ข้อกำหนดเบื้องต้น (Prerequisites)

### 2.1 บนเครื่อง Developer

```bash
# Python 3.13+
python --version

# Dependencies
pip install -r requirements.txt

# ต้องมีไฟล์เหล่านี้อยู่:
#   executable/include/ffmpeg-windows/ffmpeg.exe
#   executable/include/ffmpeg-windows/ffprobe.exe
#   executable/include/vlc-windows/libvlc.dll
#   executable/include/vlc-windows/libvlccore.dll
#   executable/include/vlc-windows/plugins/
#   themes/resources/logo.ico

# ติดตั้ง Inno Setup 6
# Download: https://jrsoftware.org/isdl.php
# Default path: C:\Program Files (x86)\Inno Setup 6\ISCC.exe
```

### 2.2 ตรวจสอบก่อน build

```bash
# ตรวจสอบไฟล์จำเป็น
test -f "executable/include/ffmpeg-windows/ffmpeg.exe" && echo "✅ FFmpeg OK" || echo "❌ FFmpeg missing"
test -f "executable/include/vlc-windows/libvlc.dll" && echo "✅ VLC OK" || echo "❌ VLC missing"
test -f "themes/resources/logo.ico" && echo "✅ Icon OK" || echo "❌ Icon missing"

# ตรวจสอบ version ใน constants.py
grep "VERSION" constants.py
grep "REPOSITORY_URL" constants.py

# ตรวจสอบ PyInstaller version (ต้อง >= 6.0)
python -m PyInstaller --version
```

---

## 3. ขั้นตอน Build (ทีละขั้น)

### 3.1 Clean old build artifacts

```bash
cd executable
rm -rf build/ compiling/ installer_output/
```

### 3.2 Build pyplayer.exe (onedir mode)

```bash
# ต้อง cd เข้า executable/ ก่อน เพราะ main.spec ใช้ os.getcwd()
cd executable

python -m PyInstaller main.spec \
    --noconfirm \
    --distpath compiling \
    --workpath build
```

**ตรวจสอบผลลัพธ์:**
```bash
ls -lh compiling/release/pyplayer.exe        # ควรได้ ~5MB
ls compiling/release/_internal/themes/        # ต้องมี theme files
ls compiling/release/_internal/plugins/vlc/   # ต้องมี libvlc.dll
ls compiling/release/_internal/plugins/ffmpeg/ # ต้องมี ffmpeg.exe
```

**ถ้าพบปัญหา:**
- `IndexError: list index out of range` → main.spec ใช้ `sys.argv[1]` อยู่ → แก้เป็น `os.getcwd()`
- `Syntax error while compiling constants.py` → ตรวจสอบ `continue` นอก loop
- `Hidden import 'Send2Trash' not found` → ไม่สำคัญ, ข้ามได้

### 3.3 Build updater.exe (onefile mode)

```bash
# ยังอยู่ใน executable/
python -m PyInstaller updater.spec \
    --noconfirm \
    --distpath compiling \
    --workpath build
```

**ตรวจสอบผลลัพธ์:**
```bash
ls -lh compiling/updater.exe    # ควรได้ ~7MB
```

### 3.4 ทดสอบ exe ก่อนสร้าง installer

```bash
# รัน pyplayer.exe ทดสอบ
./compiling/release/pyplayer.exe
```

**ตรวจสอบ:**
- [ ] หน้าต่างเปิดขึ้นไหม?
- [ ] Theme โหลดไหม? (ไม่ขาวๆ)
- [ ] เปิดไฟล์วิดีโอได้ไหม?
- [ ] เล่นวิดีโอได้ไหม?
- [ ] Trim/Save ใช้ได้ไหม?

**ถ้าพบปัญหา:**

| อาการ | สาเหตุ | วิธีแก้ |
|-------|--------|--------|
| `ModuleNotFoundError: No module named 'constants'` | constants.py มี syntax error | ตรวจสอบ `continue` นอก loop, เปลี่ยนเป็น `pass` |
| `Could not find module 'libvlc.dll'` | hook.py หา VLC path ไม่เจอ | ตรวจสอบ hook.py ใช้ `sys._MEIPASS` หรือยัง |
| Theme ขาวๆ / ไม่สวย | THEME_DIR ชี้ผิด path | ตรวจสอบ constants.py ใช้ `RESOURCE_BASE` แทน `CWD` |
| FFmpeg not detected | FFMPEG path ผิด | ตรวจสอบ constants.py verify_ffmpeg() |
| Window เปิดแล้วปิดทันที | ImportError บาง module | รันจาก command prompt เพื่อดู error |

### 3.5 Build Inno Setup installer

```bash
# วิธี A: Command line
"C:/Program Files (x86)/Inno Setup 6/ISCC.exe" installer.iss

# วิธี B: GUI (แนะนำถ้า debug)
"C:/Program Files (x86)/Inno Setup 6/Compil32.exe" installer.iss
```

**ผลลัพธ์:**
```
executable/installer_output/PyPlayerCompressor-Setup-0.6.0 beta.exe
ขนาด: ~120MB
```

---

## 4. สร้าง GitHub Release

### 4.1 เตรียมข้อมูล version

แก้ `constants.py` ก่อน build:
```python
VERSION = 'pyplayer 0.6.0 beta'          # เปลี่ยน version ตรงนี้
REPOSITORY_URL = 'https://github.com/Piyabordee/pyplayer-compressor-10mb'
```

### 4.2 สร้าง git tag และ push

```bash
# จาก root directory
cd ..

# สร้าง tag
git tag v0.6.0-beta

# Push tag
git push origin v0.6.0-beta
```

### 4.3 สร้าง Release พร้อม upload installer

```bash
# วิธี A: ใช้ gh CLI (แนะนำ)
gh release create v0.6.0-beta \
    "executable/installer_output/PyPlayerCompressor-Setup-0.6.0 beta.exe" \
    --title "PyPlayer Compressor v0.6.0 Beta" \
    --notes "## What's New
- Video player and compressor with FFmpeg
- Always-visible Save button
- Quick Trim functionality
- Auto-compress after trim (target ~10MB)
- Custom theme support

## System Requirements
- Windows 10/11 (64-bit)
- No Python installation required

## Installation
1. Download the installer
2. Run the setup wizard
3. Launch PyPlayer Compressor
4. Open a video file and enjoy!"

# วิธี B: สร้าง draft release บน GitHub web
# 1. ไปที่ https://github.com/Piyabordee/pyplayer-compressor-10mb/releases/new
# 2. เลือก tag v0.6.0-beta
# 3. ตั้งชื่อ: "PyPlayer Compressor v0.6.0 Beta"
# 4. Upload installer file
# 5. กด Publish release
```

---

## 5. ระบบ Auto-Update (ทำงานอย่างไร)

### Flow:
```
update.py::check_for_update()
    │
    ├─ GET https://github.com/Piyabordee/pyplayer-compressor-10mb/releases/latest
    │   │
    │   └─ GitHub API ตอบกลับ JSON:
    │       {
    │         "tag_name": "v0.7.0-beta",
    │         "name": "PyPlayer Compressor v0.7.0 Beta",
    │         "assets": [
    │           {
    │             "name": "PyPlayerCompressor-Setup-0.7.0 beta.exe",
    │             "browser_download_url": "https://..."
    │           }
    │         ],
    │         "body": "Release notes..."
    │       }
    │
    ├─ เปรียบเทียบ tag_name กับ VERSION ใน constants.py
    │
    └─ ถ้าเวอร์ชันใหม่กว่า → แสดง popup ให้ download
```

### ไฟล์ที่เกี่ยวข้อง:
| ไฟล์ | หน้าที่ |
|------|---------|
| `constants.py` → `REPOSITORY_URL` | กำหนด base URL |
| `constants.py` → `VERSION` | เวอร์ชันปัจจุบัน |
| `update.py` → `check_for_update()` | ส่ง request + เปรียบเทียบ version |
| `bin/updater.py` | Download + install update |

---

## 6. ปัญหาที่เคยเจอและวิธีแก้ (Troubleshooting)

### 6.1 PyInstaller 6.x Breaking Changes

**ปัญหา:** `sys.argv[1]` ไม่มีแล้วใน spec file
```python
# ❌ เก่า (PyInstaller 5.x)
CWD = os.path.dirname(os.path.realpath(sys.argv[1]))

# ✅ ใหม่ (PyInstaller 6.x)
CWD = os.path.abspath(os.getcwd())  # cd เข้า executable/ ก่อน build
```

**ปัญหา:** `__file__` ไม่มีใน spec file
```python
# ❌ ไม่ทำงาน
SPEC_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ ใช้ os.getcwd()
SPEC_DIR = os.path.abspath(os.getcwd())
```

### 6.2 PyInstaller 6.x Directory Structure

```
# PyInstaller 5.x:
release/
├── pyplayer.exe
├── PyQt5/
├── plugins/
└── themes/

# PyInstaller 6.x:
release/
├── pyplayer.exe          # เดี่ยวๆ
└── _internal/            # ทุกอย่างอยู่ในนี้
    ├── PyQt5/
    ├── plugins/
    ├── themes/
    ├── python313.dll
    └── ...
```

**ผลกระทบ:**
- `sys._MEIPASS` ชี้ไปที่ `_internal/`
- `sys.executable` ชี้ไปที่ `pyplayer.exe`
- `os.path.dirname(sys.executable)` = directory ของ exe (ไม่ใช่ _internal)

### 6.3 VLC Path Resolution

```python
# hook.py ต้อง handle ทั้ง 2 versions:
if IS_FROZEN:
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 6.x
        INTERNAL_DIR = sys._MEIPASS      # → .../release/_internal
        CWD = os.path.dirname(sys.executable)  # → .../release
        VLC_PATH = os.path.join(INTERNAL_DIR, 'plugins', 'vlc')
    else:
        # PyInstaller 5.x
        CWD = os.path.dirname(sys.argv[0])
        VLC_PATH = os.path.join(CWD, 'plugins', 'vlc')
```

### 6.4 Theme Path Resolution

```python
# constants.py ต้องใช้ RESOURCE_BASE ไม่ใช่ CWD:
if IS_COMPILED and hasattr(sys, '_MEIPASS'):
    RESOURCE_BASE = sys._MEIPASS   # themes อยู่ใน _internal/themes/
else:
    RESOURCE_BASE = CWD            # themes อยู่ใน themes/

THEME_DIR = os.path.join(RESOURCE_BASE, 'themes')
```

### 6.5 Syntax Error: `continue` นอก loop

```python
# ❌ ผิด - continue ใช้ได้แค่ใน for/while loop
if not IS_COMPILED:
    try: os.makedirs(THEME_DIR)
    except: continue    # ← SyntaxError!

# ✅ ถูก
if not IS_COMPILED:
    try: os.makedirs(THEME_DIR)
    except: pass
```

### 6.6 Antivirus False Positive

PyInstaller exe มักถูก antivirus flag:
- แนะนำ: code signing certificate
- ชั่วคราว: เพิ่ม exception ใน antivirus
- ลดปัญหา: ตั้ง `upx=False` ใน spec file

### 6.7 Inno Setup Path Issues

```iss
; ❌ ผิด - path ซ้อย (Inno Setup รันจาก executable/)
Source: "executable\compiling\release\pyplayer.exe"

; ✅ ถูก - path สัมพัทธ์จาก .iss file (อยู่ใน executable/)
Source: "compiling\release\pyplayer.exe"

; OutputDir ก็ต้องระวัง:
; ❌ OutputDir=executable\installer_output    ; → สร้าง executable/executable/installer_output/
; ✅ OutputDir=installer_output                ; → สร้าง executable/installer_output/
```

---

## 7. Quick Reference: คำสั่ง Build ทั้งหมด

```bash
# ============================================
# Complete Build Sequence (Copy & Paste)
# ============================================

# Step 1: เข้า executable directory
cd executable

# Step 2: Clean old builds
rm -rf build/ compiling/ installer_output/

# Step 3: Build pyplayer.exe
python -m PyInstaller main.spec --noconfirm --distpath compiling --workpath build

# Step 4: Build updater.exe
python -m PyInstaller updater.spec --noconfirm --distpath compiling --workpath build

# Step 5: Test exe
./compiling/release/pyplayer.exe

# Step 6: Build installer (ถ้า exe ทำงานปกติ)
"C:/Program Files (x86)/Inno Setup 6/ISCC.exe" installer.iss

# Step 7: Test installer
./installer_output/PyPlayerCompressor-Setup-*.exe

# ============================================
# GitHub Release (ถ้าต้องการเผยแพร่)
# ============================================

cd ..
git tag v0.6.0-beta
git push origin v0.6.0-beta
gh release create v0.6.0-beta \
    "executable/installer_output/PyPlayerCompressor-Setup-0.6.0 beta.exe" \
    --title "PyPlayer Compressor v0.6.0 Beta" \
    --notes "Release notes here"
```

---

## 8. Version Bump Checklist

เมื่อต้องการ release เวอร์ชันใหม่:

1. **แก้ version ใน `constants.py`:**
   ```python
   VERSION = 'pyplayer 0.7.0 beta'
   ```

2. **แก้ version ใน `executable/version_info_main.txt`:**
   ```
   filevers=(0, 7, 0, 0)
   prodvers=(0, 7, 0, 0)
   StringStruct(u'FileVersion', u'0.7.0.0')
   StringStruct(u'ProductVersion', u'0.7.0 beta')
   ```

3. **แก้ version ใน `executable/version_info_updater.txt`** (เหมือนด้านบน)

4. **แก้ version ใน `executable/installer.iss`:**
   ```
   #define AppVersion "0.7.0 beta"
   ```

5. **Build + Test + Release** (ตาม Section 7)

---

## 9. Checklist ก่อน Release

- [ ] Version ตรงทั้ง 4 ไฟล์ (constants.py, version_info_*.txt, installer.iss)
- [ ] REPOSITORY_URL ชี้ไป repo ที่ถูกต้อง
- [ ] Build pyplayer.exe สำเร็จ (ไม่มี syntax warning)
- [ ] Theme โหลดสวย (ไม่ขาว)
- [ ] เล่นวิดีโอได้
- [ ] Trim/Save/Compress ใช้ได้
- [ ] FFmpeg ทำงาน (verify จาก log)
- [ ] VLC ทำงาน (เล่นได้)
- [ ] Updater build สำเร็จ
- [ ] Installer build สำเร็จ
- [ ] ติดตั้งบนเครื่องใหม่ได้
- [ ] Uninstall สะอาด
- [ ] git tag และ push สำเร็จ
- [ ] GitHub Release สร้างสำเร็จ
- [ ] Download link ทำงาน

---

*Last updated: 2026-03-28*
*For: PyPlayer Compressor 10MB v0.6.0 beta*
