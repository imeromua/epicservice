import os
import sys
from pathlib import Path


def _add_repo_root_to_syspath() -> None:
    """Ensure repo root is importable (so `import webapp`, `import database` work)."""
    root = Path(__file__).resolve().parents[1]
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def _set_default_env(name: str, value: str) -> None:
    if not os.getenv(name):
        os.environ[name] = value


_add_repo_root_to_syspath()

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
