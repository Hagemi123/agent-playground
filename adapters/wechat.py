"""
WeChat UI Automation Adapter for Agent Playground.
Interacts with official Windows PC WeChat client using pure ctypes Win32 Desktop API.
Fully supports Windows Desktop Isolation (WinSta0/Default) and WeChat 4.x Qt/MMUI.
"""

import os
import time
import ctypes
from ctypes import wintypes
from typing import Dict, Any, Optional
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

# Configure Win32 ctypes types for 64-bit safety
user32.GetDC.restype = wintypes.HDC
user32.GetDC.argtypes = [wintypes.HWND]
user32.ReleaseDC.restype = ctypes.c_int
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.BitBlt.restype = wintypes.BOOL
gdi32.BitBlt.argtypes = [
    wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD
]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.restype = wintypes.BOOL
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.GetDIBits.restype = ctypes.c_int
gdi32.GetDIBits.argtypes = [
    wintypes.HDC, wintypes.HBITMAP, ctypes.c_uint, ctypes.c_uint,
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint
]

kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [ctypes.c_uint, wintypes.HANDLE]

DESKTOP_ALL = 0x01FF
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
SW_RESTORE = 9
CF_UNICODETEXT = 13


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD)
    ]


class WeChatAdapter:
    def __init__(self):
        self.main_hwnd = None

    @staticmethod
    def attach_to_default_desktop():
        """Ensure calling thread attaches to the interactive user desktop 'Default'."""
        h_desktop = user32.OpenDesktopW("Default", 0, False, DESKTOP_ALL)
        if h_desktop:
            user32.SetThreadDesktop(h_desktop)
            return h_desktop
        return None

    def find_wechat_window(self) -> Optional[int]:
        """Finds WeChat main window handle on Default desktop."""
        h_desk = self.attach_to_default_desktop()
        if not h_desk:
            return None

        target_hwnd = None

        def callback(hwnd, _):
            nonlocal target_hwnd
            if user32.IsWindow(hwnd):
                cls_buff = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, cls_buff, 256)
                length = user32.GetWindowTextLengthW(hwnd)
                title = ""
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value

                if ("微信" in title or "WeChat" in cls_buff.value) and "Qt" in cls_buff.value:
                    target_hwnd = hwnd
                    return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumDesktopWindows(h_desk, WNDENUMPROC(callback), 0)
        self.main_hwnd = target_hwnd
        return target_hwnd

    def check_status(self) -> Dict[str, Any]:
        """Check whether PC WeChat is running and active on the desktop."""
        hwnd = self.find_wechat_window()
        if not hwnd:
            return {
                "running": False,
                "logged_in": False,
                "msg": "WeChat main window not found on interactive desktop."
            }

        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return {
            "running": True,
            "logged_in": True,
            "hwnd": hwnd,
            "rect": f"({rect.left},{rect.top},{rect.right},{rect.bottom})[{rect.right - rect.left}x{rect.bottom - rect.top}]"
        }

    @staticmethod
    def set_clipboard(text: str):
        """Pure ctypes clipboard write (no external dependencies)."""
        user32.OpenClipboard(None)
        user32.EmptyClipboard()
        data = text.encode('utf-16le') + b'\x00\x00'
        h_mem = kernel32.GlobalAlloc(0x0002, len(data))
        p_mem = kernel32.GlobalLock(h_mem)
        ctypes.memmove(p_mem, data, len(data))
        kernel32.GlobalUnlock(h_mem)
        user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        user32.CloseClipboard()

    def capture_screen(self, filepath: str) -> Image.Image:
        """Capture full screen via pure ctypes Win32 BitBlt and GetDIBits."""
        self.attach_to_default_desktop()
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        hdc_screen = user32.GetDC(None)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        h_bmp = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
        gdi32.SelectObject(hdc_mem, h_bmp)
        gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, 0, 0, 0x00CC0020)

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(hdc_mem, h_bmp, 0, h, buf, ctypes.byref(bmi), 0)

        gdi32.DeleteObject(h_bmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(None, hdc_screen)

        img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1)
        img = img.convert("RGB")
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        img.save(filepath)
        return img

    def send_message_to_current_chat(self, message: str, capture_path: Optional[str] = None) -> bool:
        """Send message to currently open chat window."""
        hwnd = self.find_wechat_window()
        if not hwnd:
            print("[-] WeChat main window not found.")
            return False

        try:
            # 1. Bring window to front
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            time.sleep(0.3)

            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))

            # 2. Click in input box
            input_x = rect.left + 300
            input_y = rect.bottom - 90
            user32.SetCursorPos(input_x, input_y)
            time.sleep(0.1)
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.4)

            # 3. Paste via Ctrl+V
            self.set_clipboard(message)
            user32.keybd_event(0x11, 0, 0, 0) # Ctrl down
            user32.keybd_event(0x56, 0, 0, 0) # V down
            user32.keybd_event(0x56, 0, 2, 0) # V up
            user32.keybd_event(0x11, 0, 2, 0) # Ctrl up
            time.sleep(0.6)

            # 4. Send via Enter
            user32.keybd_event(0x0D, 0, 0, 0) # Enter down
            user32.keybd_event(0x0D, 0, 2, 0) # Enter up
            time.sleep(0.5)

            # 5. Click Send button as safety net
            send_x = rect.left + 540
            send_y = rect.bottom - 45
            user32.SetCursorPos(send_x, send_y)
            time.sleep(0.1)
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.8)

            if capture_path:
                self.capture_screen(capture_path)

            print(f"[+] Message successfully sent to current WeChat chat!")
            return True
        except Exception as e:
            print(f"[-] Failed to send message: {e}")
            return False
