"""Manually inject an odds boost → a promo signal (no auto-feed yet).

Usage (from backend/):
  python -m scripts.inject_boost \
      <fixture_id> <market_type> <line|none> <selection> <book> <boosted_american>

Examples:
  python -m scripts.inject_boost e912... h2h none home draftkings 250
  python -m scripts.inject_boost e912... total 2.5 over fanduel 180
"""

import asyncio
import sys

from app.workers.boosts import inject_boost


async def main(argv: list[str]) -> None:
    fixture_id, mtype, line_s, selection, book, boosted = argv
    line = None if line_s.lower() in ("none", "-", "null") else float(line_s)
    result = await inject_boost(fixture_id, mtype, line, selection, book, float(boosted))
    print(result)


if __name__ == "__main__":
    if len(sys.argv) != 7:
        print(__doc__)
        sys.exit(1)
    asyncio.run(main(sys.argv[1:]))
