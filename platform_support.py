"""Comportements clavier propres à Windows et macOS."""

import platform


def system_name():
    return platform.system().lower()


def primary_modifier(system=None):
    return "command" if (system or system_name()) == "darwin" else "ctrl"


def hotkey_spec(system=None):
    return "<cmd>+<shift>+c" if (system or system_name()) == "darwin" else "<ctrl>+<shift>+c"


def hotkey_label(system=None):
    return "⌘⇧C" if (system or system_name()) == "darwin" else "Ctrl+Shift+C"


def copy_shortcut(system=None):
    return primary_modifier(system), "c"


def paste_shortcut(system=None):
    return primary_modifier(system), "v"
