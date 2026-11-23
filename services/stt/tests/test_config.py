import pytest
from pydantic import ValidationError

from babakoto_stt.config import SttSettings


def test_sunflower_requires_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUNFLOWER_MODEL_REVISION", raising=False)
    with pytest.raises(ValidationError, match="SUNFLOWER_MODEL_REVISION"):
        SttSettings(_env_file=None, stt_engine="sunflower")


def test_fake_engine_needs_no_revision() -> None:
    assert SttSettings(_env_file=None, stt_engine="fake").stt_engine == "fake"


def test_revision_accepted() -> None:
    cfg = SttSettings(_env_file=None, stt_engine="sunflower", sunflower_model_revision="abc123")
    assert cfg.sunflower_language_token_id == 50349
