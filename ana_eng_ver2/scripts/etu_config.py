#!/usr/bin/env python3
"""Configure ETU API keys — per-user, stored outside the repo.

This is the "separate API-key port": instead of editing ~/.bashrc on every
machine, store each provider's key once in ~/.config/etu/config.json (chmod 600).
Every pipeline (etu_understand, etu_comprehend, run_pipeline) reads it as a
fallback when the corresponding environment variable is absent.

    python scripts/etu_config.py set deepseek            # interactive (hidden input)
    python scripts/etu_config.py set deepseek --key sk-...   # non-interactive
    python scripts/etu_config.py get                     # list configured providers (redacted)
    python scripts/etu_config.py unset deepseek          # remove a provider's key
    python scripts/etu_config.py path                    # print the config file location

Key priority when the engine runs: environment variable > this config file.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mmi.etu.comprehend.credentials import (  # noqa: E402
    config_path,
    get_api_key,
    load,
    set_api_key,
    unset_api_key,
)

# provider name -> environment variable, used as a convenience fallback in `set`
_ENV_FOR = {
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def _redact(key: str) -> str:
    if not key:
        return "(no key)"
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"


def cmd_set(args: argparse.Namespace) -> int:
    provider = args.provider
    key = args.key
    if not key:
        key = os.environ.get(_ENV_FOR.get(provider, ""), "") or ""
    if not key:
        key = getpass.getpass(f"API key for {provider}: ").strip()
    if not key:
        print("no key provided — nothing saved.")
        return 1
    path = set_api_key(provider, key)
    print(f"saved {provider} key -> {path}")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    providers = load().get("providers", {})
    if not providers:
        print("no providers configured.")
        print("set one with: python scripts/etu_config.py set <provider>")
        return 0
    for name, cfg in sorted(providers.items()):
        print(f"{name:12s} {_redact(cfg.get('api_key', '') if isinstance(cfg, dict) else '')}")
    return 0


def cmd_unset(args: argparse.Namespace) -> int:
    unset_api_key(args.provider)
    print(f"removed {args.provider} from {config_path()}")
    return 0


def cmd_path(args: argparse.Namespace) -> int:
    print(config_path())
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_set = sub.add_parser("set", help="store a provider's API key")
    p_set.add_argument("provider", help="provider name (deepseek, openai, gemini, openrouter, ...)")
    p_set.add_argument("--key", help="key value (prompts interactively if omitted)")
    p_set.set_defaults(func=cmd_set)

    p_get = sub.add_parser("get", help="list configured providers (keys redacted)")
    p_get.set_defaults(func=cmd_get)

    p_unset = sub.add_parser("unset", help="remove a provider's key")
    p_unset.add_argument("provider")
    p_unset.set_defaults(func=cmd_unset)

    p_path = sub.add_parser("path", help="print the config file location")
    p_path.set_defaults(func=cmd_path)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
