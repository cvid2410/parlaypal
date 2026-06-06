# Sportsbook logos

The settings book picker renders each book's logo from `/books/{key}.svg`, where `{key}` is
the **Odds API bookmaker key** (the `key` field returned by `GET /api/config`, e.g.
`draftkings`, `bovada`, `betfair_ex_uk`).

There is **no logo feed** — The Odds API doesn't provide book logos — so these are added by
hand. Drop a file named exactly `<key>.svg` here and it appears automatically; a book with no
logo file falls back to its name (the `<img>` hides itself on load error). So the picker works
from day one and logos light up as you add them.

Add them by priority:
1. Affiliate books — `draftkings`, `fanduel`, `betmgm`.
2. Popular pickable books users hold — `bovada`, `betonlineag`, `bet365` / `betfair_ex_uk`, etc.
3. Long tail — leave as a name chip.

To list current book keys: `GET /api/config` (only `pickable` books), or in the DB:
`SELECT key, title FROM books ORDER BY title;`

These are trademarked brand assets — source them from each book's brand/press page and respect
their usage terms.
