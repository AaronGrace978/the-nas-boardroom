"""Optional local phrasing via Ollama. Loopback only. Votes never come from here."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse

_PATHISH = re.compile(r"[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\- ()]+)+|[a-f0-9]{12,}")


def resolve_host(host: str | None) -> str:
    """Accept a loopback Ollama URL. Anything else is refused."""
    chosen = (host or "http://127.0.0.1:11434").strip()
    if not _loopback(chosen):
        return ""
    return chosen.rstrip("/")


def probe(host: str, timeout: float = 0.4) -> bool:
    if not host or not _loopback(host):
        return False
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(host.rstrip("/") + "/api/tags", timeout=timeout) as response:
            return 200 <= getattr(response, "status", 200) < 300
    except (OSError, urllib.error.URLError, TimeoutError):
        return False


def phrase(name: str, source: str, *, model: str, host: str, timeout: float = 8.0) -> str | None:
    """Ask a local model to rephrase `source`. Return None unless the facts survive."""
    if not host or not _loopback(host):
        return None
    prompt = (
        f"You are {name}, a seat in a local NAS board meeting.\n"
        "Rewrite the statement below in your own voice.\n"
        "Keep every path, hash, date, and number exactly as written.\n"
        "Do not add files. Do not change the recommendation.\n"
        "Write at most 120 words. Plain sentences. No preamble.\n\n"
        f"STATEMENT:\n{source}\n"
    )
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        host.rstrip("/") + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeError):
        return None
    text = str(data.get("response") or "").strip()
    if not text or not _keeps_facts(source, text):
        return None
    return text


def _loopback(host: str) -> bool:
    parsed = urlparse(host if "://" in host else f"http://{host}")
    return parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def _keeps_facts(source: str, rewritten: str) -> bool:
    if len(rewritten) > 1600:
        return False
    if re.search(r"https?://", rewritten) and not re.search(r"https?://", source):
        return False
    for token in _PATHISH.findall(rewritten):
        if token not in source:
            return False
    return True
