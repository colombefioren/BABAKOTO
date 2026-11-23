import logging
import sys
import types
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from babakoto_tts.config import TtsSettings
from babakoto_tts.engine import FakeEngine, MmsEngine, OmniVoiceEngine, build_engine


def omnivoice_settings(tmp_path: Path) -> TtsSettings:
    clip = tmp_path / "ref.wav"
    clip.write_bytes(b"RIFF")
    return TtsSettings(
        _env_file=None,
        allow_unauthenticated=True,
        tts_engine="omnivoice",
        allow_non_commercial_assets=True,
        omnivoice_model_revision="rev1",
        tts_reference_audio_path=str(clip),
        tts_reference_text="salama",
    )


def mms_settings() -> TtsSettings:
    return TtsSettings(
        _env_file=None,
        allow_unauthenticated=True,
        tts_engine="mms",
        allow_non_commercial_assets=True,
        mms_model_revision="rev2",
        mms_device="cpu",
    )


def test_fake_engine_length_follows_text() -> None:
    engine = FakeEngine()
    short = engine.synthesize("a")
    long = engine.synthesize("a" * 100)
    assert long.size > short.size
    assert long.dtype == np.float32


def test_build_engine_warns_for_non_commercial(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        assert isinstance(build_engine(mms_settings()), MmsEngine)
        assert isinstance(build_engine(omnivoice_settings(tmp_path)), OmniVoiceEngine)
    assert caplog.text.count("NON-COMMERCIAL") == 2


def test_build_engine_fake_does_not_warn(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        build_engine(TtsSettings(_env_file=None, tts_engine="fake", allow_unauthenticated=True))
    assert "NON-COMMERCIAL" not in caplog.text


def test_engines_refuse_to_synthesize_before_load(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="not loaded"):
        OmniVoiceEngine(omnivoice_settings(tmp_path)).synthesize("x")
    with pytest.raises(RuntimeError, match="not loaded"):
        MmsEngine(mms_settings()).synthesize("x")


def test_missing_runtime_is_reported_clearly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setitem(sys.modules, "torch", None)
    with pytest.raises(RuntimeError, match="omnivoice"):
        OmniVoiceEngine(omnivoice_settings(tmp_path)).load()
    with pytest.raises(RuntimeError, match="mms"):
        MmsEngine(mms_settings()).load()


def test_omnivoice_pins_revision_and_clones_reference(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: dict[str, Any] = {}
    torch = types.ModuleType("torch")
    torch.float16 = "fp16"  # type: ignore[attr-defined]
    hub = types.ModuleType("huggingface_hub")

    def snapshot_download(repo: str, **kwargs: Any) -> str:
        calls["download"] = (repo, kwargs)
        return "/local/model"

    hub.snapshot_download = snapshot_download  # type: ignore[attr-defined]

    class Model:
        @classmethod
        def from_pretrained(cls, path: str, **kwargs: Any) -> "Model":
            calls["load"] = (path, kwargs)
            return cls()

        def create_voice_clone_prompt(self, **kwargs: Any) -> str:
            calls["prompt"] = kwargs
            return "PROMPT"

        def generate(self, **kwargs: Any) -> list[np.ndarray]:
            calls["generate"] = kwargs
            return [np.ones(240, dtype=np.float64)]

    module = types.ModuleType("omnivoice")
    module.OmniVoice = Model  # type: ignore[attr-defined]
    for name, mod in (("torch", torch), ("huggingface_hub", hub), ("omnivoice", module)):
        monkeypatch.setitem(sys.modules, name, mod)

    cfg = omnivoice_settings(tmp_path)
    engine = OmniVoiceEngine(cfg)
    engine.load()
    audio = engine.synthesize("salama")
    assert calls["download"][1]["revision"] == "rev1"
    assert calls["load"][0] == "/local/model"
    assert calls["prompt"] == {
        "ref_audio": cfg.tts_reference_audio_path,
        "ref_text": "salama",
    }
    assert calls["generate"] == {"text": "salama", "voice_clone_prompt": "PROMPT"}
    assert audio.dtype == np.float32
    assert audio.size == 240


def test_mms_loads_pinned_revision_and_returns_waveform(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    class _Ctx:
        def __enter__(self) -> None:
            return None

        def __exit__(self, *_: object) -> None:
            return None

    torch = types.ModuleType("torch")
    torch.inference_mode = lambda: _Ctx()  # type: ignore[attr-defined]

    class Inputs(dict[str, Any]):
        def to(self, device: str) -> "Inputs":
            return self

    class Tokenizer:
        @classmethod
        def from_pretrained(cls, model_id: str, **kwargs: Any) -> "Tokenizer":
            calls["tokenizer"] = kwargs
            return cls()

        def __call__(self, text: str, **_: Any) -> Inputs:
            return Inputs(input_ids=[1])

    class Waveform:
        def float(self) -> "Waveform":
            return self

        def cpu(self) -> "Waveform":
            return self

        def numpy(self) -> np.ndarray:
            return np.zeros(160, dtype=np.float32)

    class Model:
        config = types.SimpleNamespace(sampling_rate=16000)

        @classmethod
        def from_pretrained(cls, model_id: str, **kwargs: Any) -> "Model":
            calls["model"] = kwargs
            return cls()

        def to(self, device: str) -> "Model":
            return self

        def eval(self) -> "Model":
            return self

        def __call__(self, **_: Any) -> Any:
            return types.SimpleNamespace(waveform=[Waveform()])

    transformers = types.ModuleType("transformers")
    transformers.AutoTokenizer = Tokenizer  # type: ignore[attr-defined]
    transformers.VitsModel = Model  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "transformers", transformers)

    engine = MmsEngine(mms_settings())
    engine.load()
    audio = engine.synthesize("salama")
    assert calls["model"]["revision"] == "rev2"
    assert calls["tokenizer"]["revision"] == "rev2"
    assert audio.size == 160
    assert engine.sample_rate == 16000
