import sys
import pyperclip
import pyautogui
import time
import language_tool_python
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QAction, 
                             QDialog, QVBoxLayout, QTextEdit, QPushButton, 
                             QLabel, QHBoxLayout, QMessageBox)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal


class CorrectionDialog(QDialog):
    def __init__(self, original_text, corrected_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TypoZap - Aperçu")
        self.setGeometry(300, 300, 600, 400)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Texte original:"))
        self.original_edit = QTextEdit()
        self.original_edit.setPlainText(original_text)
        self.original_edit.setReadOnly(True)
        self.original_edit.setMaximumHeight(150)
        layout.addWidget(self.original_edit)
        
        layout.addWidget(QLabel("Texte corrigé:"))
        self.corrected_edit = QTextEdit()
        self.corrected_edit.setPlainText(corrected_text)
        self.corrected_edit.setReadOnly(True)
        layout.addWidget(self.corrected_edit)
        
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("Copier dans le presse-papier")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(copy_btn)
        
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        self.corrected_text = corrected_text
    
    def copy_to_clipboard(self):
        pyperclip.copy(self.corrected_text)
        QMessageBox.information(self, "Copié", "Le texte a été copié dans le presse-papier!")


class LocalCorrector:
    def __init__(self):
        try:
            self.tool = language_tool_python.LanguageTool('fr-FR')
            self.available = True
        except Exception as e:
            print(f"Erreur d'initialisation LanguageTool: {e}")
            self.available = False
    
    def check_status(self):
        return self.available
    
    def correct_text(self, text, style="standard"):
        if not self.available:
            return "Erreur: Correcteur non disponible"
        
        try:
            matches = self.tool.check(text)
            corrected = language_tool_python.utils.correct(text, matches)
            
            if style == "formel":
                corrected = self.apply_formal_style(corrected)
            elif style == "informel":
                corrected = self.apply_informal_style(corrected)
            elif style == "concis":
                corrected = self.make_concise(corrected)
            
            return corrected
        except Exception as e:
            return f"Erreur de correction: {str(e)}"
    
    def apply_formal_style(self, text):
        replacements = {
            " c'est ": " cela est ",
            " t'as ": " tu as ",
            " j'ai ": " j'ai ",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    def apply_informal_style(self, text):
        text = text.replace(" cela est ", " c'est ")
        text = text.replace(" vous ", " tu ")
        return text
    
    def make_concise(self, text):
        import re
        words_to_remove = [" vraiment ", " en fait ", " donc ", " alors ", " très "]
        for word in words_to_remove:
            text = text.replace(word, " ")
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


class CorrectionWorker(QThread):
    finished = pyqtSignal(str, str)
    
    def __init__(self, corrector, text, style):
        super().__init__()
        self.corrector = corrector
        self.text = text
        self.style = style
    
    def run(self):
        corrected = self.corrector.correct_text(self.text, self.style)
        self.finished.emit(self.text, corrected)


class ClipboardWorker(QThread):
    finished = pyqtSignal(str, str, str)
    
    def __init__(self, style, old_clipboard):
        super().__init__()
        self.style = style
        self.old_clipboard = old_clipboard
    
    def run(self):
        self.msleep(400)
        text = pyperclip.paste()
        self.finished.emit(text, self.style, self.old_clipboard)


class TypoZapApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.corrector = LocalCorrector()
        self.auto_replace = True
        self.original_clipboard = ""
        
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.create_icon())
        
        self.menu = QMenu()
        
        self.styles = {
            "Standard": "standard",
            "Formel": "formel",
            "Informel": "informel",
            "Concis": "concis",
        }
        
        for style_name, style_key in self.styles.items():
            action = QAction(f"⚡ {style_name}", self)
            action.triggered.connect(lambda checked, s=style_key: self.correct_selected_text(s))
            self.menu.addAction(action)
        
        self.menu.addSeparator()
        
        self.auto_replace_action = QAction("✓ Remplacement automatique", self)
        self.auto_replace_action.setCheckable(True)
        self.auto_replace_action.setChecked(True)
        self.auto_replace_action.triggered.connect(self.toggle_auto_replace)
        self.menu.addAction(self.auto_replace_action)
        
        self.menu.addSeparator()
        
        check_action = QAction("🔍 Vérifier le correcteur", self)
        check_action.triggered.connect(self.check_corrector_status)
        self.menu.addAction(check_action)
        
        quit_action = QAction("❌ Quitter", self)
        quit_action.triggered.connect(self.quit)
        self.menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()
        
        startup_msg = "Prêt ! Ctrl+Shift+C pour zapper les fautes."
        if not self.corrector.check_status():
            startup_msg = "⚠️ Erreur d'initialisation du correcteur"
        
        self.tray_icon.showMessage(
            "⚡ TypoZap Standalone",
            startup_msg,
            QSystemTrayIcon.Information,
            3000
        )
        
        self.setup_hotkey()
    
    def create_icon(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        painter.setBrush(QColor(255, 193, 7))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 60, 60)
        
        painter.setPen(QColor(33, 33, 33))
        font = QFont("Arial", 32, QFont.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "⚡")
        
        painter.end()
        
        return QIcon(pixmap)
    
    def setup_hotkey(self):
        from pynput import keyboard
        
        def on_activate():
            self.correct_selected_text("standard")
        
        hotkey = keyboard.HotKey(
            keyboard.HotKey.parse('<ctrl>+<shift>+c'),
            on_activate
        )
        
        def for_canonical(f):
            return lambda k: f(keyboard_listener.canonical(k))
        
        keyboard_listener = keyboard.Listener(
            on_press=for_canonical(hotkey.press),
            on_release=for_canonical(hotkey.release)
        )
        
        keyboard_listener.start()
    
    def correct_selected_text(self, style):
        self.original_clipboard = pyperclip.paste()
        pyperclip.copy("")
        time.sleep(0.05)
        pyautogui.hotkey('ctrl', 'c')
        
        self.clipboard_worker = ClipboardWorker(style, self.original_clipboard)
        self.clipboard_worker.finished.connect(self.process_clipboard_text)
        self.clipboard_worker.start()
    
    def process_clipboard_text(self, text, style, old_clipboard):
        if not text or text == "":
            self.tray_icon.showMessage(
                "⚠️ Aucun texte",
                "Sélectionnez du texte puis Ctrl+Shift+C",
                QSystemTrayIcon.Warning,
                3000
            )
            pyperclip.copy(old_clipboard)
            return
        
        if text == old_clipboard and old_clipboard != "":
            self.tray_icon.showMessage(
                "⚠️ Même texte",
                "Sélectionnez un nouveau texte",
                QSystemTrayIcon.Warning,
                2000
            )
            return
        
        self.tray_icon.showMessage(
            "⚡ Zap en cours...",
            f"{len(text)} caractères • Style: {style}",
            QSystemTrayIcon.Information,
            2000
        )
        
        self.correction_worker = CorrectionWorker(self.corrector, text, style)
        self.correction_worker.finished.connect(self.show_result)
        self.correction_worker.start()
    
    def show_result(self, original, corrected):
        if self.auto_replace:
            pyperclip.copy("")
            time.sleep(0.05)
            pyperclip.copy(corrected)
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.1)
            
            if self.original_clipboard:
                pyperclip.copy(self.original_clipboard)
            
            self.tray_icon.showMessage(
                "✅ Zappé !",
                f"{len(original)} → {len(corrected)} caractères",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            dialog = CorrectionDialog(original, corrected)
            dialog.exec_()
    
    def toggle_auto_replace(self):
        self.auto_replace = self.auto_replace_action.isChecked()
        if self.auto_replace:
            self.auto_replace_action.setText("✓ Remplacement automatique")
            self.tray_icon.showMessage(
                "✅ Auto activé",
                "Les fautes seront zappées automatiquement",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            self.auto_replace_action.setText("  Remplacement automatique")
            self.tray_icon.showMessage(
                "👁️ Aperçu activé",
                "Vous verrez le texte avant remplacement",
                QSystemTrayIcon.Information,
                2000
            )
    
    def check_corrector_status(self):
        if self.corrector.check_status():
            self.tray_icon.showMessage(
                "✅ Correcteur OK",
                "LanguageTool est opérationnel",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            self.tray_icon.showMessage(
                "❌ Correcteur indisponible",
                "Erreur d'initialisation de LanguageTool",
                QSystemTrayIcon.Warning,
                3000
            )


def main():
    app = TypoZapApp(sys.argv)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()