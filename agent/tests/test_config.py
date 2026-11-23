from pathlib import Path

import pytest
from pydantic import ValidationError

from babakoto_agent.config import DEFAULT_PROMPTS_DIR, AgentSettings

TOKEN = "t" * 24


def make(**kwargs: object) -> AgentSettings:
    kwargs.setdefault("service_token", TOKEN)
    return AgentSettings(_env_file=None, **kwargs)  # type: ignore[arg-type]


def test_service_token_is_required() -> None:
    with pytest.raises(ValidationError, match="SERVICE_TOKEN"):
        AgentSettings(_env_file=None)


def test_openai_compatible_needs_url_and_model() -> None:
    with pytest.raises(ValidationError, match="OPENAI_COMPATIBLE_BASE_URL"):
        make(llm_provider="openai-compatible")
    cfg = make(
        llm_provider="openai-compatible",
        openai_compatible_base_url="http://llm:8000/v1",
        llm_model="m",
    )
    assert cfg.llm_model == "m"


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make(llm_provider="nope")


def test_default_prompts_are_loaded_from_the_repo() -> None:
    cfg = make()
    assert cfg.system_prompt.startswith("Ianao dia mpanampy")
    assert cfg.first_message.startswith("Salama")


def test_prompt_paths_can_be_overridden(tmp_path: Path) -> None:
    prompt = tmp_path / "p.md"
    prompt.write_text("  hello  \n", encoding="utf-8")
    greeting = tmp_path / "g.txt"
    greeting.write_text("bonjour\n", encoding="utf-8")
    cfg = make(system_prompt_path=str(prompt), first_message_path=str(greeting))
    assert cfg.system_prompt == "hello"
    assert cfg.first_message == "bonjour"


def test_prompts_dir_can_be_moved(tmp_path: Path) -> None:
    (tmp_path / "default.mg.md").write_text("x", encoding="utf-8")
    assert make(prompts_dir=tmp_path).system_prompt == "x"


def test_every_malagasy_prompt_has_an_english_translation() -> None:
    for mg in DEFAULT_PROMPTS_DIR.glob("*.mg.*"):
        en = mg.with_name(mg.name.replace(".mg.", ".en."))
        assert en.exists(), f"missing translation for {mg.name}"


def test_prompt_enforces_the_voice_rules() -> None:
    text = make().system_prompt
    for rule in ("markdown", "emoji", "Frantsay", "olombelona"):
        assert rule in text
