"""Détection et lancement du moteur local TypoZap embarqué."""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests

from typozap.correctors import LocalEngineCorrector, OllamaCorrector


def app_data_dir():
    if sys.platform == "win32":
        root = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library/Application Support"
    else:
        root = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share"))
    return root / "TypoZap"


def resource_dir():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


class EngineManager:
    """Lance le moteur privé ou utilise Ollama comme solution de repli."""
    def __init__(self):
        executable = "typozap-engine.exe" if sys.platform == "win32" else "typozap-engine"
        self.binary = Path(os.getenv("TYPOZAP_ENGINE", resource_dir() / "runtime" / executable))
        self.model = Path(os.getenv(
            "TYPOZAP_MODEL_PATH",
            app_data_dir() / "models" / "Ministral-3-3B-Instruct-2512-Q4_K_M.gguf",
        ))
        self.process = None

    @property
    def embedded_ready(self):
        return self.binary.is_file() and self.model.is_file()

    def start(self):
        """Démarre le serveur sur un port libre et attend son état sain."""
        if not self.embedded_ready:
            return None
        port = self._free_port()
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self.process = subprocess.Popen(
            [str(self.binary), "-m", str(self.model), "--host", "127.0.0.1", "--port", str(port),
             "-c", "2048", "-ngl", "auto"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        url = f"http://127.0.0.1:{port}"
        for _ in range(80):
            if self.process.poll() is not None:
                break
            try:
                if requests.get(f"{url}/health", timeout=0.25).ok:
                    return LocalEngineCorrector(url)
            except requests.RequestException:
                time.sleep(0.1)
        self.stop()
        return None

    def corrector(self):
        return self.start() or OllamaCorrector()

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None

    @staticmethod
    def _free_port():
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]
