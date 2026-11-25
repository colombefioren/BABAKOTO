import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from babakoto_tts.config import TtsSettings
from babakoto_tts.engine import build_engine
from babakoto_tts.local_voice import LocalVoiceEngine


@pytest.fixture
def export(tmp_path: Path) -> Path:
    model = b"synthetic model fixture"
    config = json.dumps(
        {
            "audio": {"sample_rate": 24000},
            "phoneme_type": "text",
            "num_speakers": 1,
            "num_symbols": 6,
            "phoneme_id_map": {"_": [0], "^": [1], "$": [2], "a": [3], "b": [4], " ": [5]},
        }
    ).encode()
    (tmp_path / "voice.onnx").write_bytes(model)
    (tmp_path / "voice.onnx.json").write_bytes(config)
    (tmp_path / "provenance.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "trainer": "piper-tts==1.8.0",
                "base_weights": None,
                "corpus_receipt_sha256": "f" * 64,
                "config_sha256": hashlib.sha256(config).hexdigest(),
                "model_sha256": hashlib.sha256(model).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_local_voice_requires_consent_and_local_artifact(export: Path) -> None:
    options: dict[str, Any] = {
        "_env_file": None,
        "allow_unauthenticated": True,
        "tts_engine": "babakoto-tts",
        "babakoto_tts_model_path": str(export),
    }
    with pytest.raises(ValidationError, match="BABAKOTO_TTS_CONSENT_CONFIRMED"):
        TtsSettings(**options)

    config = TtsSettings(**options, babakoto_tts_consent_confirmed=True)
    assert isinstance(build_engine(config), LocalVoiceEngine)
    assert not config.allow_non_commercial_assets
    (export / "voice.onnx").write_bytes(b"model changed")
    with pytest.raises(ValueError, match="provenance"):
        build_engine(config).load()


def test_local_voice_maps_graphemes_and_returns_mono(
    export: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: dict[str, Any] = {}

    class Model:
        def __init__(self, model: bytes, *, sess_options: Any, providers: list[str]) -> None:
            assert providers == ["CPUExecutionProvider"]
            assert sess_options.intra_op_num_threads == 2
            assert model == b"synthetic model fixture"

        def get_inputs(self) -> list[SimpleNamespace]:
            return [SimpleNamespace(name=name) for name in ["input", "input_lengths", "scales"]]

        def get_outputs(self) -> list[SimpleNamespace]:
            return [SimpleNamespace(name="output")]

        def run(self, outputs: list[str], inputs: dict[str, Any]) -> list[Any]:
            calls.update(inputs)
            assert outputs == ["output"]
            return [np.zeros((1, 1, 1, 16), dtype=np.float32)]

    monkeypatch.setitem(
        sys.modules,
        "onnxruntime",
        SimpleNamespace(SessionOptions=SimpleNamespace, InferenceSession=Model),
    )
    engine = LocalVoiceEngine(export)
    with pytest.raises(RuntimeError, match="not loaded"):
        engine.synthesize("ab")
    engine.load()
    assert engine.synthesize("🚲").size == 0
    wave = engine.synthesize("AB")
    np.testing.assert_array_equal(calls["input"], [[1, 0, 3, 0, 4, 0, 2]])
    np.testing.assert_array_equal(calls["input_lengths"], [7])
    assert wave.shape == (16,)
    assert wave.dtype == np.float32
