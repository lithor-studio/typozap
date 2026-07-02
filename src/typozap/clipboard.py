"""Transaction Qt préservant tous les formats du presse-papier.

Une ancienne valeur n'est jamais restaurée si l'utilisateur a effectué une
nouvelle copie pendant la correction.
"""

from PyQt5.QtCore import QByteArray
from PyQt5.QtCore import QMimeData
from uuid import uuid4


CAPTURE_MIME = "application/x-typozap-capture"
RESULT_MIME = "application/x-typozap-result"


def mime_snapshot(mime_data):
    return {fmt: bytes(mime_data.data(fmt)) for fmt in mime_data.formats()}


def restore_snapshot(clipboard, snapshot):
    data = QMimeData()
    for fmt, value in snapshot.items():
        data.setData(fmt, QByteArray(value))
    clipboard.setMimeData(data)


def clipboard_fingerprint(clipboard):
    return mime_snapshot(clipboard.mimeData())


class ClipboardTransaction:
    """Suit les états original, sélection copiée et résultat corrigé."""
    def __init__(self, clipboard):
        self.clipboard = clipboard
        self.original = clipboard_fingerprint(clipboard)
        self.capture_fingerprint = None
        self.selected_fingerprint = None
        self.corrected_fingerprint = None

    def begin_capture(self):
        """Pose un marqueur unique pour distinguer absence de sélection et copie réussie."""
        marker = QMimeData()
        marker.setData(CAPTURE_MIME, QByteArray(uuid4().hex.encode("ascii")))
        self.clipboard.setMimeData(marker)
        self.capture_fingerprint = clipboard_fingerprint(self.clipboard)

    def capture_is_pending(self):
        return clipboard_fingerprint(self.clipboard) == self.capture_fingerprint

    def mark_selection(self):
        self.selected_fingerprint = clipboard_fingerprint(self.clipboard)

    def selection_is_unchanged(self):
        return clipboard_fingerprint(self.clipboard) == self.selected_fingerprint

    def mark_corrected(self):
        self.corrected_fingerprint = clipboard_fingerprint(self.clipboard)

    def set_corrected_text(self, text):
        """Publie le résultat avec un jeton que toute copie utilisateur supprimera."""
        data = QMimeData()
        data.setText(text)
        data.setData(RESULT_MIME, QByteArray(uuid4().hex.encode("ascii")))
        self.clipboard.setMimeData(data)
        self.mark_corrected()

    def restore_if_unchanged(self):
        if clipboard_fingerprint(self.clipboard) != self.corrected_fingerprint:
            return False
        restore_snapshot(self.clipboard, self.original)
        return True

    def restore_original_if_selection_unchanged(self):
        if not self.selection_is_unchanged():
            return False
        restore_snapshot(self.clipboard, self.original)
        return True

    def restore_original_if_capture_pending(self):
        if not self.capture_is_pending():
            return False
        restore_snapshot(self.clipboard, self.original)
        return True
