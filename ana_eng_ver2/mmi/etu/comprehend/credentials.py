"""Per-user API-key store for ETU's reasoning/vision providers.

ETU is meant to be distributable, so requiring users to edit ~/.bashrc for every
provider key is hostile. Keys live in a per-user config file OUTSIDE the repo
(~/.config/etu/config.json, chmod 600) and the LLM client falls back to it when
the environment variable is absent. Env var still wins — backwards compatible.

Manage via the CLI (the "separate API-key port"):

    python scripts/etu_config.py set deepseek            # interactive (hidden input)
    python scripts/etu_config.py set deepseek --key sk-...
    python scripts/etu_config.py get                     # list providers (redacted)
    python scripts/etu_config.py unset deepseek
    python scripts/etu_config.py path                    # print config file location

Config file shape:

    {"providers": {"deepseek": {"api_key": "sk-..."}}}
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "etu"


def config_path() -> Path:
    return config_dir() / "config.json"


def load() -> dict:
    """Read the config file; return {} if missing or unreadable."""
    p = config_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save(data: dict) -> Path:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))
    try:
        os.chmod(p, 0o600)  # secret — keep it owner-only
    except OSError:
        pass
    return p


def get_api_key(provider: str) -> str | None:
    return (load().get("providers", {}).get(provider, {}) or {}).get("api_key") or None


def set_api_key(provider: str, api_key: str) -> Path:
    data = load()
    data.setdefault("providers", {}).setdefault(provider, {})["api_key"] = api_key
    return save(data)


def unset_api_key(provider: str) -> Path:
    data = load()
    data.get("providers", {}).pop(provider, None)
    return save(data)
