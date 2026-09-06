"""Load repo-root ``.env`` and resolve Venice / OpenRouter / Anthropic LLM settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.paths import REPO_ROOT

_DOTENV_LOADED = False


def load_dotenv(*, path: Path | None = None, override: bool = False) -> None:
    """Load KEY=VALUE pairs from ``.env``. Existing env wins unless ``override``."""
    global _DOTENV_LOADED
    env_path = path or (REPO_ROOT / ".env")
    if not env_path.is_file():
        _DOTENV_LOADED = True
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
    _DOTENV_LOADED = True


def ensure_dotenv() -> None:
    if not _DOTENV_LOADED:
        load_dotenv()


@dataclass(frozen=True)
class LlmSettings:
    api_key: str
    url: str
    model: str
    headers: dict[str, str]
    provider: str  # "venice" | "openrouter" | "anthropic"
    api_style: str  # "openai" | "anthropic"


def llm_configured() -> bool:
    ensure_dotenv()
    return bool(
        os.environ.get("VENICE_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
    )


def get_llm_settings() -> LlmSettings | None:
    """Prefer Venice, then OpenRouter, then Anthropic direct."""
    ensure_dotenv()

    venice_key = (os.environ.get("VENICE_API_KEY") or "").strip()
    if venice_key:
        base = (os.environ.get("VENICE_BASE_URL") or "https://api.venice.ai/api/v1").rstrip("/")
        return LlmSettings(
            api_key=venice_key,
            url=f"{base}/chat/completions",
            model=os.environ.get("VENICE_MODEL", "venice-uncensored"),
            headers={
                "Authorization": f"Bearer {venice_key}",
                "Content-Type": "application/json",
            },
            provider="venice",
            api_style="openai",
        )

    openrouter_key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if openrouter_key:
        return LlmSettings(
            api_key=openrouter_key,
            url="https://openrouter.ai/api/v1/messages",
            model=os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4"),
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "HTTP-Referer": os.environ.get("OPENROUTER_HTTP_REFERER", "http://localhost:3000"),
                "X-Title": os.environ.get("OPENROUTER_APP_TITLE", "MA-Darwin"),
            },
            provider="openrouter",
            api_style="anthropic",
        )

    anthropic_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if anthropic_key:
        return LlmSettings(
            api_key=anthropic_key,
            url="https://api.anthropic.com/v1/messages",
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            headers={
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            provider="anthropic",
            api_style="anthropic",
        )
    return None


def chat_text(
    *,
    system: str,
    user: str | list[dict[str, Any]],
    max_tokens: int = 2048,
    temperature: float = 0,
) -> str:
    """Run one chat turn and return assistant text. Empty string if not configured."""
    import httpx

    settings = get_llm_settings()
    if not settings:
        return ""

    if settings.api_style == "openai":
        messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        if isinstance(user, str):
            messages.append({"role": "user", "content": user})
        else:
            messages.append({"role": "user", "content": user})
        body: dict[str, Any] = {
            "model": settings.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        with httpx.Client(timeout=120.0) as client:
            response = client.post(settings.url, headers=settings.headers, json=body)
            response.raise_for_status()
            data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        content = choices[0].get("message", {}).get("content", "")
        return content if isinstance(content, str) else ""

    # Anthropic Messages API (OpenRouter Anthropic-compat or Anthropic direct)
    if isinstance(user, str):
        user_content: Any = user
    else:
        # Convert OpenAI-style multimodal parts to Anthropic image blocks when needed
        user_content = []
        for part in user:
            if part.get("type") == "text":
                user_content.append({"type": "text", "text": part.get("text", "")})
            elif part.get("type") == "image_url":
                url = (part.get("image_url") or {}).get("url", "")
                if url.startswith("data:") and ";base64," in url:
                    header, b64 = url.split(";base64,", 1)
                    media = header.removeprefix("data:") or "image/png"
                    user_content.append(
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": media, "data": b64},
                        }
                    )
            else:
                user_content.append(part)
    body = {
        "model": settings.model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user_content}],
    }
    with httpx.Client(timeout=120.0) as client:
        response = client.post(settings.url, headers=settings.headers, json=body)
        response.raise_for_status()
        data = response.json()
    return "".join(
        part.get("text", "") for part in data.get("content", []) if part.get("type") == "text"
    )
