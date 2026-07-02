"""Détection et lancement du moteur Ministral privé embarqué."""

import os
import ctypes
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests

from typozap.correctors import MinistralCorrector
from typozap.model_installer import MODEL_SIZE


MODEL_FILENAME = "Ministral-3-3B-Instruct-2512-Q4_K_M.gguf"


def app_data_dir():
    if sys.platform == "win32":
        root = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library/Application Support"
    else:
        root = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share"))
    return root / "TypoZap"


def resource_dir():
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


class EngineManager:
    """Lance exclusivement le moteur et le modèle figés par TypoZap."""

    def __init__(self):
        executable = "typozap-engine.exe" if sys.platform == "win32" else "typozap-engine"
        bundled_runtime = resource_dir() / "runtime"
        runtime = self._stable_runtime(bundled_runtime) if hasattr(sys, "_MEIPASS") else bundled_runtime
        self.binary = runtime / executable
        self.model = app_data_dir() / "models" / MODEL_FILENAME
        self.process = None
        self.job_handle = None

    @staticmethod
    def _stable_runtime(source):
        """Copie le runtime hors du dossier temporaire PyInstaller avant exécution."""
        target = app_data_dir() / "runtime"
        target.mkdir(parents=True, exist_ok=True)
        if not source.is_dir():
            return target
        for source_file in source.rglob("*"):
            if not source_file.is_file():
                continue
            relative = source_file.relative_to(source)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists() or destination.stat().st_size != source_file.stat().st_size:
                shutil.copy2(source_file, destination)
        return target

    @property
    def embedded_ready(self):
        return self.binary.is_file() and self.model.is_file() and self.model.stat().st_size == MODEL_SIZE

    def start(self):
        """Démarre le serveur local sur un port privé et attend son état sain."""
        if not self.embedded_ready:
            return None
        port = self._free_port()
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            self.process = subprocess.Popen(
                [str(self.binary), "-m", str(self.model), "--host", "127.0.0.1", "--port", str(port),
                 "-c", "8192", "-ngl", "auto"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
            if sys.platform == "win32":
                self.job_handle = self._assign_kill_job(self.process)
        except OSError:
            self.process = None
            return None
        url = f"http://127.0.0.1:{port}"
        for _ in range(80):
            if self.process.poll() is not None:
                break
            try:
                if requests.get(f"{url}/health", timeout=0.25).ok:
                    return MinistralCorrector(url)
            except requests.RequestException:
                pass
            # Le serveur répond 503 pendant le chargement du modèle : attendre
            # aussi dans ce cas, sinon les essais sont épuisés instantanément.
            time.sleep(0.1)
        self.stop()
        return None

    def corrector(self):
        return self.start()

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        if self.job_handle:
            ctypes.windll.kernel32.CloseHandle(self.job_handle)
            self.job_handle = None

    @staticmethod
    def _free_port():
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    @staticmethod
    def _assign_kill_job(process):
        """Demande à Windows de tuer le moteur si le processus parent disparaît."""
        from ctypes import wintypes

        class BasicLimits(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IoCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
            )]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimits), ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32 = ctypes.windll.kernel32
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None
        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        configured = kernel32.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits))
        assigned = configured and kernel32.AssignProcessToJobObject(job, wintypes.HANDLE(process._handle))
        if not assigned:
            kernel32.CloseHandle(job)
            return None
        return job
