# tests/test_paintable_label.py

import sys
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QColor
from gui.paintable_label import PaintableLabel

# Ensure a QApplication exists
_app = QApplication.instance() or QApplication(sys.argv)

def test_initial_state():
    """Verify defaults on initialization."""
    label = PaintableLabel()
    assert label.painting_enabled is False
    assert label.drawing is False
    assert label.active_pixmap is None
    assert label.brush_size == 10
    assert label.brush_color == QColor(Qt.black)
    # auto-scaling is disabled
    assert label.hasScaledContents() is False

def test_get_pixmap_coords_no_pixmap():
    """When no pixmap is set, coords should be (-1, -1)."""
    label = PaintableLabel()
    coord = label._get_pixmap_coords(QPoint(10, 10))
    assert coord == QPoint(-1, -1)

def test_get_pixmap_coords_mapping():
    """
    With a 50×50 pixmap in a 100×100 label:
    - scale factor is 2, offset (0,0).
    - mapping QPoint(80,20) → QPoint(40,10).
    - outside points → (-1,-1).
    """
    label = PaintableLabel()
    pix = QPixmap(50, 50)
    pix.fill(Qt.white)

    label.resize(100, 100)
    label.set_active_pixmap(pix)

    # inside
    coord = label._get_pixmap_coords(QPoint(80, 20))
    assert coord == QPoint(40, 10)

    # outside
    coord2 = label._get_pixmap_coords(QPoint(200, 200))
    assert coord2 == QPoint(-1, -1)

def test_setters():
    """Test brush enable toggle and setter methods."""
    label = PaintableLabel()

    label.set_painting_enabled(True)
    assert label.painting_enabled is True

    label.set_brush_size(25)
    assert label.brush_size == 25

    label.set_brush_color(QColor(Qt.red))
    assert label.brush_color == QColor(Qt.red)

def test_paint_point_and_line(qtbot):
    """
    Enable painting on a 100×100 pixmap, click at (50,50), then drag to (60,60).
    Verify:
      - drawing flag toggles correctly,
      - the pixel at (50,50) is painted in brush_color,
      - last_point updates to the mapped coords,
      - drawing stops on mouse release.
    """
    label = PaintableLabel()
    pix = QPixmap(100, 100)
    pix.fill(Qt.white)

    label.resize(100, 100)
    label.set_active_pixmap(pix)
    label.set_painting_enabled(True)

    # Paint a point
    qtbot.mousePress(label, Qt.LeftButton, pos=QPoint(50, 50))
    assert label.drawing is True

    img = label.active_pixmap.toImage()
    painted_color = img.pixelColor(50, 50)
    assert painted_color == label.brush_color

    # Draw a line
    qtbot.mouseMove(label, pos=QPoint(60, 60))
    expected_last = label._get_pixmap_coords(QPoint(60, 60))
    assert label.last_point == expected_last

    # Release
    qtbot.mouseRelease(label, Qt.LeftButton, pos=QPoint(60, 60))
    assert label.drawing is False
