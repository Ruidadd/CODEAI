"""Minimal Gemini REST client shared by the gemini-media scripts.

Standard library only, so the scripts run anywhere Python 3.9+ is available.
urllib honours HTTPS_PROXY and the system CA store on its own.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class GeminiError(RuntimeError):
    pass


def load_config() -> dict:
    with open(SKILL_DIR / "config.json", encoding="utf-8") as f:
        return json.load(f)


def load_json_dict(path: Path) -> dict:
    """Load a JSON object, dropping keys that start with "_" (comments)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def api_key(config: dict) -> str:
    for name in config["api_key_env"]:
        value = os.environ.get(name)
        if value:
            return value
    names = " or ".join(config["api_key_env"])
    raise GeminiError(
        f"No API key found. Set {names} in the environment "
        "(never paste the key into a file that gets committed)."
    )


def generate_content(config: dict, model: str, body: dict) -> dict:
    """POST models/{model}:generateContent and return the parsed JSON response."""
    url = f"{config['api_base']}/models/{model}:generateContent"
    payload = json.dumps(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key(config),
    }
    attempts = int(config.get("max_retries", 3))
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=config.get("timeout_sec", 180)) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = _error_message(e)
            if e.code in RETRYABLE_STATUS and attempt < attempts:
                wait = 2 ** attempt
                print(f"[gemini] HTTP {e.code}, retrying in {wait}s: {detail}", file=sys.stderr)
                time.sleep(wait)
                continue
            raise GeminiError(f"HTTP {e.code} from {model}: {detail}") from None
        except urllib.error.URLError as e:
            if attempt < attempts:
                wait = 2 ** attempt
                print(f"[gemini] network error, retrying in {wait}s: {e.reason}", file=sys.stderr)
                time.sleep(wait)
                continue
            raise GeminiError(
                f"Cannot reach {config['api_base']}: {e.reason}. "
                "If this runs in a sandbox, the host may need to be allow-listed."
            ) from None
    raise GeminiError("unreachable")


def list_models(config: dict) -> list[dict]:
    models, token = [], None
    while True:
        url = f"{config['api_base']}/models?pageSize=1000"
        if token:
            url += f"&pageToken={token}"
        request = urllib.request.Request(url, headers={"x-goog-api-key": api_key(config)})
        try:
            with urllib.request.urlopen(request, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise GeminiError(f"HTTP {e.code}: {_error_message(e)}") from None
        models.extend(data.get("models", []))
        token = data.get("nextPageToken")
        if not token:
            return models


def inline_parts(response: dict) -> tuple[list[dict], list[str]]:
    """Split the first candidate into (inline data parts, text parts)."""
    candidates = response.get("candidates") or []
    if not candidates:
        feedback = response.get("promptFeedback", {})
        reason = feedback.get("blockReason") or "no candidates returned"
        raise GeminiError(f"Gemini returned no result ({reason}).")
    candidate = candidates[0]
    parts = (candidate.get("content") or {}).get("parts") or []
    blobs = [p.get("inlineData") or p.get("inline_data") for p in parts]
    blobs = [b for b in blobs if b]
    texts = [p["text"] for p in parts if p.get("text")]
    if not blobs:
        reason = candidate.get("finishReason", "unknown")
        hint = f" Model said: {' '.join(texts)[:300]}" if texts else ""
        raise GeminiError(f"No media in response (finishReason={reason}).{hint}")
    return blobs, texts


def _error_message(e: urllib.error.HTTPError) -> str:
    try:
        body = json.loads(e.read().decode("utf-8"))
        return body.get("error", {}).get("message", str(body))[:500]
    except Exception:
        return e.reason if isinstance(e.reason, str) else str(e)
