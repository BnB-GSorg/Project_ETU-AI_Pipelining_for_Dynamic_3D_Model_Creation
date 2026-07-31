"""Model-agnostic chat client (OpenAI-compatible HTTP, no third-party deps).

Default provider is DeepSeek (cheap, text-only). The interface is deliberately
provider-neutral: to use a *vision* model later (so the system can read frames
directly instead of via transcript/OCR), add a provider here and pass image
parts — nothing else in ETU changes.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, replace
from pathlib import Path


@dataclass
class LLMConfig:
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    api_key_env: str = "DEEPSEEK_API_KEY"
    temperature: float = 0.0
    vision: bool = False


PROVIDERS: dict[str, LLMConfig] = {
    # --- text "brain": closed-set classification from text evidence ---
    "deepseek": LLMConfig("deepseek", "deepseek-chat", "https://api.deepseek.com", "DEEPSEEK_API_KEY", 0.0, False),
    # --- vision "eye": describe frames (all OpenAI-compatible chat/completions) ---
    "openai": LLMConfig("openai", "gpt-4o-mini", "https://api.openai.com/v1", "OPENAI_API_KEY", 0.0, True),
    # Gemini Flash via its OpenAI-compatible endpoint (cheap, strong on images).
    # 2.5-flash chosen: 1.5-* are retired (404) and 2.0-flash has 0 free-tier quota.
    "gemini": LLMConfig("gemini", "gemini-2.5-flash",
                        "https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY", 0.0, True),
    # OpenRouter exposes many vision models (e.g. Qwen-VL) behind one key
    "openrouter": LLMConfig("openrouter", "qwen/qwen-2.5-vl-72b-instruct",
                            "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", 0.0, True),
}


def make_config(provider: str = "deepseek", model: str | None = None) -> LLMConfig:
    if provider not in PROVIDERS:
        raise KeyError(f"unknown provider {provider!r}; known: {sorted(PROVIDERS)}")
    cfg = replace(PROVIDERS[provider])
    if model:
        cfg.model = model
    return cfg


def chat(cfg: LLMConfig, system: str, user: str, json_mode: bool = True, timeout: int = 60) -> str:
    """Single-turn chat completion. Returns the assistant message content (str)."""
    key = os.environ.get(cfg.api_key_env)
    if not key:
        raise RuntimeError(
            f"missing API key — set {cfg.api_key_env} in your environment "
            f"(provider={cfg.provider})."
        )
    url = cfg.base_url.rstrip("/") + "/chat/completions"
    body: dict = {
        "model": cfg.model,
        "temperature": cfg.temperature,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{cfg.provider} API error {e.code}: {e.read().decode('utf-8', 'ignore')[:500]}")
    return data["choices"][0]["message"]["content"]


_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def _data_url(path: str) -> str:
    p = Path(path)
    mime = _MIME.get(p.suffix.lower(), "image/png")
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def vision_chat(cfg: LLMConfig, system: str, user_text: str, image_paths: list[str], timeout: int = 120) -> str:
    """Multimodal chat: text + images, OpenAI-compatible content-parts format.

    Works across vision providers (OpenAI, Gemini's compat endpoint, OpenRouter).
    Images are inlined as base64 data URLs.
    """
    key = os.environ.get(cfg.api_key_env)
    if not key:
        raise RuntimeError(f"missing API key — set {cfg.api_key_env} (vision provider={cfg.provider}).")
    if not cfg.vision:
        raise RuntimeError(f"provider {cfg.provider!r} is not vision-capable.")

    content: list[dict] = [{"type": "text", "text": user_text}]
    for ip in image_paths:
        content.append({"type": "image_url", "image_url": {"url": _data_url(ip)}})

    url = cfg.base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": cfg.model,
        "temperature": cfg.temperature,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{cfg.provider} vision API error {e.code}: {e.read().decode('utf-8', 'ignore')[:500]}")
    return data["choices"][0]["message"]["content"]
