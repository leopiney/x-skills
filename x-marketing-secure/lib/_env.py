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
* On POSIX, a .env is refused (skipped with a warning) unless it is owned by
  the current user and not readable or writable by group/others (chmod 600).
  Credentials in a world-readable file are readable by every local account.
"""
from __future__ import annotations

import os
import stat
import sys
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


def _private_enough(path: Path) -> bool:
    """True when `path` is a regular file owned by us with no group/other access."""
    if os.name != "posix":
        return True
    try:
        st = path.stat()
    except OSError:
        return False
    if not stat.S_ISREG(st.st_mode):
        return False
    if hasattr(os, "getuid") and st.st_uid != os.getuid():
        print(f"x-skills: ignoring {path}: not owned by the current user.", file=sys.stderr)
        return False
    if st.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        print(f"x-skills: ignoring {path}: readable by other users. "
              f"Fix with: chmod 600 {path}", file=sys.stderr)
        return False
    return True


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
            if not path.is_file() or not _private_enough(path):
                continue
            values = dotenv_values(path)
            for name in _DOTENV_VARIABLES:
                value = values.get(name)
                if value is not None:
                    os.environ.setdefault(name, value)
    except ImportError:
        pass

    _ENV_LOADED = True
