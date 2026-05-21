from time import perf_counter
from urllib.parse import urljoin

import httpx

from app.db.models import UpstreamAccount


class RelayError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def normalize_base_url(base_url: str) -> str:
    clean = base_url.strip().rstrip("/")
    if not clean:
        raise RelayError("base_url is required")
    return clean + "/"


def extract_usage(payload: dict) -> dict[str, int]:
    usage = payload.get("usage") or {}
    prompt_details = usage.get("prompt_tokens_details") or {}
    completion_details = usage.get("completion_tokens_details") or {}
    cached_tokens = int(prompt_details.get("cached_tokens") or usage.get("cached_tokens") or 0)
    reasoning_tokens = int(completion_details.get("reasoning_tokens") or usage.get("reasoning_tokens") or 0)
    input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_tokens": cached_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
    }


def extract_text(payload: dict) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
    output = payload.get("output")
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            for content in item.get("content", []) if isinstance(item, dict) else []:
                text = content.get("text") if isinstance(content, dict) else None
                if isinstance(text, str):
                    parts.append(text)
        if parts:
            return "\n".join(parts)
    return ""


async def test_openai_compatible(account: UpstreamAccount, timeout_seconds: float = 20) -> dict:
    headers = {"Authorization": f"Bearer {account.api_key}"}
    url = urljoin(normalize_base_url(account.base_url), "models")
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.get(url, headers=headers)
    if response.status_code >= 400:
        raise RelayError(response.text[:500], response.status_code)
    payload = response.json()
    models = payload.get("data") if isinstance(payload, dict) else []
    return {"ok": True, "model_count": len(models) if isinstance(models, list) else 0}


async def run_openai_chat_completion(
    account: UpstreamAccount,
    model: str,
    messages: list[dict],
    timeout_seconds: float = 120,
) -> dict:
    headers = {
        "Authorization": f"Bearer {account.api_key}",
        "Content-Type": "application/json",
    }
    body = {"model": model, "messages": messages, "stream": False}
    url = urljoin(normalize_base_url(account.base_url), "chat/completions")
    start = perf_counter()
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(url, headers=headers, json=body)
    latency_ms = int((perf_counter() - start) * 1000)
    if response.status_code >= 400:
        raise RelayError(response.text[:1000], response.status_code)
    payload = response.json()
    usage = extract_usage(payload)
    return {
        "payload": payload,
        "text": extract_text(payload),
        "usage": usage,
        "latency_ms": latency_ms,
    }
