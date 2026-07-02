import unittest

try:
    from PyQt5.QtCore import QMimeData
    from typozap.clipboard import ClipboardTransaction, mime_snapshot
except ImportError:
    QMimeData = None


class FakeClipboard:
    def __init__(self, mime_data):
        self.data = mime_data

    def mimeData(self):
        return self.data

    def setMimeData(self, data):
        self.data = data


def text_mime(text, html=None):
    data = QMimeData()
    data.setText(text)
    if html:
        data.setHtml(html)
    return data


@unittest.skipIf(QMimeData is None, "PyQt5 absent")
class ClipboardTransactionTests(unittest.TestCase):
    def test_capture_marker_preserves_original_on_timeout(self):
        clipboard = FakeClipboard(text_mime("ancien", "<b>ancien</b>"))
        original = mime_snapshot(clipboard.mimeData())
        transaction = ClipboardTransaction(clipboard)
        transaction.begin_capture()

        self.assertTrue(transaction.capture_is_pending())
        self.assertTrue(transaction.restore_original_if_capture_pending())
        self.assertEqual(mime_snapshot(clipboard.mimeData()), original)

    def test_restores_all_original_formats(self):
        clipboard = FakeClipboard(text_mime("ancien", "<b>ancien</b>"))
        original = mime_snapshot(clipboard.mimeData())
        transaction = ClipboardTransaction(clipboard)
        clipboard.setMimeData(text_mime("sélection"))
        transaction.mark_selection()
        clipboard.setMimeData(text_mime("corrigé"))
        transaction.mark_corrected()

        self.assertTrue(transaction.restore_if_unchanged())
        self.assertEqual(mime_snapshot(clipboard.mimeData()), original)

    def test_user_copy_is_never_overwritten(self):
        clipboard = FakeClipboard(text_mime("ancien"))
        transaction = ClipboardTransaction(clipboard)
        clipboard.setMimeData(text_mime("sélection"))
        transaction.mark_selection()
        clipboard.setMimeData(text_mime("corrigé"))
        transaction.mark_corrected()
        clipboard.setMimeData(text_mime("nouvelle copie utilisateur"))

        self.assertFalse(transaction.restore_if_unchanged())
        self.assertEqual(clipboard.mimeData().text(), "nouvelle copie utilisateur")

    def test_identical_user_copy_removes_result_token(self):
        clipboard = FakeClipboard(text_mime("ancien"))
        transaction = ClipboardTransaction(clipboard)
        transaction.set_corrected_text("corrigé")
        clipboard.setMimeData(text_mime("corrigé"))

        self.assertFalse(transaction.restore_if_unchanged())
        self.assertEqual(clipboard.mimeData().text(), "corrigé")

    def test_change_during_inference_is_detected(self):
        clipboard = FakeClipboard(text_mime("ancien"))
        transaction = ClipboardTransaction(clipboard)
        clipboard.setMimeData(text_mime("sélection"))
        transaction.mark_selection()
        clipboard.setMimeData(text_mime("copie utilisateur"))

        self.assertFalse(transaction.selection_is_unchanged())


if __name__ == "__main__":
    unittest.main()
