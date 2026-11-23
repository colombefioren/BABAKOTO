import sys
import types
from typing import Any

import numpy as np
import pytest

from babakoto_stt.config import SttSettings
from babakoto_stt.engine import FakeEngine, SunflowerEngine, build_engine
from babakoto_stt.testing import tone


def settings() -> SttSettings:
    return SttSettings(
        _env_file=None,
        stt_engine="sunflower",
        allow_unauthenticated=True,
        sunflower_model_revision="rev1",
        sunflower_device="cpu",
    )


def test_fake_engine_reports_duration() -> None:
    result = FakeEngine("manao ahoana").transcribe(tone(2.0))
    assert result.text == "manao ahoana"
    assert result.language == "mlg"
    assert result.duration_s == pytest.approx(2.0)


def test_build_engine_picks_fake() -> None:
    cfg = SttSettings(_env_file=None, stt_engine="fake", allow_unauthenticated=True)
    assert isinstance(build_engine(cfg), FakeEngine)


def test_build_engine_picks_sunflower() -> None:
    assert isinstance(build_engine(settings()), SunflowerEngine)


def test_sunflower_transcribe_before_load_fails() -> None:
    with pytest.raises(RuntimeError, match="not loaded"):
        SunflowerEngine(settings()).transcribe(tone(0.1))


def test_sunflower_load_without_runtime_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "torch", None)
    with pytest.raises(RuntimeError, match="sunflower"):
        SunflowerEngine(settings()).load()


class _Tensor:
    def __init__(self) -> None:
        self.moved: list[Any] = []

    def to(self, *args: Any, **kwargs: Any) -> "_Tensor":
        self.moved.append((args, kwargs))
        return self


def _install_fake_runtime(monkeypatch: pytest.MonkeyPatch, calls: dict[str, Any]) -> None:
    torch = types.ModuleType("torch")
    torch.float16 = "fp16"  # type: ignore[attr-defined]
    torch.float32 = "fp32"  # type: ignore[attr-defined]

    class _Ctx:
        def __enter__(self) -> None:
            return None

        def __exit__(self, *_: object) -> None:
            return None

    torch.inference_mode = lambda: _Ctx()  # type: ignore[attr-defined]

    class Tokenizer:
        def convert_tokens_to_ids(self, token: str) -> int:
            return {"<|transcribe|>": 50359, "<|notimestamps|>": 50363}[token]

    class Processor:
        tokenizer = Tokenizer()

        @classmethod
        def from_pretrained(cls, model_id: str, **kwargs: Any) -> "Processor":
            calls["processor"] = (model_id, kwargs)
            return cls()

        def __call__(self, audio: Any, **_: Any) -> Any:
            return types.SimpleNamespace(input_features=_Tensor())

        def batch_decode(self, ids: Any, **_: Any) -> list[str]:
            return ["  manao ahoana  "]

    class Model:
        dtype = "fp32"

        @classmethod
        def from_pretrained(cls, model_id: str, **kwargs: Any) -> "Model":
            calls["model"] = (model_id, kwargs)
            return cls()

        def to(self, device: str) -> "Model":
            return self

        def eval(self) -> "Model":
            return self

        def generate(self, features: Any, **kwargs: Any) -> list[int]:
            calls["generate"] = kwargs
            return [1, 2, 3]

    transformers = types.ModuleType("transformers")
    transformers.WhisperProcessor = Processor  # type: ignore[attr-defined]
    transformers.WhisperForConditionalGeneration = Model  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "transformers", transformers)


def test_sunflower_loads_pinned_revision_and_forces_malagasy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}
    _install_fake_runtime(monkeypatch, calls)
    engine = SunflowerEngine(settings())
    engine.load()
    result = engine.transcribe(np.zeros(16000, dtype=np.float32))
    assert result.text == "manao ahoana"
    assert calls["model"][1]["revision"] == "rev1"
    assert calls["processor"][1]["revision"] == "rev1"
    assert calls["generate"]["forced_decoder_ids"] == [(1, 50349), (2, 50359), (3, 50363)]
    assert calls["generate"]["num_beams"] == 1
