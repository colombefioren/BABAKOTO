"""Typed settings, validated at startup."""

import re
from typing import Literal

from pydantic import SecretStr, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from babakoto_common.auth import MIN_TOKEN_LENGTH


class Settings(BaseSettings):
    """API configuration read from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: SecretStr = SecretStr("")
    api_secret_key: SecretStr = SecretStr("")
    agent_config_read_token: SecretStr = SecretStr("")

    @field_validator("api_secret_key", "agent_config_read_token")
    @classmethod
    def check_key(cls, value: SecretStr, info: ValidationInfo) -> SecretStr:
        secret = value.get_secret_value()
        if secret and (
            len(secret) < MIN_TOKEN_LENGTH or not re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", secret)
        ):
            field = (info.field_name or "credential").upper()
            raise ValueError(f"{field} must be a bearer token of at least 16 characters")
        return value

    @model_validator(mode="after")
    def separate_runtime_key(self) -> "Settings":
        if (
            self.agent_config_read_token.get_secret_value()
            and self.agent_config_read_token == self.api_secret_key
        ):
            raise ValueError("AGENT_CONFIG_READ_TOKEN must differ from API_SECRET_KEY")
        return self

    @property
    def database_dsn(self) -> str:
        url = self.database_url.get_secret_value()
        if url.startswith("postgresql+psycopg://"):
            return url.replace("postgresql+psycopg://", "postgresql://", 1)
        return url


def get_settings() -> Settings:
    return Settings()
