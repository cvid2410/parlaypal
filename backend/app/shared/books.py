"""Curated book-catalog overrides — the code-owned policy layer over the auto-synced `books`
table.

The table is auto-populated from The Odds API (key/title by the ingestor, region by
sync_books). These overrides are the MANUAL bits the API can't tell us, applied on top by
sync_books:
  * `pickable=False` — books we ingest for price/arb context but do NOT offer in the picker:
    the sharp reference (Pinnacle: no US retail), sweeps books (Fliff), and thin/erratic ones.
  * `affiliate_promo` / `affiliate_url` — our referral deals (only the books we monetize).
  * `category` — coarse grouping (us / offshore / exchange / euro / sweeps / sharp).
  * `name` — a nicer display name than the API's `title`, when we want to override it.

Edit here; sync_books propagates to the table. Anything not listed defaults to pickable, no
affiliate, category from the API region.
"""

from __future__ import annotations

BOOK_OVERRIDES: dict[str, dict] = {
    # --- affiliate books (monetized) ---
    "draftkings": {
        "promo": "Bet $5, Get $200 in Bonus Bets",
        "url": "https://sportsbook.draftkings.com/r/sb/cvid2410/US-NY-SB/US-NY",
        "category": "us",
    },
    "fanduel": {
        "promo": "Bet $5, Get $200 in Bonus Bets",
        "url": "https://fndl.co/jjdare5",
        "category": "us",
    },
    "betmgm": {
        "promo": "First Bet Offer Up to $1,500",
        "url": "https://sports.betmgm.com",
        "category": "us",
    },
    # Fliff is a sweepstakes book, but "Fliff Cash" is redeemable for real money and it's
    # available in more US states than DK/FD — so it's pickable, just tagged `sweeps` (the UI
    # can flag it; arb sizing on sweeps books has caveats the user accepts by selecting it).
    "fliff": {"category": "sweeps"},
    # --- not pickable (still ingested for price/arb context, just not offered) ---
    "pinnacle": {"pickable": False, "category": "sharp"},  # our devig reference; no US retail
    "suprabets": {"pickable": False},  # thin/erratic
}


def override_for(key: str) -> dict:
    return BOOK_OVERRIDES.get(key, {})
