"""Localisation de la sélection et effet aurore transparent au-dessus du texte."""

import math
import sys

from PyQt5.QtCore import QPoint, QPointF, QRect, QRectF, QTimer, Qt
from PyQt5.QtGui import QColor, QCursor, QLinearGradient, QPainter, QRadialGradient
from PyQt5.QtWidgets import QApplication, QWidget


def _windows_selection_rectangles():
    try:
        import uiautomation as automation

        control = automation.GetFocusedControl()
        if control is None:
            return []
        pattern = control.GetPattern(automation.PatternId.TextPattern)
        if pattern is None:
            return []
        rectangles = []
        for text_range in pattern.GetSelection():
            for rect in text_range.GetBoundingRectangles():
                width, height = rect.right - rect.left, rect.bottom - rect.top
                if width > 2 and height > 2:
                    rectangles.append(QRect(rect.left, rect.top, width, height))
        return rectangles
    except Exception:
        return []


def _macos_selection_rectangles():
    try:
        from ApplicationServices import (
            AXUIElementCreateSystemWide,
            AXUIElementCopyAttributeValue,
            AXUIElementCopyParameterizedAttributeValue,
            AXValueGetValue,
            kAXBoundsForRangeParameterizedAttribute,
            kAXFocusedUIElementAttribute,
            kAXSelectedTextRangeAttribute,
            kAXValueCGRectType,
        )

        system = AXUIElementCreateSystemWide()
        error, focused = AXUIElementCopyAttributeValue(system, kAXFocusedUIElementAttribute, None)
        if error or focused is None:
            return []
        error, selected_range = AXUIElementCopyAttributeValue(focused, kAXSelectedTextRangeAttribute, None)
        if error or selected_range is None:
            return []
        error, bounds = AXUIElementCopyParameterizedAttributeValue(
            focused, kAXBoundsForRangeParameterizedAttribute, selected_range, None
        )
        if error or bounds is None:
            return []
        value_result = AXValueGetValue(bounds, kAXValueCGRectType, None)
        if isinstance(value_result, tuple):
            success, rect = value_result
            if not success:
                return []
        else:
            rect = getattr(bounds, "rect", bounds)
        origin, size = rect.origin, rect.size
        if size.width > 2 and size.height > 2:
            return [QRect(int(origin.x), int(origin.y), int(size.width), int(size.height))]
    except Exception:
        pass
    return []


def selection_rectangles():
    if sys.platform == "win32":
        return _windows_selection_rectangles()
    if sys.platform == "darwin":
        return _macos_selection_rectangles()
    return []


def fallback_caret_rectangle():
    position = QCursor.pos()
    return QRect(position.x() + 10, position.y() - 14, 180, 24)


class AuroraOverlay(QWidget):
    """Surcouche sans focus donnant l'illusion d'une aurore sur la sélection."""

    def __init__(self, parent=None):
        flags = (
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
            Qt.WindowDoesNotAcceptFocus
        )
        super().__init__(parent, flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.phase = 0.0
        self.local_rectangles = []
        self.finishing = False
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.advance)

    @staticmethod
    def _to_logical(rect):
        for screen in QApplication.screens():
            geometry = screen.geometry()
            ratio = screen.devicePixelRatio()
            physical = QRect(
                int(geometry.x() * ratio), int(geometry.y() * ratio),
                int(geometry.width() * ratio), int(geometry.height() * ratio),
            )
            if physical.contains(rect.center()):
                return QRect(
                    int(geometry.x() + (rect.x() - physical.x()) / ratio),
                    int(geometry.y() + (rect.y() - physical.y()) / ratio),
                    max(1, int(rect.width() / ratio)), max(1, int(rect.height() / ratio)),
                )
        return rect

    def start(self, rectangles):
        rectangles = [self._to_logical(rect) for rect in rectangles if rect.width() > 1 and rect.height() > 1]
        if not rectangles:
            rectangles = [fallback_caret_rectangle()]
        bounds = rectangles[0]
        for rect in rectangles[1:]:
            bounds = bounds.united(rect)
        bounds = bounds.adjusted(-12, -10, 12, 10)
        self.setGeometry(bounds)
        self.local_rectangles = [rect.translated(-bounds.x(), -bounds.y()) for rect in rectangles]
        self.phase = 0.0
        self.finishing = False
        self.show()
        self.raise_()
        self.timer.start()

    def advance(self):
        self.phase = (self.phase + 0.018) % 1.0
        self.update()

    def complete(self):
        if not self.isVisible():
            return
        self.finishing = True
        self.update()
        QTimer.singleShot(350, self.stop)

    def stop(self):
        self.timer.stop()
        self.hide()
        self.local_rectangles = []
        self.finishing = False

    def paintEvent(self, event):
        if not self.local_rectangles:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        for rect in self.local_rectangles:
            area = QRectF(rect.adjusted(-4, -3, 4, 3))
            painter.save()
            painter.setClipRect(area)

            base = QLinearGradient(area.left(), area.top(), area.right(), area.bottom())
            if self.finishing:
                base.setColorAt(0, QColor(30, 240, 170, 65))
                base.setColorAt(1, QColor(80, 255, 210, 115))
            else:
                base.setColorAt(0, QColor(15, 130, 255, 28))
                base.setColorAt(0.5, QColor(25, 245, 190, 62))
                base.setColorAt(1, QColor(80, 120, 255, 22))
            painter.fillRect(area, base)

            for index, color in enumerate((
                QColor(30, 215, 255, 115), QColor(35, 255, 165, 105), QColor(90, 130, 255, 90)
            )):
                travel = (self.phase + index / 3.0) % 1.0
                x = area.left() - area.width() * 0.25 + travel * area.width() * 1.5
                y = area.center().y() + math.sin((self.phase * 2 + index) * math.pi) * area.height() * 0.24
                glow = QRadialGradient(QPointF(x, y), max(18.0, area.width() * 0.22))
                glow.setColorAt(0, color)
                glow.setColorAt(0.45, QColor(color.red(), color.green(), color.blue(), 45))
                glow.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
                painter.fillRect(area, glow)

            painter.setPen(QColor(55, 255, 200, 95 if self.finishing else 55))
            wave_y = area.bottom() - 2 + math.sin(self.phase * math.tau) * 1.5
            painter.drawLine(int(area.left()), int(wave_y), int(area.right()), int(wave_y))
            painter.restore()
        painter.end()
