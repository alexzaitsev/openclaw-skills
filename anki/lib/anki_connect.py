#!/usr/bin/env python3
"""Small AnkiConnect client used by the OpenClaw Anki skill."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


DEFAULT_ANKI_URL = "http://127.0.0.1:8765"


class AnkiConnectError(RuntimeError):
    """Raised for user-facing AnkiConnect failures."""


def anki_url() -> str:
    return os.environ.get("ANKI_CONNECT_URL", DEFAULT_ANKI_URL)


def invoke(action: str, **params: Any) -> Any:
    payload: dict[str, Any] = {"action": action, "version": 6}
    if params:
        payload["params"] = params

    request = urllib.request.Request(
        anki_url(),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise AnkiConnectError(
            f"Could not connect to AnkiConnect at {anki_url()}. "
            "Is Anki running with AnkiConnect loaded?"
        ) from exc
    except json.JSONDecodeError as exc:
        raise AnkiConnectError("AnkiConnect returned invalid JSON.") from exc

    if result.get("error"):
        raise AnkiConnectError(f"AnkiConnect error: {result['error']}")
    return result.get("result")
