from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_str(name: str) -> str:
    return (os.getenv(name) or "").strip()


def _default_provider() -> str:
    explicit = _env_str("AI_PROVIDER")
    if explicit:
        return explicit.lower()
    if _env_str("OPENROUTER_API_KEY"):
        return "openrouter"
    if _env_str("PERPLEXITY_API_KEY"):
        return "perplexity"
    if _env_str("OPENAI_API_KEY"):
        return "openai"
    if _env_str("ANTHROPIC_API_KEY"):
        return "anthropic"
    if _env_str("GEMINI_API_KEY"):
        return "gemini"
    return "openai"


def _default_model(provider: str) -> str:
    provider = provider.lower().strip()
    if provider == "openrouter":
        return "perplexity/sonar-pro"
    if provider == "perplexity":
        return "sonar-pro"
    if provider == "anthropic":
        return "claude-3-5-sonnet-latest"
    if provider == "gemini":
        return "gemini-2.0-flash"
    return "gpt-4.1"


@dataclass(frozen=True)
class Settings:
    db_path: str
    backend_base_url: str
    backend_jwt: "str | None"

    ai_provider: str
    ai_model: str

    openai_api_key: "str | None"
    anthropic_api_key: "str | None"
    gemini_api_key: "str | None"
    openrouter_api_key: "str | None"
    perplexity_api_key: "str | None"

    openrouter_http_referer: "str | None"
    openrouter_app_name: "str | None"

    auto_fix: bool
    scheduler_enabled: bool
    scheduler_interval_minutes: int

    shared_secret: "str | None"


def get_settings() -> Settings:
    provider = _default_provider()
    return Settings(
        db_path=os.getenv("GODAM_DB_PATH") or os.getenv("DB_PATH") or "./warehouse.db",
        backend_base_url=(os.getenv("BACKEND_BASE_URL") or "http://127.0.0.1:3001").rstrip("/"),
        backend_jwt=os.getenv("BACKEND_JWT") or None,
        ai_provider=provider,
        ai_model=_env_str("AI_MODEL") or _default_model(provider),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY") or None,
        perplexity_api_key=os.getenv("PERPLEXITY_API_KEY") or None,
        openrouter_http_referer=os.getenv("OPENROUTER_HTTP_REFERER") or None,
        openrouter_app_name=os.getenv("OPENROUTER_APP_NAME") or None,
        auto_fix=_env_bool("AUTO_FIX", False),
        scheduler_enabled=_env_bool("AI_SCHEDULER_ENABLED", False),
        scheduler_interval_minutes=max(1, int(os.getenv("AI_SCHEDULER_INTERVAL_MINUTES") or "10")),
        shared_secret=(os.getenv("AI_PLUGIN_SHARED_SECRET") or "").strip() or None,
    )
