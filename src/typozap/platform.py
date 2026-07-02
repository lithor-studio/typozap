"""Raccourcis propres à Windows et macOS, sans dépendance graphique."""

import platform
import re


class HotkeyMatcher:
    """Détecteur minimal réarmé uniquement après relâchement de la combinaison."""

    def __init__(self, required, callback):
        self.required = frozenset(required)
        self.callback = callback
        self.pressed = set()
        self.armed = True
        self.pending = False

    def press(self, key):
        self.pressed.add(key)
        if self.armed and self.required.issubset(self.pressed):
            self.armed = False
            self.pending = True

    def release(self, key):
        self.pressed.discard(key)
        # Déclenche seulement lorsque tous les modificateurs sont relâchés :
        # le Ctrl+C de capture ne peut ainsi devenir Ctrl+Alt+C par accident.
        if self.pending and self.required.isdisjoint(self.pressed):
            self.pending = False
            self.armed = True
            self.callback()


def system_name():
    return platform.system().lower()


def primary_modifier(system=None):
    return "command" if (system or system_name()) == "darwin" else "ctrl"


def hotkey_spec(system=None):
    # Cmd+Shift+C ouvre la palette de couleurs native dans de nombreuses apps macOS.
    # Ctrl+Shift+C insère du code dans Microsoft Teams sous Windows.
    return "<ctrl>+<alt>+c" if (system or system_name()) == "darwin" else "<ctrl>+<shift>+<f8>"


def hotkey_label(system=None):
    return "⌃⌥C" if (system or system_name()) == "darwin" else "Ctrl+Shift+F8"


def default_hotkey_sequence(system=None):
    """Séquence portable enregistrable par QSettings."""
    return "Ctrl+Alt+C" if (system or system_name()) == "darwin" else "Ctrl+Shift+F8"


def hotkey_spec_from_label(label):
    """Convertit une séquence Qt portable en spécification pynput sûre."""
    aliases = {
        "ctrl": "<ctrl>", "control": "<ctrl>", "shift": "<shift>",
        "alt": "<alt>", "meta": "<cmd>", "cmd": "<cmd>", "win": "<cmd>",
    }
    named_keys = {
        "space": "<space>", "tab": "<tab>", "enter": "<enter>",
        "return": "<enter>", "backspace": "<backspace>", "delete": "<delete>",
        "insert": "<insert>", "home": "<home>", "end": "<end>",
        "pageup": "<page_up>", "pagedown": "<page_down>",
        "up": "<up>", "down": "<down>", "left": "<left>", "right": "<right>",
    }
    parts = [part.strip() for part in label.split("+") if part.strip()]
    if len(parts) < 2:
        raise ValueError("Le raccourci doit contenir au moins une touche modificatrice.")
    modifiers = []
    keys = []
    for part in parts:
        lowered = part.lower()
        if lowered in aliases:
            modifiers.append(aliases[lowered])
        elif re.fullmatch(r"f(?:[1-9]|1[0-9]|2[0-4])", lowered):
            keys.append(f"<{lowered}>")
        elif lowered in named_keys:
            keys.append(named_keys[lowered])
        elif len(lowered) == 1 and lowered.isalnum():
            keys.append(lowered)
        else:
            raise ValueError(f"La touche « {part} » n'est pas prise en charge.")
    if not modifiers or len(keys) != 1:
        raise ValueError("Choisissez une combinaison avec un modificateur et une seule touche principale.")
    modifier_order = ["<ctrl>", "<alt>", "<shift>", "<cmd>"]
    unique_modifiers = sorted(set(modifiers), key=modifier_order.index)
    spec = "+".join(unique_modifiers) + "+" + keys[0]
    reserved = {
        "<ctrl>+<space>": "Windows et Microsoft Teams utilisent déjà Ctrl+Espace.",
        "<alt>+<tab>": "Windows utilise déjà Alt+Tab.",
        "<alt>+<f4>": "Windows utilise déjà Alt+F4.",
        "<cmd>+<space>": "Le système utilise déjà cette combinaison.",
    }
    if spec in reserved:
        raise ValueError(reserved[spec] + " Choisissez par exemple Ctrl+Shift+F8.")
    return spec


def copy_shortcut(system=None):
    return primary_modifier(system), "c"


def paste_shortcut(system=None):
    return primary_modifier(system), "v"
