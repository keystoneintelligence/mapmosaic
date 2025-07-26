# paintable_label.py

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

        self.active_pixmap = None
        self.brush_size = 10
        self.brush_color = Qt.GlobalColor.black

        # New flag to enable/disable painting
        self.painting_enabled = False

        # Scale the pixmap to fit the widget bounds
        self.setScaledContents(True)

    def set_painting_enabled(self, enabled: bool):
        """Enable or disable paint mode."""
        self.painting_enabled = enabled

    def set_brush_size(self, size: int):
        """Set the brush size."""
        self.brush_size = size

    def set_brush_color(self, color: QColor):
        """Set the brush color."""
        self.brush_color = color

    def _get_pixmap_coords(self, label_pos: QPoint) -> QPoint:
        """
        Map a click in widget coords to the full-res pixmap coords,
        taking into account scaling and centering.
        """
        if self.active_pixmap is None:
            return label_pos

        lw, lh = self.width(), self.height()
        pw, ph = self.active_pixmap.width(), self.active_pixmap.height()

        # How much the pixmap is scaled to fit
        scale = min(lw / pw, lh / ph)
        dw, dh = pw * scale, ph * scale

        # Offset to center the scaled pixmap
        ox, oy = (lw - dw) / 2, (lh - dh) / 2

        # Position within the scaled pixmap
        x = label_pos.x() - ox
        y = label_pos.y() - oy
        if x < 0 or y < 0 or x > dw or y > dh:
            return QPoint(-1, -1)

        # Map back to original pixmap coords
        return QPoint(int(x / scale), int(y / scale))

    def set_active_pixmap(self, pixmap):
        """Set the pixmap to paint on."""
        self.active_pixmap = pixmap
        self.setPixmap(self.active_pixmap)

    def mousePressEvent(self, event):
        # Only draw if paint mode is enabled and left button pressed
        if not self.painting_enabled or event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)

        pixmap_pos = self._get_pixmap_coords(event.position().toPoint())
        if pixmap_pos.x() >= 0 and self.active_pixmap.rect().contains(pixmap_pos):
            self.drawing = True
            self.last_point = pixmap_pos
            self.draw_point(self.last_point)

    def mouseMoveEvent(self, event):
        if self.painting_enabled and self.drawing and self.active_pixmap:
            pixmap_pos = self._get_pixmap_coords(event.position().toPoint())
            if pixmap_pos.x() >= 0:
                self.draw_line(self.last_point, pixmap_pos)
                self.last_point = pixmap_pos
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
        else:
            super().mouseReleaseEvent(event)

    def draw_point(self, point: QPoint):
        """Draw a single point on the active pixmap."""
        if not self.active_pixmap:
            return
        painter = QPainter(self.active_pixmap)
        pen = QPen(self.brush_color, self.brush_size,
                   Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPoint(point)
        painter.end()
        self.update()

    def draw_line(self, start_point: QPoint, end_point: QPoint):
        """Draw a line on the active pixmap."""
        if not self.active_pixmap:
            return
        painter = QPainter(self.active_pixmap)
        pen = QPen(self.brush_color, self.brush_size,
                   Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(start_point, end_point)
        painter.end()
        self.update()

    def update(self):
        """Refresh the label display with the current pixmap."""
        if self.active_pixmap:
            self.setPixmap(self.active_pixmap)
