# gui/paintable_label.py

from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import Qt, QPoint

class PaintableLabel(QLabel):
    """A QLabel subclass that allows for toggleable painting with the mouse."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.drawing = False
        self.last_point = QPoint()

        # Always store a QColor here
        self.brush_size = 10
        self.brush_color = QColor(Qt.GlobalColor.black)

        # This is the pixmap we draw onto.
        self.active_pixmap = None

        # Toggleable paint mode
        self.painting_enabled = False

        # We will manually scale before showing, so disable auto-scaling
        self.setScaledContents(False)

    def set_painting_enabled(self, enabled: bool):
        self.painting_enabled = enabled

    def set_brush_size(self, size: int):
        self.brush_size = size

    def set_brush_color(self, color: QColor):
        self.brush_color = color

    def _get_pixmap_coords(self, label_pos: QPoint) -> QPoint:
        if self.active_pixmap is None:
            return QPoint(-1, -1)
        lw, lh = self.width(), self.height()
        pw, ph = self.active_pixmap.width(), self.active_pixmap.height()
        scale = min(lw / pw, lh / ph)
        dw, dh = pw * scale, ph * scale
        ox, oy = (lw - dw) / 2, (lh - dh) / 2

        x = label_pos.x() - ox
        y = label_pos.y() - oy
        if x < 0 or y < 0 or x > dw or y > dh:
            return QPoint(-1, -1)
        return QPoint(int(x / scale), int(y / scale))

    def set_active_pixmap(self, pixmap):
        self.active_pixmap = pixmap
        self._refresh_scaled()

    def mousePressEvent(self, event):
        if (not self.painting_enabled
            or event.button() != Qt.MouseButton.LeftButton
            or self.active_pixmap is None):
            return super().mousePressEvent(event)

        pt = self._get_pixmap_coords(event.position().toPoint())
        if pt.x() >= 0 and self.active_pixmap.rect().contains(pt):
            self.drawing = True
            self.last_point = pt
            self._draw_point(pt)
        else:
            return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.painting_enabled and self.drawing and self.active_pixmap:
            pt = self._get_pixmap_coords(event.position().toPoint())
            if pt.x() >= 0:
                self._draw_line(self.last_point, pt)
                self.last_point = pt
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
        else:
            super().mouseReleaseEvent(event)

    def _draw_point(self, p: QPoint):
        painter = QPainter(self.active_pixmap)
        pen = QPen(self.brush_color, self.brush_size,
                   Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPoint(p)
        painter.end()
        self._refresh_scaled()

    def _draw_line(self, a: QPoint, b: QPoint):
        painter = QPainter(self.active_pixmap)
        pen = QPen(self.brush_color, self.brush_size,
                   Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(a, b)
        painter.end()
        self._refresh_scaled()

    def _refresh_scaled(self):
        if not self.active_pixmap:
            return
        lw, lh = self.width(), self.height()
        scaled = self.active_pixmap.scaled(
            lw, lh, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(scaled)
