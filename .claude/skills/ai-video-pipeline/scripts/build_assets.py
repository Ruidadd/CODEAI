#!/usr/bin/env python3
"""Turn a storyboard.json into video assets for the Remotion StoryboardVideo template.

For every scene it generates an image (Gemini) and a voiceover (Gemini TTS), measures the
audio, and writes <project>/public/<storyboard id>/manifest.json with frame timings.

  python3 build_assets.py storyboard.json --project my-video
  python3 build_assets.py storyboard.json --project my-video --only s02,s03 --force
  python3 build_assets.py storyboard.json --project my-video --placeholder   # no API calls

Unchanged scenes are cached: an asset is regenerated only when its inputs change
(prompt, style, refs, narration, voice, pronunciation, model) or --force is given.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import wave
import zlib
from pathlib import Path

GEMINI_SCRIPTS = Path(__file__).resolve().parents[2] / "gemini-media" / "scripts"
sys.path.insert(0, str(GEMINI_SCRIPTS))
import _gemini  # noqa: E402
import generate_image  # noqa: E402
import tts  # noqa: E402

PLACEHOLDER_CHARS_PER_SEC = {"zh": 4.5, "ja": 7.0, "en": 15.0}
PALETTE = [(27, 42, 74), (20, 184, 166), (37, 99, 235), (217, 119, 6), (124, 58, 237), (220, 38, 38)]


def load_storyboard(path: Path) -> dict:
    board = json.loads(path.read_text(encoding="utf-8"))
    for key in ("id", "scenes"):
        if key not in board:
            raise SystemExit(f"storyboard is missing '{key}'")
    ids = [s.get("id") for s in board["scenes"]]
    if any(not i for i in ids) or len(set(ids)) != len(ids):
        raise SystemExit("every scene needs a unique 'id'")
    for s in board["scenes"]:
        if not s.get("narration") or not s.get("imagePrompt"):
            raise SystemExit(f"scene {s['id']} needs 'narration' and 'imagePrompt'")
    board.setdefault("fps", 30)
    board.setdefault("width", 1920)
    board.setdefault("height", 1080)
    board.setdefault("headPadSec", 0.4)
    board.setdefault("tailPadSec", 0.6)
    return board


def closest_aspect(width: int, height: int) -> str:
    target = width / height
    def ratio(a: str) -> float:
        w, h = a.split(":")
        return int(w) / int(h)
    return min(generate_image.ASPECTS, key=lambda a: abs(math.log(ratio(a) / target)))


def digest(*parts: object) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def write_placeholder_png(path: Path, index: int, aspect: str) -> Path:
    """A small two-colour gradient PNG; Remotion scales it to cover the frame."""
    w_ratio, h_ratio = (int(x) for x in aspect.split(":"))
    width = 480
    height = max(1, round(width * h_ratio / w_ratio))
    top = PALETTE[index % len(PALETTE)]
    bottom = PALETTE[(index + 1) % len(PALETTE)]
    rows = []
    for y in range(height):
        t = y / max(1, height - 1)
        pixel = bytes(round(a + (b - a) * t) for a, b in zip(top, bottom))
        rows.append(b"\x00" + pixel * width)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b"")
    path = path.with_suffix(".png")
    path.write_bytes(png)
    return path


def write_silent_wav(path: Path, text: str, lang: str) -> float:
    if lang == "en":
        seconds = len(text.split()) / 2.6
    else:
        seconds = len(text) / PLACEHOLDER_CHARS_PER_SEC.get(lang, 5.0)
    seconds = max(1.5, round(seconds, 2))
    rate = 24000
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))
    return seconds


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("storyboard", type=Path)
    p.add_argument("--project", type=Path, required=True, help="Remotion project root (contains public/)")
    p.add_argument("--only", help="Comma-separated scene ids to (re)build; others keep cached assets")
    p.add_argument("--force", action="store_true", help="Regenerate even if inputs are unchanged")
    p.add_argument("--placeholder", action="store_true", help="Gradient images + silent audio, no API calls")
    p.add_argument("--hq-images", action="store_true", help="Use the HQ image model (final pass)")
    args = p.parse_args()

    board = load_storyboard(args.storyboard)
    base_dir = args.storyboard.resolve().parent
    out_dir = args.project / "public" / board["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_path = out_dir / ".cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    only = set(args.only.split(",")) if args.only else None
    config = _gemini.load_config()

    lang = board.get("lang") or tts.detect_lang(board["scenes"][0]["narration"])
    aspect = closest_aspect(board["width"], board["height"])
    fps = board["fps"]
    image_model = generate_image.pick_model(config, None, args.hq_images)
    tts_model = tts.pick_model(config, None, False)
    pron = str((base_dir / board["pronunciation"]).resolve()) if board.get("pronunciation") else None

    scenes_out, cursor, failures = [], 0, []
    for index, scene in enumerate(board["scenes"]):
        sid = scene["id"]
        entry = cache.get(sid, {})
        selected = only is None or sid in only
        refs = [str((base_dir / r).resolve()) for r in scene.get("refs", [])]
        style = scene.get("style", board.get("style"))
        voice = scene.get("voice", board.get("voice"))
        voice_style = scene.get("voiceStyle", board.get("voiceStyle"))
        spoken, scene_lang, voice = tts.prepare(scene["narration"], scene.get("lang", lang), voice, pron, config)

        image_key = digest("placeholder" if args.placeholder else image_model, scene["imagePrompt"], style,
                           aspect, [file_digest(Path(r)) for r in refs])
        audio_key = digest("placeholder" if args.placeholder else tts_model, spoken, voice, voice_style)

        try:
            image_path = out_dir / entry["image"] if entry.get("image") else None
            if args.force and selected or entry.get("imageKey") != image_key or not (image_path and image_path.exists()):
                if not selected and image_path and image_path.exists():
                    print(f"[{sid}] image inputs changed but scene not in --only; keeping old image", file=sys.stderr)
                else:
                    target = out_dir / f"{sid}.png"
                    if args.placeholder:
                        image_path = write_placeholder_png(target, index, aspect)
                    else:
                        print(f"[{sid}] generating image ...", file=sys.stderr)
                        result = generate_image.generate(scene["imagePrompt"], target, style=style, aspect=aspect,
                                                         refs=refs, model=image_model, config=config)
                        image_path = Path(result["path"])
                    old = entry.get("image")
                    if old and old != image_path.name and (out_dir / old).exists():
                        (out_dir / old).unlink()
                    entry.update(image=image_path.name, imageKey=image_key)

            audio_path = out_dir / f"{sid}.wav"
            if args.force and selected or entry.get("audioKey") != audio_key or not audio_path.exists():
                if not selected and audio_path.exists():
                    print(f"[{sid}] narration changed but scene not in --only; keeping old audio", file=sys.stderr)
                elif args.placeholder:
                    write_silent_wav(audio_path, scene["narration"], scene_lang)
                    entry["audioKey"] = audio_key
                else:
                    print(f"[{sid}] generating voiceover ({voice}) ...", file=sys.stderr)
                    tts.synthesize(scene["narration"], audio_path, lang=scene_lang, voice=voice, style=voice_style,
                                   pron=pron, model=tts_model, config=config)
                    entry["audioKey"] = audio_key
        except _gemini.GeminiError as e:
            failures.append(f"{sid}: {e}")
            print(f"[{sid}] FAILED: {e}", file=sys.stderr)
            cache[sid] = entry
            continue
        cache[sid] = entry

        audio_sec = tts.wav_duration(audio_path)
        head = round(board["headPadSec"] * fps)
        frames = max(
            round(scene.get("minSec", 0) * fps),
            head + math.ceil(audio_sec * fps) + round(board["tailPadSec"] * fps),
        )
        scenes_out.append({
            "id": sid,
            "title": scene.get("title"),
            "subtitle": scene.get("subtitle", scene["narration"]),
            "image": f"{board['id']}/{entry['image']}",
            "audio": f"{board['id']}/{audio_path.name}",
            "audioSec": round(audio_sec, 3),
            "from": cursor,
            "durationInFrames": frames,
            "audioStartFrame": head,
        })
        cursor += frames

    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    if failures:
        print("\nSome scenes failed; manifest not updated:\n  " + "\n  ".join(failures), file=sys.stderr)
        return 1

    manifest = {
        "id": board["id"],
        "title": board.get("title", board["id"]),
        "lang": lang,
        "fps": fps,
        "width": board["width"],
        "height": board["height"],
        "bgm": board.get("bgm"),
        "bgmVolume": board.get("bgmVolume", 0.12),
        "placeholder": args.placeholder,
        "totalFrames": cursor,
        "scenes": scenes_out,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "manifest": str(out_dir / "manifest.json"),
        "scenes": len(scenes_out),
        "totalSec": round(cursor / fps, 2),
        "qaFrames": {s["id"]: s["from"] + s["durationInFrames"] // 2 for s in scenes_out},
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
