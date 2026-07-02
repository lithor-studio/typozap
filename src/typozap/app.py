"""Interface de barre de menus et orchestration des corrections TypoZap.

La logique linguistique reste dans ``correctors`` : ce module coordonne Qt,
le raccourci global, le presse-papier et le moteur local.
"""

import difflib
import sys
import time
import traceback

import pyautogui
from PyQt5.QtCore import QObject, QPoint, QSettings, QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QKeySequence, QPainter, QPixmap, QPolygon
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QPlainTextEdit,
    QKeySequenceEdit,
    QSystemTrayIcon,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
)

from typozap.clipboard import ClipboardTransaction
from typozap.correctors import CorrectionError
from typozap.engine import EngineManager
from typozap.features import (
    Metrics, SecureHistory, active_window_title, process_memory_mb,
    style_for_window, technical_logger,
)
from typozap.model_installer import ModelInstallError, download_model
from typozap.platform import copy_shortcut, default_hotkey_sequence, hotkey_spec_from_label, paste_shortcut
from typozap.platform import HotkeyMatcher


class HotkeyBridge(QObject):
    """Transforme le callback pynput en signal sûr pour le thread principal Qt."""
    activated = pyqtSignal()


class HotkeyDialog(QDialog):
    """Permet de choisir et valider le raccourci global."""

    def __init__(self, current, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurer le raccourci")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Cliquez dans le champ puis saisissez le nouveau raccourci :"))
        self.editor = QKeySequenceEdit(QKeySequence(current))
        layout.addWidget(self.editor)
        buttons = QHBoxLayout()
        save = QPushButton("Enregistrer")
        save.clicked.connect(self.validate)
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def sequence(self):
        return self.editor.keySequence().toString(QKeySequence.PortableText)

    def validate(self):
        try:
            hotkey_spec_from_label(self.sequence())
        except ValueError as exc:
            QMessageBox.warning(self, "Raccourci invalide", str(exc))
            return
        self.accept()


class CorrectionDialog(QDialog):
    """Affiche les différences avant application."""
    def __init__(self, original_text, corrected_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TypoZap - Aperçu")
        self.resize(760, 520)
        self.corrected_text = corrected_text
        self.segments = []
        self.change_items = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Comparaison des modifications :"))
        comparison = QTextBrowser()
        table = difflib.HtmlDiff(wrapcolumn=90).make_table(
            original_text.splitlines() or [original_text],
            corrected_text.splitlines() or [corrected_text],
            "Original", "Correction", context=True, numlines=2,
        )
        comparison.setHtml(table)
        layout.addWidget(comparison)
        layout.addWidget(QLabel("Modifications (décochez celles à refuser) :"))
        changes = QListWidget()
        original_tokens = self.tokenize(original_text)
        corrected_tokens = self.tokenize(corrected_text)
        matcher = difflib.SequenceMatcher(a=original_tokens, b=corrected_tokens)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            old = "".join(original_tokens[i1:i2])
            new = "".join(corrected_tokens[j1:j2])
            if tag == "equal":
                self.segments.append(("equal", old))
                continue
            item = QListWidgetItem(f"{old or '∅'}  →  {new or '∅'}")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            changes.addItem(item)
            index = len(self.change_items)
            self.change_items.append((item, old, new))
            self.segments.append(("change", index))
        if not self.change_items:
            changes.addItem("Aucune modification détectée")
        layout.addWidget(changes)

        buttons = QHBoxLayout()
        copy_button = QPushButton("Copier le résultat")
        copy_button.clicked.connect(self.copy_result)
        apply_button = QPushButton("Appliquer")
        apply_button.clicked.connect(self.accept)
        close_button = QPushButton("Annuler")
        close_button.clicked.connect(self.reject)
        buttons.addWidget(copy_button)
        buttons.addWidget(apply_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def copy_result(self):
        QApplication.clipboard().setText(self.result_text())
        QMessageBox.information(self, "Copié", "Le texte corrigé a été copié.")

    @staticmethod
    def tokenize(text):
        import re
        return re.findall(r"\s+|[\wÀ-ÿ]+|[^\w\s]", text, flags=re.UNICODE)

    def result_text(self):
        output = []
        for kind, value in self.segments:
            if kind == "equal":
                output.append(value)
            else:
                item, old, new = self.change_items[value]
                output.append(new if item.checkState() == Qt.Checked else old)
        return "".join(output)


class PreferencesDialog(QDialog):
    """Réglages locaux de correction et de confidentialité."""

    STYLES = ["standard", "formel", "informel", "concis", "détaillé"]

    def __init__(self, settings, history_available, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Préférences TypoZap")
        self.resize(620, 540)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        writing = QDialog()
        form = QFormLayout(writing)
        self.default_style = QComboBox()
        self.default_style.addItems(self.STYLES)
        self.default_style.setCurrentText(settings.value("writing/default_style", "standard", type=str))
        self.strict = QCheckBox("Interdire toute reformulation")
        self.strict.setChecked(settings.value("writing/strict", False, type=bool))
        self.tone = QLineEdit(settings.value("writing/tone", "", type=str))
        self.dictionary = QPlainTextEdit(settings.value("writing/dictionary", "", type=str))
        self.dictionary.setPlaceholderText("Un terme protégé par ligne")
        self.guide = QPlainTextEdit(settings.value("writing/style_guide", "", type=str))
        self.guide.setPlaceholderText("Ex. Toujours vouvoyer ; écrire « e-mail ».")
        form.addRow("Style par défaut", self.default_style)
        form.addRow("Mode strict", self.strict)
        form.addRow("Ton personnalisé", self.tone)
        form.addRow("Dictionnaire personnel", self.dictionary)
        form.addRow("Guide de style", self.guide)
        tabs.addTab(writing, "Écriture")

        apps = QDialog()
        apps_layout = QVBoxLayout(apps)
        apps_layout.addWidget(QLabel(
            "Un profil par ligne au format texte-présent-dans-le-titre=style.\n"
            "Exemples : Teams=informel, Outlook=formel"
        ))
        self.profiles = QPlainTextEdit(settings.value("writing/profiles", "Teams=informel\nOutlook=formel", type=str))
        apps_layout.addWidget(self.profiles)
        tabs.addTab(apps, "Applications")

        privacy = QDialog()
        privacy_layout = QVBoxLayout(privacy)
        self.show_diff = QCheckBox("Toujours afficher les différences avant remplacement")
        self.show_diff.setChecked(settings.value("ui/show_diff", False, type=bool))
        self.history_enabled = QCheckBox("Conserver les 20 dernières corrections chiffrées")
        self.history_enabled.setEnabled(history_available)
        self.history_enabled.setChecked(history_available and settings.value("history/enabled", False, type=bool))
        privacy_layout.addWidget(self.show_diff)
        privacy_layout.addWidget(self.history_enabled)
        privacy_layout.addWidget(QLabel(
            "L'historique est désactivé par défaut et protégé par le compte Windows (DPAPI). "
            "Le journal technique ne contient jamais les textes."
        ))
        tabs.addTab(privacy, "Confidentialité")
        layout.addWidget(tabs)

        buttons = QHBoxLayout()
        save = QPushButton("Enregistrer")
        save.clicked.connect(self.save)
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def save(self):
        values = {
            "writing/default_style": self.default_style.currentText(),
            "writing/strict": self.strict.isChecked(),
            "writing/tone": self.tone.text().strip(),
            "writing/dictionary": self.dictionary.toPlainText().strip(),
            "writing/style_guide": self.guide.toPlainText().strip(),
            "writing/profiles": self.profiles.toPlainText().strip(),
            "ui/show_diff": self.show_diff.isChecked(),
            "history/enabled": self.history_enabled.isChecked(),
        }
        for key, value in values.items():
            self.settings.setValue(key, value)
        self.accept()


class CorrectionWorker(QThread):
    """Exécute l'inférence hors du thread graphique."""
    succeeded = pyqtSignal(str, str)
    failed = pyqtSignal(str)

    def __init__(self, corrector, text, style, options, parent=None):
        super().__init__(parent)
        self.corrector = corrector
        self.text = text
        self.style = style
        self.options = options

    def run(self):
        try:
            self.succeeded.emit(self.text, self.corrector.correct_text(self.text, self.style, self.options))
        except CorrectionError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # La boucle graphique ne doit jamais tomber avec le moteur.
            self.failed.emit(f"Erreur inattendue : {exc}")


class ExplanationWorker(QThread):
    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, corrector, original, corrected, parent=None):
        super().__init__(parent)
        self.corrector, self.original, self.corrected = corrector, original, corrected

    def run(self):
        try:
            self.succeeded.emit(self.corrector.explain_correction(self.original, self.corrected))
        except Exception as exc:
            self.failed.emit(str(exc))


class ModelDownloadWorker(QThread):
    """Télécharge le modèle sans figer l'interface."""
    progress = pyqtSignal(int)
    succeeded = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, destination, parent=None):
        super().__init__(parent)
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
        except Exception as exc:
            self.failed.emit(f"Installation impossible : {exc}")


class FirstRunDialog(QDialog):
    """Assistant de téléchargement affiché au premier lancement."""
    installed = pyqtSignal()

    def __init__(self, destination, parent=None):
        super().__init__(parent)
        self.destination = destination
        self.worker = None
        model_exists = self.destination.exists()
        self.setWindowTitle("Vérifier le modèle français" if model_exists else "Installer le modèle français")
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
        self.status = QLabel(
            f"Modèle détecté dans :\n{self.destination}\nUne vérification d'intégrité sera effectuée."
            if model_exists else f"Le modèle sera stocké dans :\n{self.destination}"
        )
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.install_button = QPushButton("Vérifier et réparer" if model_exists else "Télécharger et installer")
        self.install_button.clicked.connect(self.install)
        self.later_button = QPushButton("Plus tard")
        self.later_button.clicked.connect(self.reject)
        buttons.addWidget(self.install_button)
        buttons.addWidget(self.later_button)
        layout.addLayout(buttons)

    def install(self):
        self.install_button.setEnabled(False)
        self.later_button.setEnabled(False)
        self.status.setText("Vérification puis réparation si nécessaire…")
        self.worker = ModelDownloadWorker(self.destination, self)
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
    """Application de barre de menus et propriétaire de son cycle de vie."""
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("TypoZap")
        self.setOrganizationName("TypoZap")
        self.setQuitOnLastWindowClosed(False)

        self.settings = QSettings()
        self.hotkey = self.settings.value("hotkey", default_hotkey_sequence(), type=str)
        try:
            hotkey_spec_from_label(self.hotkey)
        except ValueError:
            self.hotkey = default_hotkey_sequence()
            self.settings.setValue("hotkey", self.hotkey)
        self.engine = EngineManager()
        self.corrector = self.engine.corrector()
        self.logger = technical_logger()
        self.metrics = Metrics(self.settings)
        self.history = SecureHistory()
        self.auto_replace = self.settings.value("auto_replace", True, type=bool)
        self.busy = False
        self.transaction = None
        self.worker = None
        self.capture_deadline = 0.0
        self.hotkey_listener = None
        self.active_title = ""
        self.correction_started = 0.0
        self.last_correction = None
        self.explanation_worker = None
        self.retired_workers = []
        sys.excepthook = self.handle_unhandled_exception

        self.capture_timer = QTimer(self)
        self.capture_timer.setInterval(40)
        self.capture_timer.timeout.connect(self.poll_selection)

        self.tray_icon = QSystemTrayIcon(self.create_icon(), self)
        self.tray_icon.setToolTip("TypoZap — correcteur français local")
        self.create_menu()
        self.tray_icon.show()

        self.hotkey_bridge = HotkeyBridge(self)
        self.hotkey_bridge.activated.connect(lambda: self.correct_selected_text(None))
        self.setup_hotkey()
        self.aboutToQuit.connect(self.shutdown)

        QTimer.singleShot(400, lambda: self.show_notification(
            "⚡ TypoZap",
            f"Prêt — sélectionnez un texte puis utilisez {self.hotkey}.",
        ))
        if self.engine.binary.is_file() and not self.engine.embedded_ready:
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

        self.undo_action = QAction("Annuler la dernière correction", self)
        self.undo_action.setEnabled(False)
        self.undo_action.triggered.connect(self.undo_last_correction)
        menu.addAction(self.undo_action)
        self.explain_action = QAction("Expliquer la dernière correction", self)
        self.explain_action.setEnabled(False)
        self.explain_action.triggered.connect(self.explain_last_correction)
        menu.addAction(self.explain_action)

        preferences = QAction("Préférences d'écriture…", self)
        preferences.triggered.connect(self.configure_preferences)
        menu.addAction(preferences)
        history = QAction("Historique local…", self)
        history.triggered.connect(self.show_history)
        menu.addAction(history)
        statistics = QAction("Statistiques…", self)
        statistics.triggered.connect(self.show_statistics)
        menu.addAction(statistics)

        status = QAction("Vérifier le moteur local", self)
        status.triggered.connect(self.check_engine_status)
        menu.addAction(status)
        install = QAction("Installer ou réparer le modèle", self)
        install.triggered.connect(self.offer_model_installation)
        menu.addAction(install)
        self.shortcut_action = QAction(f"Configurer le raccourci… ({self.hotkey})", self)
        self.shortcut_action.triggered.connect(self.configure_hotkey)
        menu.addAction(self.shortcut_action)
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
        painter.setBrush(QColor(33, 33, 33))
        painter.drawPolygon(QPolygon([
            QPoint(36, 10), QPoint(18, 35), QPoint(29, 35),
            QPoint(25, 54), QPoint(47, 27), QPoint(35, 27),
        ]))
        painter.end()
        return QIcon(pixmap)

    def setup_hotkey(self):
        from pynput import keyboard

        old_listener = self.hotkey_listener
        self.hotkey_listener = None
        if old_listener:
            old_listener.stop()
            try:
                old_listener.join(1)
            except RuntimeError:
                pass
        try:
            required = keyboard.HotKey.parse(hotkey_spec_from_label(self.hotkey))
            matcher = HotkeyMatcher(required, self.emit_hotkey)
            listener = None

            def on_press(key):
                try:
                    matcher.press(listener.canonical(key))
                except Exception as exc:
                    self.logger.error("hotkey_press_failed type=%s", type(exc).__name__)

            def on_release(key):
                try:
                    matcher.release(listener.canonical(key))
                except Exception as exc:
                    self.logger.error("hotkey_release_failed type=%s", type(exc).__name__)

            listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            listener.start()
            self.hotkey_listener = listener
            self.logger.info("hotkey_listener_started shortcut=%s", self.hotkey)
            return True
        except Exception as exc:
            self.logger.error("hotkey_listener_failed type=%s", type(exc).__name__)
            self.show_notification("Raccourci indisponible", str(exc), warning=True)
            return False

    def emit_hotkey(self):
        self.logger.info("hotkey_activated shortcut=%s", self.hotkey)
        self.hotkey_bridge.activated.emit()

    def configure_hotkey(self):
        dialog = HotkeyDialog(self.hotkey)
        if dialog.exec_() != QDialog.Accepted:
            return
        new_hotkey = dialog.sequence()
        try:
            hotkey_spec_from_label(new_hotkey)
        except ValueError as exc:
            self.show_notification("Raccourci invalide", str(exc), warning=True)
            return
        self.hotkey = new_hotkey
        self.settings.setValue("hotkey", new_hotkey)
        self.settings.sync()
        # Laisse Qt et le système relâcher les touches utilisées dans l'éditeur.
        QTimer.singleShot(200, self.activate_new_hotkey)

    def activate_new_hotkey(self):
        if self.setup_hotkey():
            self.shortcut_action.setText(f"Configurer le raccourci… ({self.hotkey})")
            self.show_notification("Raccourci enregistré", f"Nouveau raccourci : {self.hotkey}")

    def correct_selected_text(self, style):
        if self.busy:
            self.show_notification("Correction en cours", "Attendez la fin de la correction actuelle.", warning=True)
            return
        if self.corrector is None or not self.corrector.is_ready():
            if not self.engine.binary.is_file():
                message = "Le moteur TypoZap est absent de l'application. Reconstruisez l'exécutable avec le runtime."
            elif not self.engine.model.is_file():
                message = "Le modèle Ministral n'est pas installé."
            else:
                message = "Le moteur n'a pas pu démarrer. Utilisez « Installer ou réparer le modèle »."
            self.show_notification(
                "Moteur indisponible",
                message,
                warning=True,
            )
            if self.engine.binary.is_file() and not self.engine.embedded_ready:
                QTimer.singleShot(0, self.offer_model_installation)
            return
        self.busy = True
        self.active_title = active_window_title()
        default_style = self.settings.value("writing/default_style", "standard", type=str)
        self.pending_style = style or style_for_window(self.active_title, self.application_profiles(), default_style)
        # Laisse le temps aux touches du raccourci global d'être relâchées.
        QTimer.singleShot(120, self.begin_capture)

    def begin_capture(self):
        # Sauvegarder avant la copie permet de restaurer texte, HTML et fichiers.
        clipboard = self.clipboard()
        self.transaction = ClipboardTransaction(clipboard)
        self.transaction.begin_capture()
        pyautogui.hotkey(*copy_shortcut())
        self.capture_deadline = time.monotonic() + 1.5
        self.capture_timer.start()

    def poll_selection(self):
        clipboard = self.clipboard()
        text = clipboard.text()
        if not self.transaction.capture_is_pending() and text:
            self.capture_timer.stop()
            self.transaction.mark_selection()
            self.start_correction(text)
            return
        if time.monotonic() >= self.capture_deadline:
            self.capture_timer.stop()
            # Ne restaure que si personne n'a placé une nouvelle donnée entre-temps.
            if self.transaction.capture_is_pending():
                self.transaction.restore_original_if_capture_pending()
            self.finish_operation()
            self.show_notification("Aucun texte", "Sélectionnez du texte puis réessayez.", warning=True)

    def start_correction(self, text):
        self.show_notification("Correction en cours", f"{len(text)} caractères — style {self.pending_style}")
        self.correction_started = time.monotonic()
        self.worker = CorrectionWorker(
            self.corrector, text, self.pending_style, self.correction_options(), self
        )
        self.worker.succeeded.connect(self.show_result)
        self.worker.failed.connect(self.show_correction_error)
        self.worker.finished.connect(self.correction_thread_finished)
        self.worker.start()

    def correction_thread_finished(self):
        worker = self.sender()
        if worker is None:
            return
        # Ne jamais détruire un QThread pendant l'émission de son signal finished.
        self.retired_workers.append(worker)
        QTimer.singleShot(0, lambda current=worker: self.release_worker(current))

    def release_worker(self, worker):
        if self.worker is worker:
            self.worker = None
        if self.explanation_worker is worker:
            self.explanation_worker = None
        if worker in self.retired_workers:
            self.retired_workers.remove(worker)
        worker.deleteLater()

    def show_result(self, original, corrected):
        # Une copie faite par l'utilisateur pendant l'inférence reste prioritaire.
        if not self.transaction.selection_is_unchanged():
            self.finish_operation()
            self.show_notification(
                "Correction annulée",
                "Le presse-papier a changé pendant la correction ; votre nouvelle copie a été conservée.",
                warning=True,
            )
            return

        duration = time.monotonic() - self.correction_started
        self.metrics.record(duration, len(original))
        self.logger.info("correction_ok style=%s chars=%d duration_ms=%d chunks_possible=%s",
                         self.pending_style, len(original), int(duration * 1000), len(original) > 6000)
        if not self.auto_replace or self.settings.value("ui/show_diff", False, type=bool):
            dialog = CorrectionDialog(original, corrected)
            if dialog.exec_() == QDialog.Accepted and self.transaction.selection_is_unchanged():
                reviewed = dialog.result_text()
                QTimer.singleShot(150, lambda: self.apply_result(original, reviewed))
            else:
                self.transaction.restore_original_if_selection_unchanged()
                self.finish_operation()
            return

        self.apply_result(original, corrected)

    def apply_result(self, original, corrected):
        if not self.transaction or not self.transaction.selection_is_unchanged():
            self.finish_operation()
            self.show_notification("Correction annulée", "La sélection ou le presse-papier a changé.", warning=True)
            return
        self.last_correction = (original, corrected, time.monotonic(), self.active_title)
        self.undo_action.setEnabled(True)
        self.explain_action.setEnabled(True)
        if self.settings.value("history/enabled", False, type=bool) and self.history.available:
            try:
                self.history.add(original, corrected, self.pending_style)
            except Exception as exc:
                self.logger.error("history_write_failed type=%s", type(exc).__name__)
        self.transaction.set_corrected_text(corrected)
        pyautogui.hotkey(*paste_shortcut())
        transaction = self.transaction
        QTimer.singleShot(500, lambda: self.restore_after_paste(transaction))
        self.show_notification("Texte corrigé", f"{len(original)} → {len(corrected)} caractères")

    def restore_after_paste(self, transaction):
        # Une copie faite par l'utilisateur après le collage gagne toujours.
        transaction.restore_if_unchanged()
        if self.transaction is transaction:
            self.finish_operation()

    def show_correction_error(self, message):
        if self.transaction:
            self.transaction.restore_original_if_selection_unchanged()
        self.finish_operation()
        self.logger.error("correction_failed error=%s", message[:200].replace("\n", " "))
        self.show_notification("Correction impossible", message, warning=True)

    def application_profiles(self):
        profiles = {}
        raw = self.settings.value("writing/profiles", "Teams=informel\nOutlook=formel", type=str)
        for line in raw.splitlines():
            if "=" not in line:
                continue
            pattern, style = (part.strip() for part in line.split("=", 1))
            if pattern and style in PreferencesDialog.STYLES:
                profiles[pattern] = style
        return profiles

    def correction_options(self):
        return {
            "strict": self.settings.value("writing/strict", False, type=bool),
            "tone": self.settings.value("writing/tone", "", type=str),
            "dictionary": self.settings.value("writing/dictionary", "", type=str).splitlines(),
            "style_guide": self.settings.value("writing/style_guide", "", type=str),
        }

    def configure_preferences(self):
        PreferencesDialog(self.settings, self.history.available).exec_()

    def undo_last_correction(self):
        if not self.last_correction or time.monotonic() - self.last_correction[2] > 60:
            self.undo_action.setEnabled(False)
            self.show_notification("Annulation expirée", "La correction date de plus d'une minute.", warning=True)
            return
        current_title = active_window_title()
        if current_title and self.last_correction[3] and current_title != self.last_correction[3]:
            self.show_notification(
                "Annulation protégée", "Revenez dans l'application corrigée puis réessayez.", warning=True
            )
            return
        pyautogui.hotkey("ctrl" if sys.platform != "darwin" else "command", "z")
        self.undo_action.setEnabled(False)
        self.show_notification("Annulation envoyée", "Le document actif a reçu la commande Annuler.")

    def explain_last_correction(self):
        if not self.last_correction or self.explanation_worker:
            return
        original, corrected, _, _ = self.last_correction
        self.explanation_worker = ExplanationWorker(self.corrector, original, corrected, self)
        self.explanation_worker.succeeded.connect(self.show_explanation)
        self.explanation_worker.failed.connect(lambda message: QMessageBox.warning(None, "Explication impossible", message))
        self.explanation_worker.finished.connect(self.correction_thread_finished)
        self.explanation_worker.start()
        self.show_notification("Explication", "Analyse locale en cours…")

    def show_explanation(self, explanation):
        QMessageBox.information(None, "Pourquoi ces corrections ?", explanation)

    def show_statistics(self):
        count, chars, average = self.metrics.summary()
        state = "prêt" if self.corrector and self.corrector.is_ready() else "indisponible"
        memory = process_memory_mb(self.engine.process.pid if self.engine.process else None)
        memory_line = f"\nMémoire du moteur : {memory:.0f} Mo" if memory is not None else ""
        QMessageBox.information(
            None, "Statistiques TypoZap",
            f"Moteur : {state}\nModèle : Ministral 3 3B\nCorrections : {count}\n"
            f"Caractères traités : {chars}\nDurée moyenne : {average:.1f} s{memory_line}",
        )

    def show_history(self):
        if not self.history.available:
            QMessageBox.information(None, "Historique", "Le chiffrement système n'est pas disponible sur cette plateforme.")
            return
        entries = self.history.load()
        dialog = QDialog()
        dialog.setWindowTitle("Historique local chiffré")
        dialog.resize(700, 440)
        layout = QVBoxLayout(dialog)
        listing = QListWidget()
        details = QTextEdit()
        details.setReadOnly(True)
        for entry in entries:
            preview = entry.get("corrected", "").replace("\n", " ")[:100]
            listing.addItem(f"{entry.get('date', '')[:16]} · {entry.get('style', '')} · {preview}")
        layout.addWidget(listing)
        layout.addWidget(details)
        def show_entry(row):
            if 0 <= row < len(entries):
                entry = entries[row]
                details.setPlainText(
                    "Original :\n" + entry.get("original", "") +
                    "\n\nCorrection :\n" + entry.get("corrected", "")
                )
        listing.currentRowChanged.connect(show_entry)
        buttons = QHBoxLayout()
        clear = QPushButton("Tout effacer")
        clear.clicked.connect(lambda: (self.history.clear(), listing.clear(), details.clear()))
        close = QPushButton("Fermer")
        close.clicked.connect(dialog.accept)
        buttons.addWidget(clear)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        dialog.exec_()

    def finish_operation(self):
        self.busy = False
        self.transaction = None

    def toggle_auto_replace(self, enabled):
        self.auto_replace = enabled
        self.settings.setValue("auto_replace", enabled)
        self.show_notification("Réglage enregistré", "Remplacement automatique activé." if enabled else "Aperçu activé.")

    def check_engine_status(self):
        if self.corrector and self.corrector.is_ready():
            self.show_notification("Moteur disponible", "Ministral 3 3B est prêt.")
        else:
            if not self.engine.binary.is_file():
                message = "Runtime llama.cpp absent de l'application."
            elif not self.engine.model.is_file():
                message = "Modèle Ministral absent."
            else:
                message = "Modèle présent, mais moteur impossible à démarrer. Lancez une réparation."
            self.show_notification("Moteur indisponible", message, warning=True)

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

    def handle_unhandled_exception(self, exception_type, exception, exception_traceback):
        details = "".join(traceback.format_exception(exception_type, exception, exception_traceback))
        self.logger.critical("unhandled_exception\n%s", details)
        self.show_notification(
            "Erreur TypoZap",
            "Une erreur interne a été enregistrée. L'application reste active.",
            warning=True,
        )

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
        for worker in [getattr(self, "worker", None), getattr(self, "explanation_worker", None)]:
            if worker and worker.isRunning():
                worker.requestInterruption()
                worker.wait(3000)


def main():
    app = TypoZapApp(sys.argv)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
