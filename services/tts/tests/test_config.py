from pathlib import Path

import pytest
from pydantic import ValidationError

from babakoto_tts.config import TtsSettings


def make(**kwargs: object) -> TtsSettings:
    kwargs.setdefault("allow_unauthenticated", True)
    kwargs.setdefault("allow_unauthenticated", True)
    return TtsSettings(_env_file=None, **kwargs)  # type: ignore[arg-type]


def test_fake_engine_needs_nothing() -> None:
    assert make(tts_engine="fake").tts_engine == "fake"


def test_non_commercial_engines_are_blocked_by_default() -> None:
    with pytest.raises(ValidationError, match="ALLOW_NON_COMMERCIAL_ASSETS"):
        make(tts_engine="omnivoice")
    with pytest.raises(ValidationError, match="non-commercial"):
        make(tts_engine="mms", mms_model_revision="abc")


def test_default_engine_refuses_to_start_without_the_flag() -> None:
    with pytest.raises(ValidationError, match="non-commercial"):
        make()


def test_omnivoice_lists_every_missing_setting() -> None:
    with pytest.raises(ValidationError) as info:
        make(tts_engine="omnivoice", allow_non_commercial_assets=True)
    message = str(info.value)
    for name in ("OMNIVOICE_MODEL_REVISION", "TTS_REFERENCE_AUDIO_PATH", "TTS_REFERENCE_TEXT"):
        assert name in message


def test_omnivoice_reference_file_must_exist(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="does not point to a file"):
        make(
            tts_engine="omnivoice",
            allow_non_commercial_assets=True,
            omnivoice_model_revision="abc",
            tts_reference_audio_path=str(tmp_path / "missing.wav"),
            tts_reference_text="salama",
        )


def test_omnivoice_valid(tmp_path: Path) -> None:
    clip = tmp_path / "ref.wav"
    clip.write_bytes(b"RIFF")
    cfg = make(
        tts_engine="omnivoice",
        allow_non_commercial_assets=True,
        omnivoice_model_revision="abc",
        tts_reference_audio_path=str(clip),
        tts_reference_text="salama",
    )
    assert cfg.omnivoice_model_revision == "abc"


def test_mms_needs_revision() -> None:
    with pytest.raises(ValidationError, match="MMS_MODEL_REVISION"):
        make(tts_engine="mms", allow_non_commercial_assets=True)


def test_service_token_is_required_by_default() -> None:
    marker = "synthetic-validation-marker"
    with pytest.raises(ValidationError, match="SERVICE_TOKEN") as error:
        make(tts_engine="fake", allow_unauthenticated=False, hf_token=marker)
    assert marker not in str(error.value)


def test_short_service_token_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least"):
        make(tts_engine="fake", allow_unauthenticated=False, service_token="short")
