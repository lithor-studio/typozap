import sys
import time

import pyautogui
from PyQt5.QtCore import QObject, QSettings, QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
)

from clipboard_transaction import ClipboardTransaction, clipboard_fingerprint
from corrector import CorrectionError
from engine import EngineManager
from platform_support import copy_shortcut, hotkey_label, hotkey_spec, paste_shortcut
from model_installer import ModelInstallError, download_model


class HotkeyBridge(QObject):
    activated = pyqtSignal()


class CorrectionDialog(QDialog):
    def __init__(self, original_text, corrected_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TypoZap - Aperçu")
        self.resize(620, 420)
        self.corrected_text = corrected_text

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Texte original :"))
        original = QTextEdit(original_text)
        original.setReadOnly(True)
        original.setMaximumHeight(150)
        layout.addWidget(original)
        layout.addWidget(QLabel("Texte corrigé :"))
        corrected = QTextEdit(corrected_text)
        corrected.setReadOnly(True)
        layout.addWidget(corrected)

        buttons = QHBoxLayout()
        copy_button = QPushButton("Copier le résultat")
        copy_button.clicked.connect(self.copy_result)
        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(copy_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def copy_result(self):
        QApplication.clipboard().setText(self.corrected_text)
        QMessageBox.information(self, "Copié", "Le texte corrigé a été copié.")


class CorrectionWorker(QThread):
    succeeded = pyqtSignal(str, str)
    failed = pyqtSignal(str)

    def __init__(self, corrector, text, style):
        super().__init__()
        self.corrector = corrector
        self.text = text
        self.style = style

    def run(self):
        try:
            self.succeeded.emit(self.text, self.corrector.correct_text(self.text, self.style))
        except CorrectionError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # La boucle graphique ne doit jamais tomber avec le moteur.
            self.failed.emit(f"Erreur inattendue : {exc}")


class ModelDownloadWorker(QThread):
    progress = pyqtSignal(int)
    succeeded = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, destination):
        super().__init__()
        self.destination = destination

    def run(self):
        try:
            download_model(
                self.destination,
                lambda done, total: self.progress.emit(int(done * 100 / total)),
            )
            self.succeeded.emit()
        except ModelInstallError as exc:
            self.failed.emit(str(exc))


class FirstRunDialog(QDialog):
    installed = pyqtSignal()

    def __init__(self, destination, parent=None):
        super().__init__(parent)
        self.destination = destination
        self.worker = None
        self.setWindowTitle("Installer le modèle français")
        self.setModal(True)
        self.resize(480, 190)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "TypoZap utilise Ministral 3 3B localement. Le téléchargement fait environ 2 Go ; "
            "vos textes resteront ensuite entièrement hors ligne."
        ))
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        self.status = QLabel("Prêt à télécharger.")
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.install_button = QPushButton("Télécharger et installer")
        self.install_button.clicked.connect(self.install)
        self.later_button = QPushButton("Plus tard")
        self.later_button.clicked.connect(self.reject)
        buttons.addWidget(self.install_button)
        buttons.addWidget(self.later_button)
        layout.addLayout(buttons)

    def install(self):
        self.install_button.setEnabled(False)
        self.later_button.setEnabled(False)
        self.status.setText("Téléchargement en cours…")
        self.worker = ModelDownloadWorker(self.destination)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.succeeded.connect(self.complete)
        self.worker.failed.connect(self.failure)
        self.worker.start()

    def complete(self):
        self.status.setText("Modèle installé.")
        self.installed.emit()
        self.accept()

    def failure(self, message):
        self.status.setText(message)
        self.install_button.setEnabled(True)
        self.later_button.setEnabled(True)

    def reject(self):
        if self.worker and self.worker.isRunning():
            return
        super().reject()


class TypoZapApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("TypoZap")
        self.setOrganizationName("TypoZap")
        self.setQuitOnLastWindowClosed(False)

        self.settings = QSettings()
        self.engine = EngineManager()
        self.corrector = self.engine.corrector()
        self.auto_replace = self.settings.value("auto_replace", True, type=bool)
        self.busy = False
        self.transaction = None
        self.worker = None
        self.capture_deadline = 0.0
        self.hotkey_listener = None

        self.capture_timer = QTimer(self)
        self.capture_timer.setInterval(40)
        self.capture_timer.timeout.connect(self.poll_selection)

        self.tray_icon = QSystemTrayIcon(self.create_icon(), self)
        self.tray_icon.setToolTip("TypoZap — correcteur français local")
        self.create_menu()
        self.tray_icon.show()

        self.hotkey_bridge = HotkeyBridge(self)
        self.hotkey_bridge.activated.connect(lambda: self.correct_selected_text("standard"))
        self.setup_hotkey()
        self.aboutToQuit.connect(self.shutdown)

        QTimer.singleShot(400, lambda: self.show_notification(
            "⚡ TypoZap",
            f"Prêt — sélectionnez un texte puis utilisez {hotkey_label()}.",
        ))
        if self.engine.binary.is_file() and not self.engine.embedded_ready and not self.corrector.check_ollama():
            QTimer.singleShot(800, self.offer_model_installation)

    def create_menu(self):
        menu = QMenu()
        for label, key in {
            "Standard": "standard", "Formel": "formel", "Informel": "informel",
            "Concis": "concis", "Détaillé": "détaillé",
        }.items():
            action = QAction(f"⚡ {label}", self)
            action.triggered.connect(lambda checked=False, style=key: self.correct_selected_text(style))
            menu.addAction(action)

        menu.addSeparator()
        self.auto_replace_action = QAction("Remplacement automatique", self, checkable=True)
        self.auto_replace_action.setChecked(self.auto_replace)
        self.auto_replace_action.triggered.connect(self.toggle_auto_replace)
        menu.addAction(self.auto_replace_action)

        status = QAction("Vérifier le moteur local", self)
        status.triggered.connect(self.check_engine_status)
        menu.addAction(status)
        menu.addSeparator()
        quit_action = QAction("Quitter", self)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)

    @staticmethod
    def create_icon():
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(255, 193, 7))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 60, 60)
        painter.setPen(QColor(33, 33, 33))
        painter.setFont(QFont("Arial", 32, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "⚡")
        painter.end()
        return QIcon(pixmap)

    def setup_hotkey(self):
        from pynput import keyboard

        hotkey = keyboard.HotKey(
            keyboard.HotKey.parse(hotkey_spec()),
            self.hotkey_bridge.activated.emit,
        )

        def canonical(callback):
            return lambda key: callback(self.hotkey_listener.canonical(key))

        self.hotkey_listener = keyboard.Listener(
            on_press=canonical(hotkey.press),
            on_release=canonical(hotkey.release),
        )
        self.hotkey_listener.start()

    def correct_selected_text(self, style):
        if self.busy:
            self.show_notification("Correction en cours", "Attendez la fin de la correction actuelle.", warning=True)
            return
        self.busy = True
        self.pending_style = style
        # Laisse le temps aux touches du raccourci global d'être relâchées.
        QTimer.singleShot(120, self.begin_capture)

    def begin_capture(self):
        clipboard = self.clipboard()
        self.transaction = ClipboardTransaction(clipboard)
        clipboard.clear()
        self.empty_fingerprint = clipboard_fingerprint(clipboard)
        pyautogui.hotkey(*copy_shortcut())
        self.capture_deadline = time.monotonic() + 1.5
        self.capture_timer.start()

    def poll_selection(self):
        clipboard = self.clipboard()
        fingerprint = clipboard_fingerprint(clipboard)
        text = clipboard.text()
        if fingerprint != self.empty_fingerprint and text:
            self.capture_timer.stop()
            self.transaction.mark_selection()
            self.start_correction(text)
            return
        if time.monotonic() >= self.capture_deadline:
            self.capture_timer.stop()
            # Ne restaure que si personne n'a placé une nouvelle donnée entre-temps.
            if clipboard_fingerprint(clipboard) == self.empty_fingerprint:
                from clipboard_transaction import restore_snapshot
                restore_snapshot(clipboard, self.transaction.original)
            self.finish_operation()
            self.show_notification("Aucun texte", "Sélectionnez du texte puis réessayez.", warning=True)

    def start_correction(self, text):
        self.show_notification("Correction en cours", f"{len(text)} caractères — style {self.pending_style}")
        self.worker = CorrectionWorker(self.corrector, text, self.pending_style)
        self.worker.succeeded.connect(self.show_result)
        self.worker.failed.connect(self.show_correction_error)
        self.worker.finished.connect(self.correction_thread_finished)
        self.worker.start()

    def correction_thread_finished(self):
        if self.sender() is self.worker:
            self.worker = None

    def show_result(self, original, corrected):
        if not self.transaction.selection_is_unchanged():
            self.finish_operation()
            self.show_notification(
                "Correction annulée",
                "Le presse-papier a changé pendant la correction ; votre nouvelle copie a été conservée.",
                warning=True,
            )
            return

        if not self.auto_replace:
            self.transaction.restore_original_if_selection_unchanged()
            self.finish_operation()
            CorrectionDialog(original, corrected).exec_()
            return

        self.clipboard().setText(corrected)
        self.transaction.mark_corrected()
        pyautogui.hotkey(*paste_shortcut())
        QTimer.singleShot(250, self.restore_after_paste)
        self.show_notification("Texte corrigé", f"{len(original)} → {len(corrected)} caractères")

    def restore_after_paste(self):
        # Une copie faite par l'utilisateur après le collage gagne toujours.
        self.transaction.restore_if_unchanged()
        self.finish_operation()

    def show_correction_error(self, message):
        if self.transaction:
            self.transaction.restore_original_if_selection_unchanged()
        self.finish_operation()
        self.show_notification("Correction impossible", message, warning=True)

    def finish_operation(self):
        self.busy = False
        self.transaction = None

    def toggle_auto_replace(self, enabled):
        self.auto_replace = enabled
        self.settings.setValue("auto_replace", enabled)
        self.show_notification("Réglage enregistré", "Remplacement automatique activé." if enabled else "Aperçu activé.")

    def check_engine_status(self):
        if self.corrector.check_ollama():
            source = "moteur embarqué" if self.engine.process else "Ollama"
            self.show_notification("Moteur disponible", f"TypoZap utilise le {source}.")
        else:
            self.show_notification("Moteur indisponible", "Installez le modèle ou démarrez Ollama.", warning=True)

    def offer_model_installation(self):
        dialog = FirstRunDialog(self.engine.model)
        dialog.installed.connect(self.activate_embedded_engine)
        dialog.exec_()

    def activate_embedded_engine(self):
        corrector = self.engine.start()
        if corrector:
            self.corrector = corrector
            self.show_notification("Installation terminée", "Le moteur français local est prêt.")
        else:
            self.show_notification("Moteur incomplet", "Le moteur local TypoZap est absent.", warning=True)

    def show_notification(self, title, message, warning=False):
        tray_icon = getattr(self, "tray_icon", None)
        if tray_icon is None:
            return
        icon = QSystemTrayIcon.Warning if warning else QSystemTrayIcon.Information
        tray_icon.showMessage(title, message, icon, 3500)

    def shutdown(self):
        capture_timer = getattr(self, "capture_timer", None)
        if capture_timer:
            capture_timer.stop()
        hotkey_listener = getattr(self, "hotkey_listener", None)
        if hotkey_listener:
            hotkey_listener.stop()
        engine = getattr(self, "engine", None)
        if engine:
            engine.stop()


def main():
    app = TypoZapApp(sys.argv)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
