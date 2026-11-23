import pytest
from pydantic import ValidationError

from babakoto_stt.config import SttSettings


def test_sunflower_requires_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUNFLOWER_MODEL_REVISION", raising=False)
    with pytest.raises(ValidationError, match="SUNFLOWER_MODEL_REVISION"):
        SttSettings(_env_file=None, stt_engine="sunflower", allow_unauthenticated=True)


def test_fake_engine_needs_no_revision() -> None:
    assert (
        SttSettings(_env_file=None, stt_engine="fake", allow_unauthenticated=True).stt_engine
        == "fake"
    )


def test_revision_accepted() -> None:
    cfg = SttSettings(
        _env_file=None,
        stt_engine="sunflower",
        allow_unauthenticated=True,
        sunflower_model_revision="abc123",
    )
    assert cfg.sunflower_language_token_id == 50349


def test_service_token_is_required_by_default() -> None:
    with pytest.raises(ValidationError, match="SERVICE_TOKEN"):
        SttSettings(_env_file=None, stt_engine="fake")


def test_short_service_token_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least"):
        SttSettings(_env_file=None, stt_engine="fake", service_token="short")


def test_valid_service_token_is_accepted() -> None:
    assert SttSettings(_env_file=None, stt_engine="fake", service_token="x" * 16).service_token
