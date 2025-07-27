# tests/test_main_window.py

import os
import sys
import builtins
import io
import pytest
from pathlib import Path
import datetime as real_datetime

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt

import gui.main_window as module
from gui.main_window import make_timestamped_dir, MainWindow

# Ensure a QApplication exists
_app = QApplication.instance() or QApplication(sys.argv)


def test_make_timestamped_dir(monkeypatch, tmp_path):
    """make_timestamped_dir uses the frozen datetime to name its folder."""
    fixed = real_datetime.datetime(2022, 1, 30, 14, 5, 9)

    class DummyDateTime:
        @staticmethod
        def now():
            return fixed

    monkeypatch.setattr(module, "datetime", DummyDateTime)

    base = tmp_path / "output_base"
    result = make_timestamped_dir(str(base))
    expected = base / "20220130_140509"
    assert Path(result) == expected
    assert expected.exists()


def test_mainwindow_missing_api_key(monkeypatch):
    """Without ./api.key present, MainWindow raises FileNotFoundError."""
    monkeypatch.setattr(module, "make_timestamped_dir", lambda base_path="./output": "/unused")
    monkeypatch.setattr(os.path, "exists", lambda path: False)

    with pytest.raises(FileNotFoundError) as exc:
        MainWindow()
    assert "OpenAI Key should be in ./api.key" in str(exc.value)


def test_mainwindow_init_and_navigation(monkeypatch, tmp_path):
    """
    Stub out FinalRenderWidget as a QWidget subclass so stacking works,
    then verify MainWindow's pages and navigation logic.
    """
    # 1) Stub timestamped dir
    monkeypatch.setattr(module, "make_timestamped_dir", lambda base_path="./output": str(tmp_path))

    # 2) Fake api.key exists and contains our test key
    monkeypatch.setattr(os.path, "exists", lambda path: path == "./api.key")
    fake_key = io.StringIO("MY_TEST_KEY")
    monkeypatch.setattr(builtins, "open", lambda path, mode='r': fake_key)

    # 3) Stub OpenAIImageGenerator so we capture the key
    class DummyGen:
        def __init__(self, api_key):
            self.api_key = api_key
    monkeypatch.setattr(module, "OpenAIImageGenerator", DummyGen)

    # 4) Stub FinalRenderWidget as a QWidget subclass
    from types import SimpleNamespace
    class DummyFinal(QWidget):
        def __init__(self, generator):
            super().__init__()
            self.generator = generator
            # back_button needs a clicked.connect
            self.back_button = SimpleNamespace(clicked=SimpleNamespace(connect=lambda fn: None))
            # store set_colormap calls
            self._last_cm = None
            self.output_dir = None
        def set_colormap(self, cm):
            self._last_cm = cm

    monkeypatch.setattr(module, "FinalRenderWidget", DummyFinal)

    # === Instantiate MainWindow ===
    mw = MainWindow()

    # Basic checks
    assert mw.windowTitle() == "MapMosaic"
    assert mw.output_dir == str(tmp_path)
    assert isinstance(mw.image_generator, DummyGen)
    assert mw.image_generator.api_key == "MY_TEST_KEY"

    # Check stacked pages
    st = mw.stacked_widget
    assert st.count() == 4
    assert st.currentWidget() is mw.welcome_page

    # Prevent real noise generation
    mw.noise_page.update_preview = lambda: None

    # -- go_to_noise --
    mw.go_to_noise()
    assert st.currentWidget() is mw.noise_page
    cfg = mw.noise_page.config
    assert cfg["seed"] == 42
    assert cfg["width"] == mw.noise_page.preview_size[0]
    assert cfg["height"] == mw.noise_page.preview_size[1]

    # -- go_to_feature --
    class StubHM:
        def __init__(self): self.saved = None
        def save(self, path): self.saved = path

    stub_hm = StubHM()
    mw.noise_page.get_heightmap = lambda: stub_hm
    got = {}
    mw.feature_page.set_heightmap = lambda hm: got.update({"hm": hm})

    mw.go_to_feature()
    exp_hm_path = os.path.join(str(tmp_path), "heightmap.png")
    assert stub_hm.saved == exp_hm_path
    assert got["hm"] is stub_hm
    assert st.currentWidget() is mw.feature_page

    # -- go_to_final --
    class StubCM:
        def __init__(self): self.saved = None
        def save(self, path, *args): self.saved = (path, args)

    stub_cm = StubCM()
    mw.feature_page.get_colormap = lambda: stub_cm

    mw.go_to_final()
    exp_cm_path = os.path.join(str(tmp_path), "featuremap.png")
    assert mw.final_page._last_cm is stub_cm
    assert stub_cm.saved[0] == exp_cm_path
    assert mw.final_page.output_dir == str(tmp_path)
    assert st.currentWidget() is mw.final_page
