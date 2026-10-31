import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from .config import Settings
from .prompts import SYSTEM_PROMPT, TOOL_LIST_PROMPT, USER_PROMPT_TEMPLATE


class AgentError(Exception):
    pass


@dataclass(frozen=True)
class ToolDecision:
    tool_name: str
    tool_args: Dict[str, Any]
    needs_confirmation: bool
    confirmation_reason: Optional[str]
    summary: str


def _provider_headers(provider: str, api_key: str) -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if provider == "openrouter":
        headers["HTTP-Referer"] = (os.getenv("OPENROUTER_HTTP_REFERER") or "http://localhost").strip()
        headers["X-Title"] = (os.getenv("OPENROUTER_APP_NAME") or "GoDam AI Assistant").strip()
    return headers


def _call_openai_compatible(
    *,
    provider: str,
    api_key: str,
    base_url: str,
    model: str,
    command: str,
) -> str:
    if not api_key:
        raise AgentError(f"{provider.upper()}_API_KEY is not set")

    url = f"{base_url.rstrip('/')}/chat/completions"
    payload: Dict[str, Any] = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + TOOL_LIST_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(command=command)},
        ],
    }

    # Prefer strict JSON mode when the upstream supports it. If the provider/model
    # rejects the format, retry once without it and rely on the prompt contract.
    use_json_mode = provider in {"openai", "openrouter", "perplexity"}
    if use_json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = _provider_headers(provider, api_key)
    response = requests.post(url, headers=headers, json=payload, timeout=45)
    if not response.ok and use_json_mode and response.status_code in {400, 404, 422}:
        payload.pop("response_format", None)
        response = requests.post(url, headers=headers, json=payload, timeout=45)

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = response.text.strip()
        if not detail:
            detail = f"HTTP {response.status_code}"
        raise AgentError(f"{provider} request failed: {detail[:500]}") from exc

    data = response.json()
    return data["choices"][0]["message"]["content"]


def _call_openai(settings: Settings, command: str) -> str:
    return _call_openai_compatible(
        provider="openai",
        api_key=settings.openai_api_key or "",
        base_url="https://api.openai.com/v1",
        model=settings.ai_model,
        command=command,
    )


def _call_openrouter(settings: Settings, command: str) -> str:
    return _call_openai_compatible(
        provider="openrouter",
        api_key=settings.openrouter_api_key or "",
        base_url="https://openrouter.ai/api/v1",
        model=settings.ai_model,
        command=command,
    )


def _call_perplexity(settings: Settings, command: str) -> str:
    return _call_openai_compatible(
        provider="perplexity",
        api_key=settings.perplexity_api_key or "",
        base_url="https://api.perplexity.ai",
        model=settings.ai_model,
        command=command,
    )


def _call_anthropic(settings: Settings, command: str) -> str:
    if not settings.anthropic_api_key:
        raise AgentError("ANTHROPIC_API_KEY is not set")
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": settings.ai_model,
        "max_tokens": 800,
        "temperature": 0,
        "system": SYSTEM_PROMPT + "\n\n" + TOOL_LIST_PROMPT,
        "messages": [{"role": "user", "content": USER_PROMPT_TEMPLATE.format(command=command)}],
    }
    r = requests.post(url, headers={"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}, json=payload, timeout=45)
    r.raise_for_status()
    data = r.json()
    blocks = data.get("content") or []
    text = ""
    for block in blocks:
        if block.get("type") == "text":
            text += block.get("text") or ""
    return text.strip()


def _call_gemini(settings: Settings, command: str) -> str:
    if not settings.gemini_api_key:
        raise AgentError("GEMINI_API_KEY is not set")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.ai_model}:generateContent?key={settings.gemini_api_key}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": SYSTEM_PROMPT
                        + "\n\n"
                        + TOOL_LIST_PROMPT
                        + "\n\n"
                        + USER_PROMPT_TEMPLATE.format(command=command)
                    }
                ],
            }
        ],
        "generationConfig": {"temperature": 0},
    }
    r = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=45)
    r.raise_for_status()
    data = r.json()
    text = (((data.get("candidates") or [])[0]).get("content") or {}).get("parts") or [{}]
    return (text[0].get("text") or "").strip()


def decide_tool(settings: Settings, command: str) -> ToolDecision:
    provider = settings.ai_provider
    if provider == "openai":
        raw = _call_openai(settings, command)
    elif provider == "openrouter":
        raw = _call_openrouter(settings, command)
    elif provider == "perplexity":
        raw = _call_perplexity(settings, command)
    elif provider == "anthropic":
        raw = _call_anthropic(settings, command)
    elif provider == "gemini":
        raw = _call_gemini(settings, command)
    else:
        raise AgentError(f"Unknown AI_PROVIDER: {provider}")

    try:
        obj = json.loads(raw)
    except Exception as e:
        raise AgentError(f"Model did not return valid JSON. Raw: {raw[:500]}") from e

    tool_name = str(obj.get("tool_name") or "").strip()
    tool_args = obj.get("tool_args") or {}
    needs_confirmation = bool(obj.get("needs_confirmation"))
    confirmation_reason = obj.get("confirmation_reason")
    summary = str(obj.get("summary") or "").strip() or f"Run tool {tool_name}"

    if not tool_name:
        raise AgentError("Model response missing tool_name")
    if not isinstance(tool_args, dict):
        raise AgentError("tool_args must be an object")

    return ToolDecision(
        tool_name=tool_name,
        tool_args=tool_args,
        needs_confirmation=needs_confirmation,
        confirmation_reason=str(confirmation_reason) if confirmation_reason else None,
        summary=summary,
    )
