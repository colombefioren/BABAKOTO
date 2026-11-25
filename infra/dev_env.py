"""Initialize local Compose credentials while preserving existing settings."""

import os
import secrets
from pathlib import Path

from dotenv import dotenv_values, set_key


def main() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        template = Path(".env.example").read_text(encoding="utf-8")
        fd = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as env_file:
            env_file.write(template)

    values = dotenv_values(env_path, interpolate=False)
    credentials = (
        ("LIVEKIT_API_KEY", 16),
        ("LIVEKIT_API_SECRET", 32),
        ("SERVICE_TOKEN", 32),
        ("WEB_PLAYGROUND_PASSWORD", 32),
        ("API_SECRET_KEY", 32),
        ("POSTGRES_PASSWORD", 32),
    )
    for name, size in credentials:
        if not values.get(name):
            env_path.chmod(0o600)
            set_key(env_path, name, secrets.token_hex(size), follow_symlinks=True)


if __name__ == "__main__":
    main()
