#!/usr/bin/env python3
"""Generate or edit an image with a Gemini image model ("Nano Banana" family).

Examples:
  python3 generate_image.py --prompt "A robot reading a map" --style isometric-tech --out out/robot.png
  python3 generate_image.py --prompt "Same robot, now waving" --ref out/robot.png --out out/robot-wave.png
  python3 generate_image.py --prompt "..." --dry-run      # print the request, no API call

Prints one JSON line per image to stdout: {"path": ..., "mime": ..., "model": ...}
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _gemini  # noqa: E402

ASPECTS = {"1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}
SIZES = {"1K", "2K", "4K"}
EXT_BY_MIME = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def load_styles() -> dict:
    return _gemini.load_json_dict(_gemini.SKILL_DIR / "styles.json")


def build_prompt(prompt: str, style: str | None) -> tuple[str, str | None]:
    """Wrap the scene prompt with the style preset. Returns (text, preset aspect)."""
    if not style:
        return prompt.strip(), None
    styles = load_styles()
    if style not in styles:
        raise _gemini.GeminiError(f"Unknown style '{style}'. Available: {', '.join(styles)}")
    preset = styles[style]
    text = " ".join(s for s in (preset.get("prefix"), prompt.strip(), preset.get("suffix")) if s)
    return text, preset.get("aspect")


def build_request(text: str, refs: list[str], aspect: str | None, size: str | None) -> dict:
    parts: list[dict] = [{"text": text}]
    for ref in refs:
        mime = mimetypes.guess_type(ref)[0] or "image/png"
        data = base64.b64encode(Path(ref).read_bytes()).decode("ascii")
        parts.append({"inlineData": {"mimeType": mime, "data": data}})
    image_config = {}
    if aspect:
        image_config["aspectRatio"] = aspect
    if size:
        image_config["imageSize"] = size
    generation_config: dict = {"responseModalities": ["TEXT", "IMAGE"]}
    if image_config:
        generation_config["imageConfig"] = image_config
    return {"contents": [{"role": "user", "parts": parts}], "generationConfig": generation_config}


def pick_model(config: dict, model: str | None, hq: bool) -> str:
    if model:
        return model
    if os.environ.get("GEMINI_IMAGE_MODEL"):
        return os.environ["GEMINI_IMAGE_MODEL"]
    return config["image_model_hq"] if hq else config["image_model"]


def generate(
    prompt: str,
    out: str | Path,
    *,
    style: str | None = None,
    aspect: str | None = None,
    size: str | None = None,
    refs: list[str] | None = None,
    model: str | None = None,
    hq: bool = False,
    config: dict | None = None,
) -> dict:
    """Generate one image and write it to `out`. Returns metadata including the final path."""
    config = config or _gemini.load_config()
    text, preset_aspect = build_prompt(prompt, style)
    aspect = aspect or preset_aspect
    if aspect and aspect not in ASPECTS:
        raise _gemini.GeminiError(f"Unsupported aspect ratio {aspect}. Use one of {sorted(ASPECTS)}")
    if size and size not in SIZES:
        raise _gemini.GeminiError(f"Unsupported size {size}. Use one of {sorted(SIZES)}")
    model = pick_model(config, model, hq)
    body = build_request(text, refs or [], aspect, size)
    response = _gemini.generate_content(config, model, body)
    blobs, texts = _gemini.inline_parts(response)
    blob = blobs[0]
    mime = blob.get("mimeType") or blob.get("mime_type") or "image/png"
    path = Path(out)
    ext = EXT_BY_MIME.get(mime)
    if ext and path.suffix.lower() != ext and not (ext == ".jpg" and path.suffix.lower() == ".jpeg"):
        path = path.with_suffix(ext)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(blob["data"]))
    return {"path": str(path), "mime": mime, "model": model, "prompt": text, "note": " ".join(texts)[:300]}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group()
    src.add_argument("--prompt", help="What to draw (English prompts usually work best)")
    src.add_argument("--prompt-file", help="Read the prompt from a UTF-8 text file")
    p.add_argument("--out", default="out/image.png", help="Output path; suffix is fixed to match the returned format")
    p.add_argument("--style", help="Preset name from styles.json")
    p.add_argument("--aspect", help="Aspect ratio, e.g. 16:9, 9:16, 1:1 (overrides the style preset)")
    p.add_argument("--size", help="1K / 2K / 4K (only models that support imageSize, e.g. the HQ model)")
    p.add_argument("--ref", action="append", default=[], help="Reference image for editing/consistency (repeatable)")
    p.add_argument("--n", type=int, default=1, help="Number of variations (one API call each)")
    p.add_argument("--model", help="Model id override")
    p.add_argument("--hq", action="store_true", help="Use image_model_hq from config.json")
    p.add_argument("--list-styles", action="store_true", help="Print style presets and exit")
    p.add_argument("--dry-run", action="store_true", help="Print the request body without calling the API")
    args = p.parse_args()

    try:
        if args.list_styles:
            for name, preset in load_styles().items():
                print(f"{name:16} {preset.get('aspect', ''):6} {preset.get('description', '')}")
            return 0
        if not (args.prompt or args.prompt_file):
            p.error("one of --prompt / --prompt-file is required")
        prompt = args.prompt or Path(args.prompt_file).read_text(encoding="utf-8")
        config = _gemini.load_config()
        if args.dry_run:
            text, preset_aspect = build_prompt(prompt, args.style)
            body = build_request(text, args.ref, args.aspect or preset_aspect, args.size)
            for part in body["contents"][0]["parts"]:
                if "inlineData" in part:
                    part["inlineData"]["data"] = f"<{len(part['inlineData']['data'])} base64 chars>"
            print(json.dumps({"model": pick_model(config, args.model, args.hq), "body": body}, ensure_ascii=False, indent=2))
            return 0
        out = Path(args.out)
        for i in range(args.n):
            target = out if args.n == 1 else out.with_name(f"{out.stem}-{i + 1}{out.suffix}")
            result = generate(
                prompt, target, style=args.style, aspect=args.aspect, size=args.size,
                refs=args.ref, model=args.model, hq=args.hq, config=config,
            )
            print(json.dumps(result, ensure_ascii=False))
        return 0
    except _gemini.GeminiError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
