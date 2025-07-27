# tests/test_welcome_widget.py

import os
import pytest
from pathlib import Path
from PIL import Image

from PySide6.QtGui import QPalette, QColor, QFont
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QApplication

from gui.welcome_widget import WelcomeWidget

# ensure a QApplication is running for all tests
_app = QApplication.instance() or QApplication([])

@pytest.mark.parametrize("file_exists", [False, True])
def test_logo_label_pixmap(monkeypatch, tmp_path, qtbot, file_exists):
    """
    If favicon.png exists next to the module, logo_label.pixmap() should be valid.
    Otherwise, it should be a null QPixmap (i.e. pixmap.isNull() is True).
    """
    # point module.__file__ into our temp dir
    import gui.welcome_widget as module
    fake_mod = tmp_path / "welcome_widget.py"
    fake_mod.write_text("# dummy")
    monkeypatch.setattr(module, "__file__", str(fake_mod))

    logo_png = tmp_path / "favicon.png"
    if file_exists:
        # create a 1×1 white PNG
        Image.new("RGBA", (1, 1), (255, 255, 255, 255)).save(str(logo_png))

    # patch os.path.exists() to only return True for our temp favicon.png
    monkeypatch.setattr(os.path, "exists", lambda path: str(logo_png) == path)

    w = WelcomeWidget()
    qtbot.addWidget(w)
    px = w.logo_label.pixmap()

    if file_exists:
        assert px is not None, "Expected a QPixmap instance when favicon.png exists"
        assert not px.isNull(), "Expected a non-null pixmap when favicon.png exists"
    else:
        # Qt will return a QPixmap(null) rather than None
        assert px is not None, "Expected a QPixmap (even if null)"
        assert px.isNull(), "Expected a null pixmap when favicon.png is missing"

def test_background_and_palette():
    w = WelcomeWidget()
    assert w.autoFillBackground() is True
    pal = w.palette()
    assert pal.color(QPalette.ColorRole.Window) == QColor("white")

def test_layout_margins_spacing_alignment():
    w = WelcomeWidget()
    layout = w.layout()
    assert layout.getContentsMargins() == (40, 40, 40, 40)
    assert layout.spacing() == 25
    assert bool(layout.alignment() & Qt.AlignmentFlag.AlignCenter)

def test_welcome_text_properties():
    w = WelcomeWidget()
    lbl = w.welcome_text
    assert lbl.textFormat() == Qt.TextFormat.RichText
    assert bool(lbl.alignment() & Qt.AlignmentFlag.AlignCenter)
    assert "<h2" in lbl.text() and "MapMosaic" in lbl.text()

@pytest.mark.parametrize("expected_text, size", [
    ("🗺️  Get Started", (180, 45)),
])
def test_start_button_properties(qtbot, expected_text, size):
    w = WelcomeWidget()
    qtbot.addWidget(w)
    btn = w.start_button

    assert btn.text() == expected_text
    assert btn.minimumSize() == QSize(*size)
    assert btn.maximumSize() == QSize(*size)

    font: QFont = btn.font()
    assert font.pointSize() == 11
    assert font.bold() is True

def test_stylesheet_contains_expected_rules():
    w = WelcomeWidget()
    ss = w.styleSheet()
    assert "background-color: white" in ss
    assert "border-radius: 6px" in ss
    assert "QPushButton:hover" in ss
    assert "QPushButton:pressed" in ss
