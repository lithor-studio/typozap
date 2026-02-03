import sys
import requests
import pyperclip
import pyautogui
import time
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


class OllamaCorrector:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.model = "llama3.2"
    
    def check_ollama(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def correct_text(self, text, style="standard"):
        prompts = {
            "standard": f"Corrige les fautes d'orthographe et de grammaire dans le texte suivant. Retourne uniquement le texte corrigé sans aucune explication:\n\n{text}",
            "formel": f"Corrige et reformule ce texte dans un style formel et professionnel. Retourne uniquement le texte corrigé:\n\n{text}",
            "informel": f"Corrige et reformule ce texte dans un style décontracté et amical. Retourne uniquement le texte corrigé:\n\n{text}",
            "concis": f"Corrige et rends ce texte plus concis et direct. Retourne uniquement le texte corrigé:\n\n{text}",
            "détaillé": f"Corrige et enrichis ce texte avec plus de détails et d'explications. Retourne uniquement le texte corrigé:\n\n{text}"
        }
        
        prompt = prompts.get(style, prompts["standard"])
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                return f"Erreur: {response.status_code}"
        except Exception as e:
            return f"Erreur de connexion: {str(e)}"


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
        self.corrector = OllamaCorrector()
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
            "Détaillé": "détaillé"
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
        
        check_action = QAction("🔍 Vérifier Ollama", self)
        check_action.triggered.connect(self.check_ollama_status)
        self.menu.addAction(check_action)
        
        quit_action = QAction("❌ Quitter", self)
        quit_action.triggered.connect(self.quit)
        self.menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()
        
        self.tray_icon.showMessage(
            "⚡ TypoZap",
            "Prêt ! Ctrl+Shift+C pour zapper les fautes instantanément.",
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
    
    def check_ollama_status(self):
        if self.corrector.check_ollama():
            self.tray_icon.showMessage(
                "✅ Ollama OK",
                "Le service est opérationnel",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            self.tray_icon.showMessage(
                "❌ Ollama indisponible",
                "Démarrez Ollama pour utiliser TypoZap",
                QSystemTrayIcon.Warning,
                3000
            )


def main():
    app = TypoZapApp(sys.argv)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()