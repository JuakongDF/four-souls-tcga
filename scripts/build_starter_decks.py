#!/usr/bin/env python3
"""Generate starter decklists for Four Souls TCG Arena setup.

This avoids manually selecting cards from the full list by providing ready-to-load
shared decks (loot/treasure/monster/room), plus character and starting item pools.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def deck(title: str, game: str, fmt: str, categories: dict[str, list[str]]) -> dict:
    created = now_iso()
    deck_list: dict[str, object] = {"categoriesOrder": list(categories.keys())}
    total = 0

    for cat, ids in categories.items():
        entries = [{"count": 1, "id": cid} for cid in ids]
        deck_list[cat] = entries
        total += len(entries)

    return {
        "title": title,
        "id": str(uuid4()),
        "game": game,
        "format": fmt,
        "cardCount": total,
        "createdAt": created,
        "lastModifiedAt": created,
        "deckList": deck_list,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Four Souls starter decks JSON")
    parser.add_argument("--cards", default="cards.json", help="Input cards JSON")
    parser.add_argument("--output", default="starter_decks.json", help="Output starter decks JSON")
    parser.add_argument("--game", default="The Binding of Isaac: Four Souls", help="Game name")
    parser.add_argument("--format", default="Classic", help="Format name")
    args = parser.parse_args()

    cards = json.loads(Path(args.cards).read_text(encoding="utf-8"))

    by_type: dict[str, list[str]] = defaultdict(list)
    for card_id, card in cards.items():
        ctype = card.get("type", "Unknown")
        by_type[ctype].append(card_id)

    for t in by_type:
        by_type[t].sort()

    decks = [
        deck("FS Shared Loot Deck (All)", args.game, args.format, {"Loot": by_type.get("Loot", [])}),
        deck("FS Shared Treasure Deck (All)", args.game, args.format, {"Treasure": by_type.get("Treasure", [])}),
        deck("FS Shared Monster Deck (All)", args.game, args.format, {"Monster": by_type.get("Monster", [])}),
        deck("FS Shared Room Deck (All)", args.game, args.format, {"Room": by_type.get("Room", [])}),
        deck("FS Shared Bonus Souls (All)", args.game, args.format, {"BonusSoul": by_type.get("BonusSoul", [])}),
        deck("FS Character Pool (All)", args.game, args.format, {"Character": by_type.get("Character", [])}),
        deck("FS Starting Items Pool (All)", args.game, args.format, {"Eternal": by_type.get("Eternal", [])}),
        deck(
            "FS Full Setup Pack (All Shared)",
            args.game,
            args.format,
            {
                "Loot": by_type.get("Loot", []),
                "Treasure": by_type.get("Treasure", []),
                "Monster": by_type.get("Monster", []),
                "Room": by_type.get("Room", []),
                "BonusSoul": by_type.get("BonusSoul", []),
                "Character": by_type.get("Character", []),
                "Eternal": by_type.get("Eternal", []),
            },
        ),
    ]

    Path(args.output).write_text(json.dumps(decks, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Wrote {len(decks)} decks to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
