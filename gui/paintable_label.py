# File: paintable_label.py
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPainter, QPen
from PySide6.QtCore import Qt, QPoint

class PaintableLabel(QLabel):
    """A QLabel subclass that allows for painting with the mouse."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.drawing = False
        self.last_point = QPoint()
        
        self.active_pixmap = None
        self.brush_size = 10
        self.brush_color = Qt.GlobalColor.black

    # --- NEW HELPER FUNCTION ---
    # This function translates coordinates from the label's space to the pixmap's space.
    def _get_pixmap_coords(self, label_pos: QPoint) -> QPoint:
        if self.active_pixmap is None:
            return label_pos

        # Get the size of the label and the pixmap
        label_size = self.size()
        pixmap_size = self.active_pixmap.size()

        # Calculate the offset of the centered pixmap
        offset_x = (label_size.width() - pixmap_size.width()) // 2
        offset_y = (label_size.height() - pixmap_size.height()) // 2
        
        # Subtract the offset to get the coordinate relative to the pixmap
        return label_pos - QPoint(offset_x, offset_y)

    def set_active_pixmap(self, pixmap):
        self.active_pixmap = pixmap
        self.setPixmap(self.active_pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.active_pixmap:
            # --- MODIFIED ---
            # Translate coordinates before using them
            pixmap_pos = self._get_pixmap_coords(event.position().toPoint())

            # Only start drawing if the click is inside the pixmap's bounds
            if self.active_pixmap.rect().contains(pixmap_pos):
                self.drawing = True
                self.last_point = pixmap_pos
                self.draw_point(self.last_point)

    def mouseMoveEvent(self, event):
        if self.drawing and self.active_pixmap:
            # --- MODIFIED ---
            # Translate coordinates before drawing
            pixmap_pos = self._get_pixmap_coords(event.position().toPoint())
            self.draw_line(self.last_point, pixmap_pos)
            self.last_point = pixmap_pos

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False

    def draw_point(self, point):
        if not self.active_pixmap:
            return
        painter = QPainter(self.active_pixmap)
        pen = QPen(self.brush_color, self.brush_size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPoint(point)
        painter.end()
        self.update()

    def draw_line(self, start_point, end_point):
        if not self.active_pixmap:
            return
        painter = QPainter(self.active_pixmap)
        pen = QPen(self.brush_color, self.brush_size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(start_point, end_point)
        painter.end()
        self.update()

    def update(self):
        # Update the label's display
        self.setPixmap(self.active_pixmap)