# tests/test_noise_widget.py

import sys
import pytest
from PIL import Image

from PySide6.QtWidgets import QApplication, QSizePolicy
from PySide6.QtGui import QPalette, QColor, QFont, QPixmap
from PySide6.QtCore import Qt, QSize

import gui.noise_widget as module
from gui.noise_widget import NoiseWidget

# Ensure a QApplication exists
_app = QApplication.instance() or QApplication(sys.argv)


def test_initial_state_noise_widget():
    """Defaults: no config, no generator, preview_size is (512,512)."""
    w = NoiseWidget()
    assert w.config is None
    assert w.generator is None
    assert w.preview_size == (512, 512)


def test_background_and_layout_noise_widget():
    """Widget has a white autofill background and the main layout’s margins and spacing."""
    w = NoiseWidget()
    # white autofill background
    assert w.autoFillBackground() is True
    pal = w.palette()
    assert pal.color(QPalette.ColorRole.Window) == QColor("white")

    # main layout margins & spacing
    layout = w.layout()
    assert layout.getContentsMargins() == (40, 40, 40, 40)
    assert layout.spacing() == 25


def test_preview_label_properties():
    """The preview_label is centered, has correct minimum size,
    uses an expanding size policy, and has the border style."""
    w = NoiseWidget()
    lbl = w.preview_label

    # alignment stays centered
    assert lbl.alignment() == Qt.AlignCenter

    # now we check minimum size rather than fixed size
    assert (lbl.minimumWidth(), lbl.minimumHeight()) == w.preview_size

    # size policy should be expanding in both directions
    sp = lbl.sizePolicy()
    assert sp.horizontalPolicy() == QSizePolicy.Expanding
    assert sp.verticalPolicy()   == QSizePolicy.Expanding

    # border style remains
    assert "border: 1px solid #ddd" in lbl.styleSheet()


def test_spinbox_defaults_and_properties():
    """Verify each QSpinBox/QDoubleSpinBox default value and step sit within their ranges."""
    w = NoiseWidget()

    # Base frequency
    bf = w.base_freq_spin
    assert bf.value() == pytest.approx(0.005, rel=1e-3)
    assert bf.minimum() < bf.value() < bf.maximum()
    assert bf.singleStep() == pytest.approx(0.0001, rel=1e-6)
    assert bf.decimals() == 3

    # Octaves
    oc = w.octaves_spin
    assert oc.value() == 6
    assert oc.minimum() == 1
    assert oc.maximum() == 10

    # Lacunarity
    lac = w.lacunarity_spin
    assert lac.value() == pytest.approx(2.2, rel=1e-3)
    assert lac.minimum() < lac.value() < lac.maximum()
    assert lac.singleStep() == pytest.approx(0.1, rel=1e-6)

    # Gain
    gn = w.gain_spin
    assert gn.value() == pytest.approx(0.5, rel=1e-3)
    assert gn.minimum() < gn.value() < gn.maximum()
    assert gn.singleStep() == pytest.approx(0.01, rel=1e-6)

    # Warp amplitude
    wa = w.warp_amp_spin
    assert wa.value() == pytest.approx(0.1, rel=1e-3)
    assert wa.minimum() < wa.value() < wa.maximum()
    assert wa.singleStep() == pytest.approx(0.01, rel=1e-6)

    # Warp frequency
    wf = w.warp_freq_spin
    assert wf.value() == pytest.approx(0.02, rel=1e-3)
    assert wf.minimum() < wf.value() < wf.maximum()
    assert wf.singleStep() == pytest.approx(0.001, rel=1e-6)

    # Seed
    sd = w.seed_spin
    assert sd.value() == 42
    assert sd.minimum() == 0
    assert sd.maximum() == 2**31 - 1

    # All spin-boxes share max width 120
    for sb in [
        w.base_freq_spin, w.octaves_spin, w.lacunarity_spin,
        w.gain_spin, w.warp_amp_spin, w.warp_freq_spin, w.seed_spin
    ]:
        assert sb.maximumWidth() == 120


def test_next_button_properties():
    """Continue button has correct text, fixed size, and bold 11-pt font."""
    w = NoiseWidget()
    btn = w.next_button

    assert btn.text() == "Continue"
    assert btn.minimumSize() == QSize(180, 45)
    assert btn.maximumSize() == QSize(180, 45)

    font: QFont = btn.font()
    assert font.pointSize() == 11
    assert font.bold() is True


def test_stylesheet_noise_widget():
    """Widget stylesheet includes background rule, hover/pressed, and label font-size."""
    w = NoiseWidget()
    ss = w.styleSheet()
    assert "background-color: white" in ss
    assert "QPushButton:hover" in ss
    assert "QLabel" in ss and "font-size: 13px" in ss


def test_apply_settings_and_update_preview(monkeypatch, qtbot):
    """
    Monkey-patch HeightmapGenerator.generate and pillow_to_pixmap so update_preview
    sets preview_label.pixmap() to our stub QPixmap.
    """
    stub_img = Image.new("RGB", (3, 5), (1, 2, 3))
    stub_pix = QPixmap(3, 5)
    stub_pix.fill(Qt.red)

    monkeypatch.setattr(
        module.HeightmapGenerator,
        "generate",
        lambda self, w, h: stub_img
    )
    monkeypatch.setattr(
        module,
        "pillow_to_pixmap",
        lambda img: stub_pix
    )

    w = NoiseWidget()
    qtbot.addWidget(w)

    cfg = {"seed": 123}
    w.apply_settings(cfg)

    assert w.config == cfg
    assert w.seed_spin.value() == 123

    pix = w.preview_label.pixmap()
    assert pix is not None
    assert pix.cacheKey() == stub_pix.cacheKey()


def test_get_heightmap(monkeypatch):
    """
    get_heightmap() returns None if no config/generator,
    otherwise returns an image of the right size.
    """
    w = NoiseWidget()
    assert w.get_heightmap() is None

    class FakeGen:
        def generate(self, width, height):
            return Image.new("RGB", (width, height))

    w.config = {"width": 10, "height": 20}
    w.generator = FakeGen()

    img = w.get_heightmap()
    assert img.size == (10, 20)
