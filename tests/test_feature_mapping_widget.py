# tests/test_feature_mapping_widget.py

import os
import sys
import pytest
import numpy as np
from PIL import Image

from PySide6.QtWidgets import QApplication, QColorDialog
from PySide6.QtGui import QPixmap, QColor, QMouseEvent
from PySide6.QtCore import Qt, QEvent, QPoint

import gui.feature_mapping_widget as module
from gui.feature_mapping_widget import FeatureMappingWidget

# Ensure a QApplication exists
_app = QApplication.instance() or QApplication(sys.argv)


@pytest.fixture
def widget(monkeypatch, tmp_path):
    # Stub pillow_to_pixmap to return a small pixmap
    stub_pix = QPixmap(2, 2)
    stub_pix.fill(QColor('red'))
    monkeypatch.setattr(module, 'pillow_to_pixmap', lambda img: stub_pix)

    w = FeatureMappingWidget()
    w.output_dir = str(tmp_path)
    w.show()
    return w


def test_initial_state(widget):
    w = widget
    assert not w.brush_size.isVisible()
    assert not w.brush_color_btn.isVisible()
    assert w.paintable_label.active_pixmap is None

    expected = [int(90 * (i + 1) / len(w.regions)) for i in range(len(w.regions))]
    assert w.range_slider.values() == expected


def test_paint_toggle_shows_and_hides_controls(widget):
    w = widget
    w.paint_toggle.click()
    assert w.brush_size.isVisible()
    assert w.brush_color_btn.isVisible()

    w.paint_toggle.click()
    assert not w.brush_size.isVisible()
    assert not w.brush_color_btn.isVisible()


def test_set_heightmap_and_update_colormap(widget):
    w = widget
    arr = np.array([[0, 128], [192, 255]], dtype=np.uint8)
    img = Image.fromarray(arr, 'L')
    w.set_heightmap(img)

    assert isinstance(w.colormap, Image.Image)
    assert w.colormap.size == img.size
    assert isinstance(w.paintable_label.active_pixmap, QPixmap)


def test_choose_color_updates_region_and_calls_update(monkeypatch, widget):
    w = widget
    new_col = QColor(1, 2, 3)
    monkeypatch.setattr(QColorDialog, 'getColor', staticmethod(lambda *args, **kwargs: new_col))

    calls = []
    monkeypatch.setattr(w, 'update_colormap', lambda *_: calls.append(True))

    btn = w.handle_buttons[0]
    w.choose_color(0)

    assert w.regions[0]['color'] == new_col
    assert new_col.name() in btn.styleSheet()
    assert calls, "update_colormap should be called"


def test_event_filter_click_triggers_choose_color(monkeypatch, widget):
    w = widget
    idx = 2
    btn = w.handle_buttons[idx]

    calls = []
    monkeypatch.setattr(w, 'choose_color', lambda i: calls.append(i))

    pos = QPoint(btn.width() // 2, btn.height() // 2)
    mapped = btn.mapTo(w.range_slider, pos)
    press = QMouseEvent(QEvent.MouseButtonPress, pos, mapped, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    assert w.eventFilter(btn, press) is True

    release = QMouseEvent(QEvent.MouseButtonRelease, pos, mapped, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    w._dragging_btn = False
    assert w.eventFilter(btn, release) is True

    assert calls == [idx]


def test_get_colormap_from_active_pixmap(widget):
    w = widget
    # Create a standalone pixmap of known size and fill with a known color
    pix = QPixmap(3, 3)
    pix.fill(QColor(10, 20, 30))
    w.paintable_label.active_pixmap = pix

    cm = w.get_colormap()
    assert isinstance(cm, Image.Image)
    assert cm.size == (3, 3)
    # All pixels should match (10,20,30)
    assert cm.getpixel((1, 1)) == (10, 20, 30)


def test_save_colormap_writes_file(monkeypatch, widget, tmp_path):
    w = widget
    img = Image.new('RGB', (4, 4), (5, 6, 7))
    monkeypatch.setattr(w, 'get_colormap', lambda: img)

    w.save_colormap(str(tmp_path))
    out_path = tmp_path / "featuremap.png"
    assert out_path.exists()

    saved = Image.open(str(out_path))
    assert saved.mode == 'RGB'
    assert saved.size == img.size
