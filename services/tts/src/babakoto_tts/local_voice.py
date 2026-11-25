"""Run an operator-supplied Babakoto voice export through ONNX Runtime."""

import hashlib
from importlib import import_module
from pathlib import Path
from typing import Annotated, Any, Literal

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field

from malagasy_text.graphemes import voice_graphemes

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class VoiceProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = Field(alias="schema")
    trainer: Literal["piper-tts==1.8.0"]
    base_weights: None
    corpus_receipt_sha256: Digest
    config_sha256: Digest
    model_sha256: Digest


class VoiceAudio(BaseModel):
    sample_rate: Literal[24_000]


class VoiceScales(BaseModel):
    noise_scale: float = Field(default=0.667, ge=0, le=2)
    length_scale: float = Field(default=1.0, ge=0.25, le=4)
    noise_w: float = Field(default=0.8, ge=0, le=2)


class VoiceConfig(BaseModel):
    audio: VoiceAudio
    phoneme_type: Literal["text"]
    num_speakers: Literal[1]
    num_symbols: int = Field(gt=3)
    phoneme_id_map: dict[str, list[int]]
    inference: VoiceScales = Field(default_factory=VoiceScales)


class LocalVoiceEngine:
    sample_rate = 24_000

    def __init__(self, model_dir: Path) -> None:
        self._path = model_dir
        self._session: Any = None
        self._config: VoiceConfig | None = None

    def load(self) -> None:
        provenance = VoiceProvenance.model_validate_json(
            (self._path / "provenance.json").read_bytes()
        )
        config_data = (self._path / "voice.onnx.json").read_bytes()
        model = (self._path / "voice.onnx").read_bytes()
        if (
            hashlib.sha256(config_data).hexdigest() != provenance.config_sha256
            or hashlib.sha256(model).hexdigest() != provenance.model_sha256
        ):
            raise ValueError("local voice files do not match their export provenance")

        config = VoiceConfig.model_validate_json(config_data)
        alphabet = config.phoneme_id_map
        if (
            len(alphabet) != config.num_symbols
            or any(len(char) != 1 for char in alphabet)
            or sorted(alphabet.values()) != [[i] for i in range(config.num_symbols)]
            or any(alphabet.get(char) != [i] for i, char in enumerate("_^$"))
        ):
            raise ValueError("local voice configuration has an invalid grapheme map")
        try:
            ort = import_module("onnxruntime")
        except ImportError as exc:
            raise RuntimeError("install babakoto-tts with the `local` extra") from exc

        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        session = ort.InferenceSession(
            model, sess_options=options, providers=["CPUExecutionProvider"]
        )
        if {item.name for item in session.get_inputs()} != {"input", "input_lengths", "scales"}:
            raise ValueError("local voice graph does not accept the single-speaker inputs")
        if {item.name for item in session.get_outputs()} != {"output"}:
            raise ValueError("local voice graph does not provide the waveform output")
        self._session = session
        self._config = config

    def synthesize(self, text: str) -> npt.NDArray[np.float32]:
        if self._config is None:
            raise RuntimeError("engine is not loaded")
        alphabet = self._config.phoneme_id_map
        graphemes = [char for char in voice_graphemes(text) if char in alphabet]
        if not graphemes:
            return np.empty(0, dtype=np.float32)
        ids = [1, 0]
        for char in graphemes:
            ids.extend((alphabet[char][0], 0))
        ids.append(2)

        scale = self._config.inference
        [output] = self._session.run(
            ["output"],
            {
                "input": np.asarray([ids], dtype=np.int64),
                "input_lengths": np.asarray([len(ids)], dtype=np.int64),
                "scales": np.asarray(
                    [scale.noise_scale, scale.length_scale, scale.noise_w], dtype=np.float32
                ),
            },
        )
        samples = np.asarray(output, dtype=np.float32)
        if samples.ndim < 2 or any(size != 1 for size in samples.shape[:-1]):
            raise RuntimeError("local voice output is not a mono waveform")
        if not samples.size or not np.isfinite(samples).all():
            raise RuntimeError("local voice returned invalid samples")
        return samples.reshape(-1)
