from __future__ import annotations

import json
from os import getenv
from typing import Any
from urllib import error, request


def _http_json(url: str, method: str = "GET", headers: dict[str, str] | None = None, payload: dict[str, Any] | None = None) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, method=method, headers=headers or {}, data=body)
    try:
        with request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return None if not raw else json.loads(raw)
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} calling {url}: {details}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Network error calling {url}: {exc.reason}") from exc


def _http_bytes(url: str, headers: dict[str, str] | None = None, max_bytes: int = 1024 * 1024) -> bytes:
    """Download raw bytes from *url*, reading at most *max_bytes*."""
    req = request.Request(url=url, method="GET", headers=headers or {})
    try:
        with request.urlopen(req, timeout=60) as response:
            return response.read(max_bytes)
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} downloading {url}: {details}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Network error downloading {url}: {exc.reason}") from exc


def _require_env(name: str) -> str:
    value = getenv(name)
    if value is None:
        raise KeyError(name)
    return value
