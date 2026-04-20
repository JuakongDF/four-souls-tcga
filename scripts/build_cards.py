#!/usr/bin/env python3
"""Build a TCG Arena card list JSON by scraping Four Souls public card pages.

This script collects card links from Four Souls card-search pages, then extracts
card title and image URL from each card page.

Usage:
  ./scripts/build_cards.py --output ./cards.json
  ./scripts/build_cards.py --output ./cards.json --max-per-type 30
"""

from __future__ import annotations

import argparse
import json
import re
import time
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE = "https://foursouls.com"
USER_AGENT = "Mozilla/5.0 (compatible; FourSouls-TCGA-Builder/1.0)"

CARD_TYPES = {
    "character": "Character",
    "eternal": "Eternal",
    "treasure": "Treasure",
    "loot": "Loot",
    "monster": "Monster",
    "bsoul": "BonusSoul",
    "room": "Room",
}

CARD_BACKS = {
    "Character": "https://foursouls.com/wp-content/uploads/2021/10/CharacterCardBack.png",
    "Eternal": "https://foursouls.com/wp-content/uploads/2021/10/EternalCardBack.png",
    "Treasure": "https://foursouls.com/wp-content/uploads/2021/10/TreasureCardBack.png",
    "Loot": "https://foursouls.com/wp-content/uploads/2021/10/LootCardBack.png",
    "Monster": "https://foursouls.com/wp-content/uploads/2021/10/MonsterCardBack.png",
    "BonusSoul": "https://foursouls.com/wp-content/uploads/2022/01/SoulCardBack.png",
    "Room": "https://foursouls.com/wp-content/uploads/2022/04/RoomCardBack.png",
}


def fetch(url: str, retries: int = 4, timeout: int = 25, base_backoff: float = 1.2) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    last_exc: Exception | None = None

    for attempt in range(retries + 1):
        try:
            with urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            last_exc = exc
            status = getattr(exc, "code", 0) or 0
            # Retry transient server/rate-limit responses.
            if status in (408, 425, 429, 500, 502, 503, 504, 520, 522, 524) and attempt < retries:
                time.sleep(base_backoff * (2 ** attempt))
                continue
            raise
        except (URLError, TimeoutError) as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(base_backoff * (2 ** attempt))
                continue
            raise

    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"Failed to fetch URL: {url}")


def extract_card_links(search_html: str) -> list[str]:
    links = re.findall(r'href="(https://foursouls.com/cards/[^"]+)"', search_html)
    cleaned: list[str] = []
    seen = set()
    for link in links:
        if "/cards/" not in link:
            continue
        if "card-search" in link:
            continue
        link = link.split("#", 1)[0].rstrip("/") + "/"
        if link not in seen:
            seen.add(link)
            cleaned.append(link)
    return cleaned


def gather_links(card_type: str) -> list[str]:
    all_links: list[str] = []
    seen = set()
    for page in range(1, 30):
        if page == 1:
            url = f"{BASE}/card-search/?card_type={card_type}"
        else:
            url = f"{BASE}/card-search/page/{page}/?card_type={card_type}"

        html = fetch(url)
        page_links = extract_card_links(html)
        if not page_links:
            break

        added = 0
        for link in page_links:
            if link in seen:
                continue
            seen.add(link)
            all_links.append(link)
            added += 1

        if added == 0:
            break

    return all_links


def extract_title(html: str) -> str | None:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    text = re.sub(r"<[^>]+>", "", m.group(1))
    return unescape(text).strip()


def extract_face_image(html: str) -> str | None:
    # Prefer the explicit "Card Face" anchor.
    m = re.search(r'href="(https://foursouls.com/wp-content/uploads/[^"]+)"[^>]*>[^<]*Card Face', html, flags=re.IGNORECASE)
    if m:
        return m.group(1)

    # Fallback: first uploaded PNG/JPG in content.
    m = re.search(r'https://foursouls.com/wp-content/uploads/[\w\-/%.]+\.(?:png|jpg|jpeg|webp)', html, flags=re.IGNORECASE)
    if m:
        return m.group(0)

    return None


def slug_to_id(url: str) -> str:
    slug = url.rstrip("/").split("/")[-1]
    return slug.replace("-", "_").upper().replace("_", "-")


def make_card(card_id: str, title: str, type_name: str, face_image: str) -> dict:
    back_image = CARD_BACKS[type_name]
    return {
        "id": card_id,
        "isToken": False,
        "face": {
            "front": {
                "name": title,
                "type": type_name,
                "cost": 0,
                "image": face_image,
                "isHorizontal": False,
            },
            "back": {
                "name": "",
                "type": "",
                "cost": 0,
                "image": back_image,
                "isHorizontal": False,
            },
        },
        "name": title.lower(),
        "type": type_name,
        "cost": 0,
        "set": "unknown",
    }


def build_cards(max_per_type: int | None, pause: float) -> dict:
    cards = {}

    for source_type, target_type in CARD_TYPES.items():
        links = gather_links(source_type)
        if max_per_type:
            links = links[:max_per_type]

        print(f"[{source_type}] {len(links)} links")

        for idx, link in enumerate(links, start=1):
            try:
                html = fetch(link)
                title = extract_title(html)
                face_image = extract_face_image(html)

                if not title or not face_image:
                    print(f"  - skip {link} (missing title/image)")
                    continue

                card_id = slug_to_id(link)
                cards[card_id] = make_card(card_id, title, target_type, face_image)
                if idx % 25 == 0:
                    print(f"  processed {idx}/{len(links)}")
            except Exception as exc:
                print(f"  - error {link}: {exc}")

            if pause > 0:
                time.sleep(pause)

    return dict(sorted(cards.items(), key=lambda kv: kv[0]))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build TCG Arena cards JSON from Four Souls pages")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--max-per-type", type=int, default=None, help="Optional cap per card type for quick testing")
    parser.add_argument("--pause", type=float, default=0.05, help="Delay between requests in seconds")
    args = parser.parse_args()

    cards = build_cards(args.max_per_type, args.pause)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(cards, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(f"Wrote {len(cards)} cards to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
