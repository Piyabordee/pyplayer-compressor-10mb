"""
Resource Path Helper for PyPlayer Compressor
จัดการ path ของ resource files ทั้งตอน development และตอนรันจาก exe

การใช้งาน:
    from resource_helper import resource_path

    # อ่านไฟล์ config
    config_file = resource_path('config.ini')

    # เรียก ffmpeg.exe
    ffmpeg_path = resource_path('plugins/ffmpeg/ffmpeg.exe')

    # โหลด icon
    icon_path = resource_path('themes/resources/logo.ico')
"""

import os
import sys


def resource_path(relative_path: str) -> str:
    """
    รับ path แบบ relative และคืนค่า absolute path ที่ถูกต้อง
    ทำงานได้ทั้งใน development mode และ compiled exe mode (PyInstaller)

    Args:
        relative_path: Path แบบ relative เช่น 'config.ini', 'themes/logo.ico'

    Returns:
        Absolute path ที่ใช้งานได้จริง

    Examples:
        >>> resource_path('config.ini')
        'C:\\Users\\...\\pyplayer-master\\config.ini'  # development
        'C:\\Program Files\\PyPlayer\\config.ini'      # compiled
    """
    try:
        # PyInstaller สร้างโฟลเดอร์ temp สำหรับ resource files
        # sys._MEIPASS จะมีค่าเฉพาะตอนรันจาก exe
        base_path = sys._MEIPASS
    except AttributeError:
        # ตอน development ไม่มี sys._MEIPASS
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def get_resource_dir(relative_dir: str = "") -> str:
    """
    รับชื่อโฟลเดอร์ และคืนค่า absolute path ของโฟลเดอร์นั้น
    สะดวกสำหรับกรณีที่ต้องการ path ของโฟลเดอร์ (ไม่ใช่ไฟล์)

    Args:
        relative_dir: ชื่อโฟลเดอร์ เช่น 'themes', 'plugins'

    Returns:
        Absolute path ของโฟลเดอร์

    Examples:
        >>> get_resource_dir('themes')
        'C:\\Program Files\\PyPlayer\\themes'
    """
    return resource_path(relative_dir)


def ensure_resource_path(relative_path: str) -> str:
    """
    คล้ายกับ resource_path() แต่จะตรวจสอบว่าไฟล์/โฟลเดอร์มีอยู่จริง
    ถ้าไม่มีจะสร้างโฟลเดอร์ (สำหรับโฟลเดอร์) หรือ raise Exception (สำหรับไฟล์)

    Args:
        relative_path: Path แบบ relative

    Returns:
        Absolute path ที่ใช้งานได้

    Raises:
        FileNotFoundError: ถ้าเป็นไฟล์และไม่พบไฟล์
    """
    full_path = resource_path(relative_path)

    if os.path.exists(full_path):
        return full_path

    # ถ้าเป็นโฟลเดอร์ที่ไม่มีอยู่ ให้สร้าง
    if not os.path.splitext(relative_path)[1]:  # ไม่มี extension = เป็นโฟลเดอร์
        os.makedirs(full_path, exist_ok=True)
        return full_path

    # ถ้าเป็นไฟล์ที่ไม่พบ
    raise FileNotFoundError(f"Resource not found: {full_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Compatibility layer สำหรับโค้ดเดิมของ PyPlayer
# ─────────────────────────────────────────────────────────────────────────────

# สำหรับโค้ดที่ใช้ constants.IS_COMPILED อยู่แล้ว ไม่ต้องเปลี่ยน
# แต่ถ้าต้องการย้ายมาใช้ resource_path helper สามารถทำได้ดังนี้:

"""
ตัวอย่างการ migrate จาก constants.py ไปใช้ resource_path:

# วิธีเดิม (ใน constants.py):
if IS_COMPILED:
    FFMPEG = f'{CWD}{_sep}plugins{_sep}ffmpeg{_sep}ffmpeg'
else:
    folder = 'ffmpeg-windows' if IS_WINDOWS else 'ffmpeg-unix'
    FFMPEG = f'{CWD}{_sep}executable{_sep}include{_sep}{folder}{_sep}ffmpeg'

# วิธีใหม่ (ใช้ resource_path):
from resource_helper import resource_path
import os

FFMPEG = resource_path('plugins/ffmpeg/ffmpeg')
if IS_WINDOWS and not FFMPEG.endswith('.exe'):
    FFMPEG = FFMPEG + '.exe'
"""
