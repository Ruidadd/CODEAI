#!/usr/bin/env python3
"""List Gemini models available to this API key, optionally filtered.

  python3 list_models.py              # everything
  python3 list_models.py image tts    # names containing "image" or "tts"
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _gemini  # noqa: E402


def main() -> int:
    filters = [f.lower() for f in sys.argv[1:]]
    try:
        models = _gemini.list_models(_gemini.load_config())
    except _gemini.GeminiError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    for m in models:
        name = m.get("name", "").removeprefix("models/")
        if filters and not any(f in name.lower() for f in filters):
            continue
        methods = ",".join(m.get("supportedGenerationMethods", []))
        print(f"{name:45} {methods:40} {m.get('displayName', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
