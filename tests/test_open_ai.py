# tests/test_openai_image_generator.py

import os
import sys
import base64
import builtins
import io
import pytest
from pathlib import Path
import openai as openai_sdk
import inference.openai as module
from inference.openai import OpenAIImageGenerator
from types import SimpleNamespace
from PIL import Image

@pytest.fixture(autouse=True)
def isolate_openai_api_key(monkeypatch):
    """Ensure we don't touch the real openai.api_key."""
    monkeypatch.setattr(openai_sdk, "api_key", None)
    yield

def test_process_image_not_exists(capsys):
    """Nonexistent path returns None with a warning."""
    result = OpenAIImageGenerator._process_image("no_file.png")
    assert result is None
    captured = capsys.readouterr()
    assert "Warning: File not found" in captured.out

def test_process_image_io_error(tmp_path, monkeypatch, capsys):
    """IO errors during open return None with an error message."""
    p = tmp_path / "img.png"
    p.write_bytes(b"data")
    # Force open to raise
    monkeypatch.setattr(builtins, "open", lambda path, mode="rb": (_ for _ in ()).throw(IOError("fail")))
    result = OpenAIImageGenerator._process_image(str(p))
    assert result is None
    captured = capsys.readouterr()
    assert "Error loading image" in captured.out

def test_generate_rough_draft_image_success(monkeypatch):
    """generate_rough_draft_image calls generate_image once and returns its path."""
    gen = OpenAIImageGenerator("key")
    calls = []
    def fake_gen_image(self, prompt, output_path, reference_images, prefix, quality):
        calls.append((prompt, output_path, reference_images, prefix, quality))
        return "draft.png"
    monkeypatch.setattr(OpenAIImageGenerator, "generate_image", fake_gen_image)

    out = gen.generate_rough_draft_image("wd", "ref.png", "mystyle")
    assert out == "draft.png"
    assert len(calls) == 1
    _, wd, refs, prefix, qual = calls[0]
    assert "mystyle" in calls[0][0]
    assert wd == "wd"
    assert refs == ["ref.png"]
    assert prefix == "rough_draft"
    assert qual == "low"

def test_generate_rough_draft_image_retries_then_success(monkeypatch):
    """generate_rough_draft_image retries on None once before succeeding."""
    gen = OpenAIImageGenerator("key")
    seq = [None, "ok.png"]
    def fake(self, *args, **kwargs):
        return seq.pop(0)
    monkeypatch.setattr(OpenAIImageGenerator, "generate_image", fake)

    out = gen.generate_rough_draft_image("wd", "ref.png", "desc")
    assert out == "ok.png"

def test_generate_rough_draft_image_failure(monkeypatch):
    """Fails after 3 unsuccessful attempts."""
    gen = OpenAIImageGenerator("key")
    monkeypatch.setattr(OpenAIImageGenerator, "generate_image", lambda *args, **kwargs: None)
    with pytest.raises(ValueError) as exc:
        gen.generate_rough_draft_image("wd", "ref.png", "desc")
    assert "Failed to call OpenAI" in str(exc.value)

@pytest.mark.parametrize("method_name,prefix", [
    ("generate_seed_image", "seed_2"),
    ("generate_mosaic_image", "mosaic_5"),
])
def test_generate_seed_and_mosaic(monkeypatch, tmp_path, method_name, prefix):
    """Test seed & mosaic generators call generate_image with correct kwargs."""
    gen = OpenAIImageGenerator("key")
    calls = []
    def fake(self, *args, **kwargs):
        calls.append(kwargs)
        return f"{prefix}.png"
    monkeypatch.setattr(OpenAIImageGenerator, "generate_image", fake)

    if method_name == "generate_seed_image":
        func = gen.generate_seed_image
        args = (2, str(tmp_path), "ref.png", "style")
    else:
        mask = tmp_path / "mask.png"
        mask.write_bytes(b"m")
        func = gen.generate_mosaic_image
        args = (5, str(tmp_path), "ref.png", str(mask), "style")

    out = func(*args)
    assert out == f"{prefix}.png"
    assert len(calls) == 1
    kwargs = calls[0]
    assert kwargs["prefix"] == prefix
    if method_name == "generate_mosaic_image":
        assert "mask" in kwargs
        assert hasattr(kwargs["mask"], "read")
    else:
        assert "mask" not in kwargs

def test_generate_image_text_only(tmp_path, monkeypatch, capsys):
    """generate_image works without reference_images, prints warning."""
    gen = OpenAIImageGenerator("key")
    # stub module.datetime.now().strftime(...)
    class DummyDT:
        @staticmethod
        def now():
            return DummyDT()
        def strftime(self, fmt):
            return "20250101_000000"
    monkeypatch.setattr(module, "datetime", DummyDT)

    # stub openai.images.edit
    img_bytes = b"xyz"
    b64 = base64.b64encode(img_bytes).decode()
    class StubResult:
        data = [SimpleNamespace(b64_json=b64)]
    monkeypatch.setattr(openai_sdk.images, "edit", lambda **kw: StubResult())

    # create output directory so generate_image can save into it
    outdir = tmp_path / "outdir"
    outdir.mkdir()

    out = gen.generate_image(
        prompt="p",
        output_path=str(outdir),
        reference_images=None,
        prefix="gen",
    )
    captured = capsys.readouterr()
    assert "no valid reference images" in captured.out.lower()

    expected = Path(outdir / "gen_20250101_000000.png")
    assert Path(out) == expected
    assert expected.exists()
    assert expected.read_bytes() == img_bytes

def test_generate_image_with_reference(tmp_path, monkeypatch):
    """generate_image uses provided reference file and closes it."""
    gen = OpenAIImageGenerator("key")
    class DummyDT2:
        @staticmethod
        def now():
            return DummyDT2()
        def strftime(self, fmt):
            return "20250102_010203"
    monkeypatch.setattr(module, "datetime", DummyDT2)

    ref = tmp_path / "ref.png"
    ref.write_bytes(b"abc")
    # create output directory
    outdir = tmp_path / "dir"
    outdir.mkdir()

    calls = {}
    def fake_edit(**kw):
        calls['image'] = kw.get("image")
        data = [SimpleNamespace(b64_json=base64.b64encode(b"123").decode())]
        return SimpleNamespace(data=data)
    monkeypatch.setattr(openai_sdk.images, "edit", fake_edit)

    out = gen.generate_image(
        prompt="p",
        output_path=str(outdir),
        reference_images=[str(ref)],
        prefix="pref",
        size="10x10",
    )
    img_file = calls['image']
    assert img_file.closed

    expected = Path(outdir / "pref_20250102_010203.png")
    assert Path(out) == expected
    assert expected.exists()

def test_test_api_key_success(monkeypatch):
    """test_api_key returns True on successful models.list()."""
    class DummyClient:
        def __init__(self, api_key): self.api_key = api_key
        class models:
            @staticmethod
            def list(): return ["model1"]
    monkeypatch.setattr(module, "OpenAI", DummyClient)

    gen = OpenAIImageGenerator("mykey")
    assert gen.test_api_key() is True

def test_test_api_key_failure(monkeypatch):
    """test_api_key raises ValueError on failure."""
    class DummyClient:
        def __init__(self, api_key): pass
        class models:
            @staticmethod
            def list(): raise RuntimeError("bad key")
    monkeypatch.setattr(module, "OpenAI", DummyClient)

    gen = OpenAIImageGenerator("k")
    with pytest.raises(ValueError) as exc:
        gen.test_api_key()
    assert "OpenAI API key test failed" in str(exc.value)
