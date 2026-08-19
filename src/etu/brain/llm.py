"""Provider-neutral chat client over seven LLM endpoints.

Only two request shapes exist in practice: the OpenAI chat-completions API,
which most vendors and local servers imitate, and Anthropic's messages API.
Everything else is a base URL, a key and a default model.
"""

from __future__ import annotations

import functools
import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

ANTHROPIC_VERSION = "2023-06-01"
ANTHROPIC_MAX_TOKENS = 2048

_PROVIDERS: dict[str, dict[str, str]] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
        "flavor": "openai",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env": "ANTHROPIC_API_KEY",
        "model": "claude-sonnet-4-20250514",
        "flavor": "anthropic",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key_env": "GEMINI_API_KEY",
        "model": "gemini-2.5-flash",
        "flavor": "openai",
    },
    "lmstudio": {
        "base_url": "http://localhost:1234/v1",
        "api_key_env": "",
        "model": "local-model",
        "flavor": "openai",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key_env": "",
        "model": "qwen2.5:7b",
        "flavor": "openai",
    },
    "opencode": {
        "base_url": "http://localhost:4080/v1",
        "api_key_env": "",
        "model": "opencode/default",
        "flavor": "openai",
    },
    "openapi": {
        "base_url": "",  # taken from ETU_OPENAPI_BASE_URL at call time
        "api_key_env": "ETU_OPENAPI_API_KEY",
        "model": "default",
        "flavor": "openai",
    },
}


class LLMError(RuntimeError):
    """Any failure to obtain a usable reply from a provider."""


@dataclass
class LLMConfig:
    provider: str = "openai"
    model: str = ""
    base_url: str = ""
    api_key_env: str = ""
    temperature: float = 0.2
    timeout: float = 60.0


def providers() -> list[str]:
    return sorted(_PROVIDERS)


def _resolve(cfg: LLMConfig) -> dict[str, str]:
    spec = _PROVIDERS.get(cfg.provider)
    if spec is None:
        raise LLMError(
            f"unknown provider {cfg.provider!r}; choose one of {', '.join(providers())}"
        )

    base_url = cfg.base_url or spec["base_url"]
    if cfg.provider == "openapi" and not base_url:
        base_url = os.environ.get("ETU_OPENAPI_BASE_URL", "")
    if not base_url:
        raise LLMError(
            "provider 'openapi' needs a base URL: set ETU_OPENAPI_BASE_URL or "
            "pass LLMConfig(base_url=...)"
        )

    return {
        "base_url": base_url.rstrip("/"),
        "api_key_env": cfg.api_key_env or spec["api_key_env"],
        "model": cfg.model or spec["model"],
        "flavor": spec["flavor"],
    }


def describe(cfg: LLMConfig) -> str:
    spec = _resolve(cfg)
    env = spec["api_key_env"]
    if not env:
        key = "key: none needed"
    elif os.environ.get(env):
        key = f"key: {env} set"
    else:
        key = f"key: {env} MISSING"
    return f"{cfg.provider} {spec['model']} @ {spec['base_url']} ({key})"


def _api_key(env: str) -> str:
    if not env:
        return ""
    key = os.environ.get(env, "")
    if not key:
        raise LLMError(f"missing API key: set the {env} environment variable")
    return key


def _send_http(
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout: float = 60.0,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        raise LLMError(f"{url} returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise LLMError(f"could not reach {url}: {exc}") from exc

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise LLMError(f"{url} returned non-JSON body: {payload[:200]}") from exc
    if not isinstance(parsed, dict):
        raise LLMError(
            f"{url} returned {type(parsed).__name__}, expected a JSON object"
        )
    return parsed


def _openai_request(
    spec: dict[str, str], cfg: LLMConfig, system: str, user: str
) -> tuple[str, dict[str, str], dict[str, Any]]:
    key = _api_key(spec["api_key_env"])
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    body = {
        "model": spec["model"],
        "temperature": cfg.temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    return f"{spec['base_url']}/chat/completions", headers, body


def _anthropic_request(
    spec: dict[str, str], cfg: LLMConfig, system: str, user: str
) -> tuple[str, dict[str, str], dict[str, Any]]:
    headers = {
        "x-api-key": _api_key(spec["api_key_env"]),
        "anthropic-version": ANTHROPIC_VERSION,
    }
    body = {
        "model": spec["model"],
        "max_tokens": ANTHROPIC_MAX_TOKENS,
        "temperature": cfg.temperature,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    return f"{spec['base_url']}/messages", headers, body


def _openai_text(reply: dict[str, Any]) -> str:
    try:
        return reply["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"unexpected reply shape: {json.dumps(reply)[:200]}") from exc


def _anthropic_text(reply: dict[str, Any]) -> str:
    try:
        return reply["content"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"unexpected reply shape: {json.dumps(reply)[:200]}") from exc


def chat(
    system: str,
    user: str,
    cfg: LLMConfig | None = None,
    send: Callable[[str, dict, dict], dict] | None = None,
) -> str:
    cfg = cfg or LLMConfig()
    spec = _resolve(cfg)

    if spec["flavor"] == "anthropic":
        url, headers, body = _anthropic_request(spec, cfg, system, user)
        extract = _anthropic_text
    else:
        url, headers, body = _openai_request(spec, cfg, system, user)
        extract = _openai_text

    if send is None:
        send = functools.partial(_send_http, timeout=cfg.timeout)

    reply = send(url, headers, body)
    if not isinstance(reply, dict):
        raise LLMError(f"sender returned {type(reply).__name__}, expected a dict")

    text = extract(reply)
    if not isinstance(text, str):
        raise LLMError(f"reply text was {type(text).__name__}, expected a string")
    return text


def chat_json(
    system: str,
    user: str,
    cfg: LLMConfig | None = None,
    send: Callable[[str, dict, dict], dict] | None = None,
) -> dict:
    text = chat(system, user, cfg, send)
    obj = _extract_json_object(text)
    if obj is None:
        raise LLMError(f"no JSON object found in reply: {text[:200]}")
    return obj


def _extract_json_object(text: str) -> dict | None:
    for candidate in (_strip_fences(text), _first_braced_span(text)):
        if candidate is None:
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _strip_fences(text: str) -> str:
    body = text.strip()
    if not body.startswith("```"):
        return body
    lines = body.splitlines()
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines[1:]).strip()


def _first_braced_span(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\" and in_string:
            escaped = True
        elif char == '"':
            in_string = not in_string
        elif in_string:
            continue
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None
