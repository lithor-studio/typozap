"""Services locaux : profils applicatifs, métriques, journal et historique protégé."""

import base64
import ctypes
import json
import logging
import logging.handlers
import subprocess
import sys
from ctypes import wintypes
from datetime import datetime, timezone

from typozap.engine import app_data_dir


def technical_logger():
    """Journal rotatif sans contenu utilisateur."""
    folder = app_data_dir() / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("typozap")
    if not logger.handlers:
        handler = logging.handlers.RotatingFileHandler(
            folder / "typozap.log", maxBytes=500_000, backupCount=2, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def active_window_title():
    """Retourne seulement le titre de la fenêtre active, jamais son contenu."""
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to get name of first process whose frontmost is true'],
                capture_output=True, text=True, timeout=1, check=False,
            )
            return result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    if sys.platform != "win32":
        return ""
    user32 = ctypes.windll.user32
    window = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(window)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(window, buffer, length + 1)
    return buffer.value


def process_memory_mb(pid):
    if sys.platform != "win32" or not pid:
        return None
    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
        ]
    handle = ctypes.windll.kernel32.OpenProcess(0x1000 | 0x0400, False, pid)
    if not handle:
        return None
    try:
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return counters.WorkingSetSize / (1024 * 1024)
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)
    return None


def style_for_window(title, profiles, fallback):
    lowered = title.lower()
    for pattern, style in profiles.items():
        if pattern.strip() and pattern.strip().lower() in lowered:
            return style
    return fallback


class Metrics:
    def __init__(self, settings):
        self.settings = settings

    def record(self, duration, source_length):
        count = self.settings.value("metrics/count", 0, type=int) + 1
        total_ms = self.settings.value("metrics/total_ms", 0, type=int) + int(duration * 1000)
        chars = self.settings.value("metrics/chars", 0, type=int) + source_length
        self.settings.setValue("metrics/count", count)
        self.settings.setValue("metrics/total_ms", total_ms)
        self.settings.setValue("metrics/chars", chars)

    def summary(self):
        count = self.settings.value("metrics/count", 0, type=int)
        total_ms = self.settings.value("metrics/total_ms", 0, type=int)
        chars = self.settings.value("metrics/chars", 0, type=int)
        average = total_ms / count / 1000 if count else 0
        return count, chars, average


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data):
    buffer = ctypes.create_string_buffer(data)
    return _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def _dpapi(data, protect):
    if sys.platform != "win32":
        raise RuntimeError("Historique chiffré disponible uniquement sous Windows pour le moment.")
    source, keepalive = _blob(data)
    output = _Blob()
    function = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    args = (ctypes.byref(source), "TypoZap", None, None, None, 0, ctypes.byref(output)) if protect else (
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output)
    )
    if not function(*args):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)


class SecureHistory:
    """Historique optionnel protégé par le compte Windows via DPAPI."""

    def __init__(self):
        self.path = app_data_dir() / "history.dat"

    @property
    def available(self):
        return sys.platform == "win32"

    def load(self):
        if not self.path.exists():
            return []
        try:
            encrypted = base64.b64decode(self.path.read_bytes())
            return json.loads(_dpapi(encrypted, False).decode("utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return []

    def add(self, original, corrected, style):
        entries = self.load()
        entries.insert(0, {
            "date": datetime.now(timezone.utc).isoformat(), "style": style,
            "original": original, "corrected": corrected,
        })
        payload = json.dumps(entries[:20], ensure_ascii=False).encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(base64.b64encode(_dpapi(payload, True)))

    def clear(self):
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
