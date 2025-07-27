# tests/test_multi_handle_slider.py

import sys
import pytest

from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent, QPaintEvent

from gui.multi_handle_slider import MultiHandleSlider

# Ensure a QApplication exists
_app = QApplication.instance() or QApplication(sys.argv)


def test_initial_state():
    """Slider starts with no values and dragging disabled."""
    slider = MultiHandleSlider(Qt.Horizontal)
    assert slider.values() == []
    assert slider._dragging is False
    assert slider._drag_index is None


def test_set_range_clamps_existing_values():
    """setRange should clamp any existing values into the new range."""
    slider = MultiHandleSlider(Qt.Horizontal)
    slider._values = [0, 50, 100]
    slider.setRange(10, 90)
    # values below 10 -> 10, above 90 -> 90
    assert slider.values() == [10, 50, 90]


def test_set_values_sorts_and_emits(qtbot):
    """setValues sorts inputs, clamps to range, updates internal list, and emits."""
    slider = MultiHandleSlider(Qt.Horizontal)
    slider.setRange(0, 100)

    recorded = []
    slider.valuesChanged.connect(recorded.append)

    slider.setValues([80, -20, 50, 120])
    # should clamp to [0, 50, 80, 100] sorted
    assert slider.values() == [0, 50, 80, 100]
    # signal emitted exactly once with the sorted list
    assert recorded == [[0, 50, 80, 100]]


def test_value_pixel_conversion_horizontal():
    """_value_to_pixel and _pixel_to_value should be inverses for horizontal orientation."""
    slider = MultiHandleSlider(Qt.Horizontal)
    slider.setRange(0, 100)
    slider.resize(100, 20)

    # Value 25 → pixel ≈ 25
    pix = slider._value_to_pixel(25)
    assert pytest.approx(pix, rel=1e-2) == 25

    # Pixel 75 → value ≈ 75
    val = slider._pixel_to_value(75)
    assert pytest.approx(val, rel=1e-2) == 75


def test_handle_widget_positioning():
    """
    addHandleWidget should parent the widget and position it
    at the correct pixel based on the handle value.
    """
    slider = MultiHandleSlider(Qt.Horizontal)
    slider.setRange(0, 100)
    slider.resize(100, 20)

    handle = QLabel("H")
    handle.resize(10, 10)
    slider.addHandleWidget(0, handle)

    # set one handle at value 50
    slider.setValues([50])

    # expected x = pixel(50) - half handle width = 50 - 5 = 45
    # expected y = center_y - handle.height = (20//2) - 10 = 10 - 10 = 0
    pos = handle.pos()
    assert pos == QPoint(45, 0)


def test_dragging_handle_updates_value_and_emits(qtbot):
    """
    Simulate dragging the first of two handles from 30→60.
    Ensure the value updates, emits each move, and respects order.
    """
    slider = MultiHandleSlider(Qt.Horizontal)
    slider.setRange(0, 100)
    slider.resize(100, 20)
    slider.setValues([30, 70])

    recorded = []
    slider.valuesChanged.connect(recorded.append)

    # Press near value=30 at pixel ~30
    qtbot.mousePress(slider, Qt.LeftButton, pos=QPoint(30, 10))

    # Drag to pixel 60
    qtbot.mouseMove(slider, QPoint(60, 10))
    # Release
    qtbot.mouseRelease(slider, Qt.LeftButton, pos=QPoint(60, 10))

    # After drag, first handle moves to ~60, second remains 70
    assert slider.values()[0] == pytest.approx(60, rel=1e-2)
    assert slider.values()[1] == 70

    # At least one valuesChanged emission should have occurred during move
    assert any(vals[0] == pytest.approx(60, rel=1e-2) for vals in recorded)


def test_paint_event_no_values_does_nothing(qtbot):
    """
    Calling paintEvent with no values should not error.
    """
    slider = MultiHandleSlider(Qt.Horizontal)
    slider.setRange(0, 100)
    evt = QPaintEvent(slider.rect())
    # No exception should be raised
    slider.paintEvent(evt)
