"""Typed settings for the agent worker, validated at startup."""

from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


class AgentSettings(BaseSettings):
    """Agent configuration read from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    stt_provider: Literal["sunflower", "gladia", "babakoto-asr"] = "sunflower"
    gladia_api_key: SecretStr = SecretStr("")
    llm_provider: Literal["anthropic", "openai", "google", "openai-compatible"] = "anthropic"
    llm_model: str = ""
    openai_compatible_base_url: str = ""
    openai_compatible_api_key: str = ""

    # Our speech services. Both need the shared service token.
    stt_service_url: str = "http://localhost:8001"
    tts_service_url: str = "http://localhost:8002"
    service_token: str = ""
    # Sample rate the TTS engine produces: 24000 for OmniVoice, 16000 for MMS.
    tts_sample_rate: int = 24_000
    service_timeout_s: float = 30.0

    # Conversation behavior.
    # Folder holding default.mg.md and first_message.mg.txt. Containers set this explicitly.
    prompts_dir: Path = DEFAULT_PROMPTS_DIR
    system_prompt_path: str = ""
    first_message_path: str = ""
    agent_config_api_url: str = ""
    agent_config_read_token: SecretStr = SecretStr("")
    # Silence after the user stops before the agent answers.
    endpointing_min_delay_s: float = 0.4
    endpointing_max_delay_s: float = 2.0
    # Speech needed to count as an interruption: the barge-in budget is 300 ms.
    interruption_min_duration_s: float = 0.2
    vad_min_silence_s: float = 0.3

    @model_validator(mode="after")
    def _validate(self) -> "AgentSettings":
        if not self.service_token:
            raise ValueError("SERVICE_TOKEN is required to call the Babakoto speech services")
        if self.stt_provider == "gladia" and not self.gladia_api_key.get_secret_value().strip():
            raise ValueError("STT_PROVIDER=gladia needs GLADIA_API_KEY")
        if self.llm_provider == "openai-compatible" and not (
            self.openai_compatible_base_url and self.llm_model
        ):
            raise ValueError(
                "LLM_PROVIDER=openai-compatible needs OPENAI_COMPATIBLE_BASE_URL and LLM_MODEL"
            )
        return self

    @property
    def system_prompt(self) -> str:
        path = (
            Path(self.system_prompt_path)
            if self.system_prompt_path
            else self.prompts_dir / "default.mg.md"
        )
        return path.read_text(encoding="utf-8").strip()

    @property
    def first_message(self) -> str:
        path = (
            Path(self.first_message_path)
            if self.first_message_path
            else self.prompts_dir / "first_message.mg.txt"
        )
        return path.read_text(encoding="utf-8").strip()
