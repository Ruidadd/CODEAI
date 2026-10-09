#!/usr/bin/env python3
"""Fetch latest blog / YouTube / X posts for every entity in config/sources.json
and write docs/data/feed.json for the dashboard.

Stdlib only, so the GitHub Action needs no pip install.

X (Twitter) has no free public feed. Two optional modes, picked by env var:
  X_BEARER_TOKEN  official X API v2 (paid, pay-per-use)
  NITTER_BASE     an RSS bridge such as a self-hosted Nitter / RSSHub
                  (e.g. https://nitter.example.com -> {base}/{handle}/rss)
With neither set, X sources are listed as "not configured" and the dashboard
links straight to the profiles.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "sources.json"
OUT = ROOT / "docs" / "data" / "feed.json"
CACHE = ROOT / "docs" / "data" / "id_cache.json"

UA = "Mozilla/5.0 (compatible; ai-leaders-dashboard/1.0; +https://github.com)"
TIMEOUT = 20
PER_SOURCE = 10
MAX_AGE_DAYS = 90
SUMMARY_LEN = 280

X_BEARER = os.environ.get("X_BEARER_TOKEN", "").strip()
NITTER_BASE = os.environ.get("NITTER_BASE", "").strip().rstrip("/")

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def http_get(url: str, headers: dict | None = None) -> bytes:
    h = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.8"}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def clean(text: str | None, limit: int = SUMMARY_LEN) -> str:
    if not text:
        return ""
    t = WS_RE.sub(" ", html.unescape(TAG_RE.sub(" ", text))).strip()
    return t if len(t) <= limit else t[: limit - 1].rstrip() + "…"


def safe_url(u: str | None) -> str:
    u = (u or "").strip()
    return u if u.startswith(("https://", "http://")) else ""


def _text(el, path):
    found = el.find(path, NS)
    return found.text if found is not None and found.text else None


def parse_feed(data: bytes) -> list[dict]:
    """Parse RSS 2.0 or Atom into [{title,url,date,summary,thumb}]."""
    root = ET.fromstring(data)
    out = []
    if root.tag.endswith("rss") or root.find("channel") is not None:
        for it in root.iter("item"):
            thumb = it.find("media:thumbnail", NS)
            enc = it.find("enclosure")
            img = thumb.get("url") if thumb is not None else None
            if not img and enc is not None and (enc.get("type") or "").startswith("image"):
                img = enc.get("url")
            out.append({
                "title": clean(_text(it, "title"), 200),
                "url": safe_url(_text(it, "link")),
                "date": parse_date(_text(it, "pubDate") or _text(it, "dc:date")),
                "summary": clean(_text(it, "description") or _text(it, "content:encoded")),
                "thumb": safe_url(img),
            })
    else:  # Atom (incl. YouTube)
        for e in root.findall("atom:entry", NS):
            link = ""
            for l in e.findall("atom:link", NS):
                if l.get("rel", "alternate") == "alternate":
                    link = l.get("href", "")
                    break
            thumb = e.find("media:group/media:thumbnail", NS)
            out.append({
                "title": clean(_text(e, "atom:title"), 200),
                "url": safe_url(link),
                "date": parse_date(_text(e, "atom:published") or _text(e, "atom:updated")),
                "summary": clean(_text(e, "atom:summary") or _text(e, "media:group/media:description")
                                 or _text(e, "atom:content")),
                "thumb": safe_url(thumb.get("url") if thumb is not None else None),
            })
    return out


# ---------- source-specific fetchers ----------

YT_ID_RES = [
    re.compile(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"'),
    re.compile(r'"externalId":"(UC[\w-]{22})"'),
    re.compile(r'"browseId":"(UC[\w-]{22})"'),
]


def resolve_youtube(handle: str, cache: dict) -> str:
    if re.fullmatch(r"UC[\w-]{22}", handle):
        return handle
    key = f"yt:{handle.lower()}"
    if key in cache:
        return cache[key]
    page = http_get(f"https://www.youtube.com/@{urllib.parse.quote(handle)}",
                    {"Cookie": "SOCS=CAI; CONSENT=YES+1"}).decode("utf-8", "replace")
    for rx in YT_ID_RES:
        m = rx.search(page)
        if m:
            cache[key] = m.group(1)
            return m.group(1)
    raise RuntimeError("channel id not found on page")


def fetch_blog(url: str, cache: dict) -> list[dict]:
    return parse_feed(http_get(url))


def fetch_youtube(handle: str, cache: dict) -> list[dict]:
    cid = resolve_youtube(handle, cache)
    return parse_feed(http_get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"))


def fetch_x(handle: str, cache: dict) -> list[dict]:
    if X_BEARER:
        auth = {"Authorization": f"Bearer {X_BEARER}"}
        key = f"x:{handle.lower()}"
        uid = cache.get(key)
        if not uid:
            u = json.loads(http_get(f"https://api.x.com/2/users/by/username/{handle}", auth))
            uid = u["data"]["id"]
            cache[key] = uid
        q = "max_results=5&exclude=retweets,replies&tweet.fields=created_at"
        res = json.loads(http_get(f"https://api.x.com/2/users/{uid}/tweets?{q}", auth))
        return [{
            "title": clean(t.get("text"), 200),
            "url": f"https://x.com/{handle}/status/{t['id']}",
            "date": parse_date(t.get("created_at")),
            "summary": clean(t.get("text")),
            "thumb": "",
        } for t in res.get("data", [])]
    items = parse_feed(http_get(f"{NITTER_BASE}/{urllib.parse.quote(handle)}/rss"))
    # Point links back at x.com rather than the bridge host.
    for it in items:
        m = re.search(r"/status/(\d+)", it["url"])
        if m:
            it["url"] = f"https://x.com/{handle}/status/{m.group(1)}"
    return items


FETCHERS = {"blog": fetch_blog, "youtube": fetch_youtube, "x": fetch_x}


def build_jobs(entities: list[dict]) -> list[dict]:
    jobs, seen = [], set()
    for e in entities:
        def add(kind, target, author):
            k = f"{kind}:{target.lower()}"
            if target and k not in seen:
                seen.add(k)
                jobs.append({"key": k, "entity": e["id"], "kind": kind,
                             "target": target, "author": author})
        for u in e.get("blog", []):
            add("blog", u, e["name"])
        for h in e.get("youtube", []):
            add("youtube", h, e["name"])
        for h in e.get("x", []):
            add("x", h, e["name"])
        for p in e.get("people", []):
            if p.get("x"):
                add("x", p["x"], p["name"])
    return jobs


def run_job(job: dict, cache: dict, now: datetime) -> tuple[dict, list[dict]]:
    status = {"key": job["key"], "entity": job["entity"], "kind": job["kind"],
              "target": job["target"], "ok": False, "count": 0, "error": ""}
    if job["kind"] == "x" and not (X_BEARER or NITTER_BASE):
        status["error"] = "not configured"
        return status, []
    try:
        raw = FETCHERS[job["kind"]](job["target"], cache)
    except Exception as ex:  # noqa: BLE001 - one bad feed must not kill the run
        status["error"] = f"{type(ex).__name__}: {ex}"[:200]
        return status, []
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    items = []
    for r in raw:
        if not r["url"] or not r["title"]:
            continue
        if r["date"] and r["date"] < cutoff:
            continue
        items.append({
            "id": r["url"],
            "source": job["key"],
            "entity": job["entity"],
            "kind": job["kind"],
            "author": job["author"],
            "handle": job["target"] if job["kind"] != "blog" else "",
            "title": r["title"],
            "url": r["url"],
            "date": (r["date"] or now).isoformat(timespec="seconds"),
            "summary": r["summary"] if r["summary"] != r["title"] else "",
            "thumb": r["thumb"],
        })
    items.sort(key=lambda i: i["date"], reverse=True)
    items = items[:PER_SOURCE]
    status.update(ok=True, count=len(items))
    return status, items


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return default


def main() -> int:
    cfg = load_json(CONFIG, None)
    if not cfg:
        print(f"cannot read {CONFIG}", file=sys.stderr)
        return 1
    prev = load_json(OUT, {})
    cache = load_json(CACHE, {})
    now = datetime.now(timezone.utc).replace(microsecond=0)
    jobs = build_jobs(cfg["entities"])

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda j: run_job(j, cache, now), jobs))

    # Keep the last good items of a source that failed this round.
    prev_by_source: dict[str, list] = {}
    for it in prev.get("items", []):
        prev_by_source.setdefault(it.get("source"), []).append(it)

    items, statuses = {}, []
    for status, got in results:
        if not status["ok"]:
            got = prev_by_source.get(status["key"], [])
            status["stale"] = len(got)
        for it in got:
            items.setdefault(it["id"], it)
        statuses.append(status)

    out = {
        "generated": now.isoformat(timespec="seconds"),
        "x_mode": "api" if X_BEARER else ("bridge" if NITTER_BASE else "off"),
        "entities": cfg["entities"],
        "sources": statuses,
        "items": sorted(items.values(), key=lambda i: i["date"], reverse=True),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(OUT)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), "utf-8")

    ok = sum(s["ok"] for s in statuses)
    print(f"{ok}/{len(statuses)} sources ok, {len(out['items'])} items, x_mode={out['x_mode']}")
    for s in statuses:
        if not s["ok"] and s["error"] != "not configured":
            print(f"  FAIL {s['key']}: {s['error']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
