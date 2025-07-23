# tests/test_final_render_widget.py

import os
import sys
import io
import pytest
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

import gui.final_render_widget as module
from gui.final_render_widget import _RenderWorker, FinalRenderWidget
from PIL import Image

# ensure a QApplication exists
_app = QApplication.instance() or QApplication(sys.argv)


def test_render_worker_success(tmp_path):
    """_RenderWorker.run should emit finished with the opened PIL.Image."""
    # create a small test image file
    img_path = tmp_path / "test.png"
    orig = Image.new("RGB", (2, 3), (5, 6, 7))
    orig.save(str(img_path))

    # dummy generator that returns our path and checks args
    class Gen:
        def generate_rough_draft_image(self, working_dir, reference_image, map_description):
            assert working_dir == str(tmp_path)
            assert reference_image == str(img_path)
            assert map_description == "desc"
            return str(img_path)

    worker = _RenderWorker(Gen(), {"working_dir": str(tmp_path), "path": str(img_path)}, "desc")

    finished = []
    errors = []
    worker.finished.connect(lambda img: finished.append(img))
    worker.error.connect(lambda err: errors.append(err))

    worker.run()

    assert len(finished) == 1
    img = finished[0]
    assert isinstance(img, Image.Image)
    assert img.size == (2, 3)
    assert errors == []


def test_render_worker_error(tmp_path):
    """_RenderWorker.run should emit error on exception."""
    class BadGen:
        def generate_rough_draft_image(self, *args, **kwargs):
            raise RuntimeError("oops")

    worker = _RenderWorker(BadGen(), {"working_dir": "x", "path": "y"}, "p")
    finished = []
    errors = []
    worker.finished.connect(lambda img: finished.append(img))
    worker.error.connect(lambda err: errors.append(err))

    worker.run()

    assert finished == []
    assert len(errors) == 1
    assert "oops" in errors[0]


@pytest.fixture
def widget(tmp_path, monkeypatch):
    """
    Create a FinalRenderWidget with:
     - output_dir set to tmp_path,
     - pillow_to_pixmap stubbed,
     - QFileDialog.getSaveFileName stubbed.
    """
    # stub pillow_to_pixmap to return a known pixmap
    stub_pix = QPixmap(10, 10)
    monkeypatch.setattr(module, "pillow_to_pixmap", lambda img: stub_pix)

    # stub the file dialog so save_final_map doesn't open real UI
    def fake_save(parent, title, default, filt):
        # return a path without .png to test extension logic
        return str(tmp_path / "out"), None
    monkeypatch.setattr(module.QFileDialog, "getSaveFileName", staticmethod(fake_save))

    w = FinalRenderWidget()
    w.output_dir = str(tmp_path)
    return w


def test_initial_state(widget):
    """Verify default UI state before any operations."""
    w = widget
    # preview_label shows placeholder text
    assert "No map loaded." in w.preview_label.text()
    # progress hidden, export disabled
    assert w.progress_bar.isVisible() is False
    assert w.export_button.isEnabled() is False
    # back and generate buttons enabled
    assert w.back_button.isEnabled() is True
    assert w.generate_button.isEnabled() is True


def test_set_colormap_saves_and_updates_preview(widget, tmp_path):
    """set_colormap should save the image, set base_image, update preview, and disable export."""
    w = widget

    # create a test PIL.Image
    img = Image.new("RGB", (4, 4), (100, 150, 200))
    w.set_colormap(img)

    feature_path = tmp_path / "featuremap.png"
    assert feature_path.exists()

    # base_image must point to that file and working_dir
    assert w.base_image["path"] == str(feature_path)
    assert w.base_image["working_dir"] == str(tmp_path)

    # preview updated to our stub pixmap
    pix = w.preview_label.pixmap()
    assert pix is not None and isinstance(pix, QPixmap)
    # export still disabled immediately after set_colormap
    assert w.export_button.isEnabled() is False


def test_on_render_finished_and_error(widget):
    """on_render_finished should enable buttons and hide progress; error should show message."""
    w = widget
    # stub preview size so scaling works
    w.preview_label.resize(20, 20)

    # ----- success -----
    stub_pix = QPixmap(5, 5)
    # call finished
    w.on_render_finished(Image.new("RGB", (5, 5), (1, 2, 3)))
    # progress hidden, buttons re-enabled
    assert w.progress_bar.isVisible() is False
    assert w.generate_button.isEnabled() is True
    assert w.back_button.isEnabled() is True
    assert w.export_button.isEnabled() is True
    # original_pixmap set
    assert isinstance(w.original_pixmap, QPixmap)

    # ----- error -----
    w.progress_bar.setVisible(True)
    w.generate_button.setEnabled(False)
    w.back_button.setEnabled(False)
    # call error
    w.on_render_error("fail msg")
    assert "Error generating map" in w.preview_label.text()
    assert w.progress_bar.isVisible() is False
    assert w.generate_button.isEnabled() is True
    assert w.back_button.isEnabled() is True


def test__update_preview_and_get_final_pixmap(widget):
    """_update_preview should set original_pixmap and update preview_label; get_final_pixmap returns it."""
    w = widget
    pix = QPixmap(8, 6)
    w.preview_label.resize(16, 12)

    w._update_preview(pix)
    assert w.original_pixmap.cacheKey() == pix.cacheKey()
    lbl_pix = w.preview_label.pixmap()
    assert lbl_pix is not None
    assert w.get_final_pixmap().cacheKey() == pix.cacheKey()


def test_save_final_map_creates_file(widget, tmp_path):
    """
    save_final_map should invoke QFileDialog stub and save the original_pixmap to disk,
    adding .png if missing.
    """
    w = widget
    # Set a valid pixmap
    pix = QPixmap(12, 12)
    pix.fill(Qt.red)
    w.original_pixmap = pix

    # call save
    w.save_final_map()

    # dialog default returned tmp_path/"out" → code appends ".png"
    saved = tmp_path / "out.png"
    assert saved.exists()
    # file is a valid PNG
    img = Image.open(str(saved))
    assert img.size == (12, 12)
