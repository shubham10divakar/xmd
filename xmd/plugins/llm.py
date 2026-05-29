"""@llm plugin — call an LLM via the stdlib (zero deps).

Talks to the Anthropic Messages API. The API key is read from the
``ANTHROPIC_API_KEY`` environment variable — the runtime never stores or bundles
a key (same detect-don't-install spirit as the language plugins).

    - @llm
      prompt: Summarize {{ memory.notes }} in one line.
      model: claude-sonnet-4-6   # optional
      max_tokens: 512            # optional
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .base import Result, register

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-6"


@register("llm")
def run_llm(params: dict, ctx: dict) -> Result:
    prompt = params.get("prompt", params.get("text", params.get("run", "")))
    if not str(prompt).strip():
        return Result(ok=False, error="@llm requires a 'prompt' param", code=2)

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return Result(
            ok=False,
            error="ANTHROPIC_API_KEY not set — @llm needs an API key "
            "(the runtime never stores one). Export it to enable planning.",
            code=3,
        )

    model = str(params.get("model") or DEFAULT_MODEL)
    try:
        max_tokens = int(params.get("max_tokens", 1024) or 1024)
    except (TypeError, ValueError):
        max_tokens = 1024

    body = json.dumps(
        {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": str(prompt)}],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": API_VERSION,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        text = "".join(
            blk.get("text", "")
            for blk in data.get("content", [])
            if blk.get("type") == "text"
        )
        return Result(ok=True, output=text)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        return Result(ok=False, error=f"LLM API error {e.code}: {detail[:500]}", code=e.code)
    except urllib.error.URLError as e:
        return Result(ok=False, error=f"LLM request failed: {e.reason}", code=1)
