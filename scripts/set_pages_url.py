#!/usr/bin/env python3
"""Update game.json cards.dataUrl for GitHub Pages.

Usage:
  ./scripts/set_pages_url.py --user YOUR_GH_USER --repo YOUR_REPO
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Set GitHub Pages cards URL in game.json")
    parser.add_argument("--user", required=True, help="GitHub username or org")
    parser.add_argument("--repo", required=True, help="Repository name")
    parser.add_argument("--game", default="game.json", help="Path to game.json")
    args = parser.parse_args()

    game_path = Path(args.game)
    data = json.loads(game_path.read_text(encoding="utf-8"))

    cards_url = f"https://{args.user}.github.io/{args.repo}/cards.json"
    data.setdefault("cards", {})["dataUrl"] = cards_url

    game_path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Updated cards.dataUrl -> {cards_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
