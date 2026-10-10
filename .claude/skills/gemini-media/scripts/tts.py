#!/usr/bin/env python3
"""Text-to-speech with Gemini TTS, saved as 16-bit mono WAV.

Examples:
  python3 tts.py --text "光庭信息へようこそ。" --lang ja --out out/intro.wav
  python3 tts.py --text-file narration.txt --voice Charon --style "用沉稳、专业的语气朗读" --out out/n.wav
  python3 tts.py --text $'A: 你好！\nB: 你好，今天聊什么？' --speakers A=Kore,B=Puck --out out/dialog.wav
  python3 tts.py --text "..." --dry-run      # show the request and the text after pronunciation fixes

Prints one JSON line to stdout: {"path": ..., "duration_sec": ..., "voice": ..., "model": ...}
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _gemini  # noqa: E402

KNOWN_VOICES = {
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede", "Callirrhoe", "Autonoe",
    "Enceladus", "Iapetus", "Umbriel", "Algieba", "Despina", "Erinome", "Algenib", "Rasalgethi",
    "Laomedeia", "Achernar", "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird",
    "Zubenelgenubi", "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
}
KANA = re.compile(r"[\u3040-\u30ff]")
CJK = re.compile(r"[\u4e00-\u9fff]")
ASCII_WORD = re.compile(r"^[A-Za-z0-9 .\-]+$")


def detect_lang(text: str) -> str:
    if KANA.search(text):
        return "ja"
    if CJK.search(text):
        return "zh"
    return "en"


def apply_pronunciation(text: str, lang: str, extra: str | None = None) -> str:
    """Replace terms with readings the TTS model pronounces correctly.

    Uses pronunciation/<lang>.json plus an optional extra JSON file. Longest terms
    are replaced first; ASCII terms only match as whole words.
    """
    table: dict[str, str] = {}
    default = _gemini.SKILL_DIR / "pronunciation" / f"{lang}.json"
    if default.exists():
        table.update(_gemini.load_json_dict(default))
    if extra:
        table.update(_gemini.load_json_dict(Path(extra)))
    if not table:
        return text
    keys = sorted(table, key=len, reverse=True)
    alternatives = [
        rf"(?<![A-Za-z]){re.escape(k)}(?![A-Za-z])" if ASCII_WORD.match(k) else re.escape(k)
        for k in keys
    ]
    pattern = re.compile("|".join(alternatives))
    return pattern.sub(lambda m: table[m.group(0)], text)


def parse_speakers(spec: str) -> list[tuple[str, str]]:
    pairs = []
    for item in spec.split(","):
        name, _, voice = item.partition("=")
        if not name.strip() or not voice.strip():
            raise _gemini.GeminiError(f"Bad --speakers entry '{item}'. Use NAME=Voice,NAME=Voice")
        pairs.append((name.strip(), voice.strip()))
    if len(pairs) > 2:
        raise _gemini.GeminiError("Gemini TTS supports at most 2 speakers per request.")
    return pairs


def build_request(text: str, voice: str, style: str | None, speakers: list[tuple[str, str]] | None) -> dict:
    if speakers:
        names = " and ".join(n for n, _ in speakers)
        lead = style.rstrip(":： ") if style else f"TTS the following conversation between {names}"
        prompt = f"{lead}:\n{text}"
        speech_config = {
            "multiSpeakerVoiceConfig": {
                "speakerVoiceConfigs": [
                    {"speaker": n, "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": v}}}
                    for n, v in speakers
                ]
            }
        }
    else:
        prompt = f"{style.rstrip(':： ')}:\n{text}" if style else text
        speech_config = {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}
    return {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": speech_config},
    }


def sample_rate(mime: str) -> int:
    match = re.search(r"rate=(\d+)", mime or "")
    return int(match.group(1)) if match else 24000


def write_wav(path: Path, pcm: bytes, rate: int) -> float:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return len(pcm) / 2 / rate


def wav_duration(path: str | Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def pick_model(config: dict, model: str | None, hq: bool) -> str:
    if model:
        return model
    if os.environ.get("GEMINI_TTS_MODEL"):
        return os.environ["GEMINI_TTS_MODEL"]
    return config["tts_model_hq"] if hq else config["tts_model"]


def prepare(text: str, lang: str | None, voice: str | None, pron: str | None, config: dict) -> tuple[str, str, str]:
    lang = lang or detect_lang(text)
    voice = voice or config["default_voice"].get(lang, "Kore")
    if voice not in KNOWN_VOICES:
        print(f"[tts] warning: '{voice}' is not in the known voice list; sending it anyway.", file=sys.stderr)
    return apply_pronunciation(text, lang, pron), lang, voice


def synthesize(
    text: str,
    out: str | Path,
    *,
    lang: str | None = None,
    voice: str | None = None,
    style: str | None = None,
    speakers: list[tuple[str, str]] | None = None,
    pron: str | None = None,
    model: str | None = None,
    hq: bool = False,
    config: dict | None = None,
) -> dict:
    """Synthesize `text` to a WAV file. Returns metadata including duration."""
    config = config or _gemini.load_config()
    spoken, lang, voice = prepare(text, lang, voice, pron, config)
    model = pick_model(config, model, hq)
    response = _gemini.generate_content(config, model, build_request(spoken, voice, style, speakers))
    blobs, _ = _gemini.inline_parts(response)
    path = Path(out).with_suffix(".wav")
    mime = blobs[0].get("mimeType") or blobs[0].get("mime_type") or ""
    if "wav" in mime:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(blobs[0]["data"]))
        duration = wav_duration(path)
    else:
        pcm = b"".join(base64.b64decode(b["data"]) for b in blobs)
        duration = write_wav(path, pcm, sample_rate(mime))
    return {
        "path": str(path),
        "duration_sec": round(duration, 3),
        "voice": voice if not speakers else dict(speakers),
        "lang": lang,
        "model": model,
        "spoken_text": spoken,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--text")
    src.add_argument("--text-file", help="UTF-8 text file to read")
    p.add_argument("--out", default="out/speech.wav")
    p.add_argument("--lang", choices=["zh", "ja", "en"], help="Default: detected from the text")
    p.add_argument("--voice", help="Prebuilt voice name, see references/voices.md")
    p.add_argument("--style", help='Delivery instruction, e.g. "落ち着いたトーンで読み上げてください"')
    p.add_argument("--speakers", help="Two-speaker dialog: A=Kore,B=Puck (text lines start with 'A:' / 'B:')")
    p.add_argument("--pron", help="Extra pronunciation JSON {term: reading}")
    p.add_argument("--model", help="Model id override")
    p.add_argument("--hq", action="store_true", help="Use tts_model_hq from config.json")
    p.add_argument("--dry-run", action="store_true", help="Print the request without calling the API")
    args = p.parse_args()

    try:
        text = args.text if args.text is not None else Path(args.text_file).read_text(encoding="utf-8")
        speakers = parse_speakers(args.speakers) if args.speakers else None
        config = _gemini.load_config()
        if args.dry_run:
            spoken, lang, voice = prepare(text, args.lang, args.voice, args.pron, config)
            body = build_request(spoken, voice, args.style, speakers)
            print(json.dumps({"model": pick_model(config, args.model, args.hq), "lang": lang, "body": body},
                             ensure_ascii=False, indent=2))
            return 0
        result = synthesize(
            text, args.out, lang=args.lang, voice=args.voice, style=args.style, speakers=speakers,
            pron=args.pron, model=args.model, hq=args.hq, config=config,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except _gemini.GeminiError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
