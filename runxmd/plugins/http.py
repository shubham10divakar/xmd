"""@http plugin — make an HTTP request with the stdlib (zero deps).

    - @http
      method: GET
      url: https://api.github.com
      body: {"x": 1}        # optional; sent as the request body
      content_type: application/json   # optional
"""
from __future__ import annotations

import urllib.error
import urllib.request

from .base import Result, register

_MAX = 2000


@register("http")
def run_http(params: dict, ctx: dict) -> Result:
    url = str(params.get("url", "")).strip()
    if not url:
        return Result(ok=False, error="@http requires a 'url' param", code=2)
    method = str(params.get("method", "GET")).upper()

    headers = {}
    if params.get("content_type"):
        headers["Content-Type"] = str(params["content_type"])

    body = params.get("body")
    data = None
    if body is not None:
        data = (body if isinstance(body, str) else str(body)).encode("utf-8")

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8", "replace")
            status = getattr(resp, "status", resp.getcode())
        return Result(ok=200 <= status < 400, output=f"{status}\n{_clip(text)}", code=status)
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")
        return Result(ok=False, output=f"{e.code}\n{_clip(text)}", error=str(e), code=e.code)
    except urllib.error.URLError as e:
        return Result(ok=False, error=f"request failed: {e.reason}", code=1)


def _clip(text: str) -> str:
    if len(text) <= _MAX:
        return text
    return text[:_MAX] + f"\n… [truncated {len(text) - _MAX} chars]"
