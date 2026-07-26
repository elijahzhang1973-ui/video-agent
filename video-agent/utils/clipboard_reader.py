"""Read Unicode text from the Windows clipboard without persisting it."""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes


CF_UNICODETEXT = 13


class ClipboardReadError(RuntimeError):
    """Raised when the Windows clipboard cannot be read safely."""


def read_clipboard_text(attempts: int = 5, retry_delay: float = 0.05) -> str:
    """Return Unicode clipboard text, or an empty string for non-text content."""
    if sys.platform != "win32":
        raise ClipboardReadError("剪贴板模式仅支持Windows。")

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL

    for attempt in range(attempts):
        if user32.OpenClipboard(None):
            break
        if attempt + 1 < attempts:
            time.sleep(retry_delay)
    else:
        raise ClipboardReadError("无法读取Windows剪贴板，请稍后重试。")

    try:
        if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return ""

        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            raise ClipboardReadError("无法读取剪贴板中的文本。")

        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            raise ClipboardReadError("无法读取剪贴板中的文本。")
        try:
            return ctypes.wstring_at(pointer)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()
