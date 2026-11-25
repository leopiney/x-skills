"""Internal helper to load credentials from .env when python-dotenv is available.

Hardened fork notes:

* The upstream loader searched upward from the *current working directory*
  (`find_dotenv(usecwd=True)`). Any repository you happened to be working in,
  or any parent directory of it, could ship a .env that silently swapped in
  someone else's PUBLORA_API_KEY / X_PLATFORM_ID / PIXFARO_TOKEN, so approved
  drafts and generated images would land in an attacker-controlled account.
  This loader only reads two fixed, user-owned locations:

    1. `$XDG_CONFIG_HOME/x-skills/.env` (default `~/.config/x-skills/.env`)
    2. `<skill install dir>/.env` (this file's parent's parent)

* Only an allowlist of credential names is ever copied into the environment.
  Nothing this bundle executes or routes traffic through can come from a file.
* Variables already present in the launch environment always win.
"""
from __future__ import annotations

import os
from pathlib import Path

_ENV_LOADED = False
#: The only variables a .env may set.
_DOTENV_VARIABLES = (
    "APIFY_TOKEN", "PUBLORA_API_KEY", "X_PLATFORM_ID", "PIXFARO_TOKEN", "PIXFARO_API_KEY",
)


def env_candidates() -> list[Path]:
    """Where `load_env` looks, in order. Never derived from the cwd."""
    config_home = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    user_env = Path(config_home) / "x-skills" / ".env"
    skill_env = Path(__file__).resolve().parents[1] / ".env"
    out = [user_env]
    if skill_env != user_env:
        out.append(skill_env)
    return out


def load_env(force: bool = False) -> None:
    """Load allowlisted credentials from the fixed .env locations.

    Safe no-op if python-dotenv is missing, preserving Tier 0 (manual)
    zero-dependency operation. Existing environment variables are preserved.
    """
    global _ENV_LOADED
    if _ENV_LOADED and not force:
        return

    try:
        from dotenv import dotenv_values

        for path in env_candidates():
            if not path.is_file():
                continue
            values = dotenv_values(path)
            for name in _DOTENV_VARIABLES:
                value = values.get(name)
                if value is not None:
                    os.environ.setdefault(name, value)
    except ImportError:
        pass

    _ENV_LOADED = True
