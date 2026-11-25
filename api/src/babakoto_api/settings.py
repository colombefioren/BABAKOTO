"""Typed settings, validated at startup."""

import re
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from babakoto_common.auth import MIN_TOKEN_LENGTH


class Settings(BaseSettings):
    """API configuration read from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: SecretStr = SecretStr("")
    api_secret_key: SecretStr = SecretStr("")

    @field_validator("api_secret_key")
    @classmethod
    def check_key(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if secret and (
            len(secret) < MIN_TOKEN_LENGTH or not re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", secret)
        ):
            raise ValueError("API_SECRET_KEY must be a bearer token of at least 16 characters")
        return value

    @property
    def database_dsn(self) -> str:
        url = self.database_url.get_secret_value()
        if url.startswith("postgresql+psycopg://"):
            return url.replace("postgresql+psycopg://", "postgresql://", 1)
        return url


def get_settings() -> Settings:
    return Settings()
