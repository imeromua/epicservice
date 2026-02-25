import os


def _set_default_env(name: str, value: str) -> None:
    if not os.getenv(name):
        os.environ[name] = value


# Ensure required env vars exist so importing project modules doesn't fail in CI.
_set_default_env("BOT_TOKEN", "TEST:TOKEN")

# Use real Postgres in CI via service container. For local run, these defaults are harmless.
_set_default_env("DB_HOST", "localhost")
_set_default_env("DB_PORT", "5432")
_set_default_env("DB_NAME", "epicservice")
_set_default_env("DB_USER", "epicuser")
_set_default_env("DB_PASSWORD", "password")

# Disable redis for tests unless explicitly enabled.
_set_default_env("REDIS_ENABLED", "false")
_set_default_env("WEBAPP_ADMIN_IDS", "")
