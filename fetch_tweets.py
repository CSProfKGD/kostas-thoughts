#!/usr/bin/env python3
"""Fetch public tweet text for the local Kosta's Thoughts archive."""

from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


DEFAULT_INPUT_FILE = Path("kostas thoughts.txt")
CACHE_FILE = Path("tweet_cache.json")
STATUS_RE = re.compile(r"https?://(?:x|twitter)\.com/([^/\s]+)/status/(\d+)(?:\?[^\s]*)?", re.I)
ADDITIONAL_TWEET_URLS = [
    "https://x.com/CSProfKGD/status/2067935592361369920?s=20",
    "https://x.com/CSProfKGD/status/2069423541200552231?s=20",
    "https://x.com/CSProfKGD/status/2068401977088774448?s=20",
    "https://x.com/CSProfKGD/status/2068243455063580764?s=20",
]


class ParagraphParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_p = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "p":
            self.in_p = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "p":
            self.in_p = False

    def handle_data(self, data: str) -> None:
        if self.in_p:
            self.parts.append(data)


def load_urls(input_file: Path) -> list[tuple[str, str, str]]:
    raw = input_file.read_text(encoding="utf-8")
    urls: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for block in [*re.split(r"\n\s*\n", raw), *ADDITIONAL_TWEET_URLS]:
        entry = block.strip()
        if not entry:
            continue
        match = STATUS_RE.search(entry)
        if not match:
            continue
        username = match.group(1)
        status_id = match.group(2)
        if status_id in seen:
            continue
        seen.add(status_id)
        urls.append((status_id, username, match.group(0)))
    return urls


def extract_text(embed_html: str) -> str:
    parser = ParagraphParser()
    parser.feed(embed_html)
    text = html.unescape(" ".join(part.strip() for part in parser.parts if part.strip()))
    return re.sub(r"\s+", " ", text).strip()


def fetch_oembed(url: str) -> dict[str, str | None]:
    endpoint = "https://publish.twitter.com/oembed?omit_script=true&url=" + urllib.parse.quote(url, safe="")
    request = urllib.request.Request(endpoint, headers={"User-Agent": "KostasThoughtsLocalArchive/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
    text = extract_text(data.get("html", ""))
    return {
        "author_name": data.get("author_name"),
        "author_url": data.get("author_url"),
        "text": text,
        "html": data.get("html"),
    }


def fetch_fxtwitter(username: str, status_id: str) -> dict[str, str | None]:
    endpoint = f"https://api.fxtwitter.com/{username}/status/{status_id}"
    request = urllib.request.Request(endpoint, headers={"User-Agent": "KostasThoughtsLocalArchive/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
    tweet = data.get("tweet") or {}
    text = tweet.get("text") or ""
    if not text:
        raise ValueError("No tweet text returned")
    return {
        "author_name": (tweet.get("author") or {}).get("name"),
        "author_url": f"https://x.com/{username}",
        "text": text,
        "html": None,
    }


def appears_truncated(text: str) -> bool:
    return bool(re.search(r"…(?:\s+(?:https?://|pic\.twitter\.com)|\s*$)", text or ""))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Fetch public tweet text for local archive generation.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_FILE, help="path to the source text file")
    args = parser.parse_args()

    existing = {}
    if CACHE_FILE.exists():
        existing = json.loads(CACHE_FILE.read_text(encoding="utf-8"))

    tweets = existing.get("tweets", {})
    errors = existing.get("errors", {})
    urls = load_urls(args.input)

    for index, (status_id, username, url) in enumerate(urls, start=1):
        existing_text = tweets.get(status_id, {}).get("text")
        if existing_text and not appears_truncated(existing_text):
            continue
        try:
            try:
                fetched = fetch_fxtwitter(username, status_id)
            except Exception:
                fetched = fetch_oembed(url)
            tweets[status_id] = {"url": url, **fetched}
            errors.pop(status_id, None)
            print(f"[{index}/{len(urls)}] fetched {status_id}")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            errors[status_id] = {"url": url, "error": str(exc)}
            print(f"[{index}/{len(urls)}] failed {status_id}: {exc}")
        time.sleep(0.15)

    output = {
        "source": args.input.name,
        "fetched_count": sum(1 for item in tweets.values() if item.get("text")),
        "error_count": len(errors),
        "tweets": tweets,
        "errors": errors,
    }
    CACHE_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {CACHE_FILE} with {output['fetched_count']} tweet texts and {output['error_count']} errors.")


if __name__ == "__main__":
    main()
