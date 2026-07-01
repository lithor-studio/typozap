"""Transaction Qt préservant tous les formats du presse-papier."""

from PyQt5.QtCore import QByteArray
from PyQt5.QtCore import QMimeData


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
    def __init__(self, clipboard):
        self.clipboard = clipboard
        self.original = clipboard_fingerprint(clipboard)
        self.selected_fingerprint = None
        self.corrected_fingerprint = None

    def mark_selection(self):
        self.selected_fingerprint = clipboard_fingerprint(self.clipboard)

    def selection_is_unchanged(self):
        return clipboard_fingerprint(self.clipboard) == self.selected_fingerprint

    def mark_corrected(self):
        self.corrected_fingerprint = clipboard_fingerprint(self.clipboard)

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
