# File: multi_handle_slider.py
from PySide6.QtWidgets import QSlider
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QPainter, QPen

class MultiHandleSlider(QSlider):
    """
    A QSlider subclass that supports multiple draggable handles on one groove.
    Emits valuesChanged(list_of_ints) when handles move.
    Handles cannot cross each other (values sorted), with the native handle hidden.
    """
    valuesChanged = Signal(list)

    def __init__(self, orientation: Qt.Orientation, parent=None):
        super().__init__(orientation, parent)
        self._values = []
        self._dragging = False
        self._drag_index = None
        self._handle_widgets = {}
        self.setMouseTracking(True)

        if orientation == Qt.Horizontal:
            self.setStyleSheet("QSlider::handle:horizontal { background: transparent; width: 0px; }")
        else:
            self.setStyleSheet("QSlider::handle:vertical { background: transparent; height: 0px; }")

    def setRange(self, minimum: int, maximum: int) -> None:
        super().setRange(minimum, maximum)
        self._values = [max(min(v, maximum), minimum) for v in self._values]
        self.update()

    def setValues(self, values: list[int]) -> None:
        mn, mx = self.minimum(), self.maximum()
        self._values = sorted(max(min(int(v), mx), mn) for v in values)
        self.valuesChanged.emit(self._values)
        self.update()
        self._update_handle_widgets()

    def values(self) -> list[int]:
        return list(self._values)

    def addHandleWidget(self, index: int, widget) -> None:
        widget.setParent(self)
        self._handle_widgets[index] = widget
        self._update_handle_widgets()

    def mousePressEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._values:
            pos = event.position().toPoint()
            closest = min(
                range(len(self._values)),
                key=lambda i: abs(self._value_to_pixel(self._values[i]) - (
                    pos.x() if self.orientation() == Qt.Horizontal else pos.y()))
            )
            self._dragging = True
            self._drag_index = closest
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        if self._dragging and self._drag_index is not None:
            val = self._pixel_to_value(
                pos.x() if self.orientation() == Qt.Horizontal else pos.y()
            )
            mn, mx = self.minimum(), self.maximum()
            val = max(min(val, mx), mn)
            idx = self._drag_index
            if idx > 0:
                val = max(val, self._values[idx - 1])
            if idx < len(self._values) - 1:
                val = min(val, self._values[idx + 1])
            self._values[idx] = val
            self.valuesChanged.emit(self._values)
            self.update()
            self._update_handle_widgets()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            self._drag_index = None
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._values:
            return
        painter = QPainter(self)
        pen = QPen(Qt.black, 2)
        painter.setPen(pen)
        for val in self._values:
            pix = self._value_to_pixel(val)
            if self.orientation() == Qt.Horizontal:
                y0 = self.height() // 2 - 6
                y1 = self.height() // 2 + 6
                painter.drawLine(pix, y0, pix, y1)
            else:
                x0 = self.width() // 2 - 6
                x1 = self.width() // 2 + 6
                painter.drawLine(x0, pix, x1, pix)
        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_handle_widgets()

    def _value_to_pixel(self, value: int) -> int:
        mn, mx = self.minimum(), self.maximum()
        length = self.width() if self.orientation() == Qt.Horizontal else self.height()
        ratio = (value - mn) / float(mx - mn) if mx > mn else 0
        return int(ratio * length)

    def _pixel_to_value(self, pixel: int) -> int:
        mn, mx = self.minimum(), self.maximum()
        length = self.width() if self.orientation() == Qt.Horizontal else self.height()
        ratio = float(pixel) / length if length else 0
        return int(ratio * (mx - mn) + mn)

    def _update_handle_widgets(self):
        for idx, widget in self._handle_widgets.items():
            if idx < len(self._values):
                pix = self._value_to_pixel(self._values[idx])
                if self.orientation() == Qt.Horizontal:
                    x = pix - widget.width() // 2
                    y = (self.height() // 2) - widget.height()
                else:
                    x = (self.width() // 2) - widget.width()
                    y = pix - widget.height() // 2
                widget.move(x, y)
                widget.show()
