"""Minimal team-name normalization for cross-feed matching (Odds API ↔ API-Football).

Deliberately light: lowercase, strip accents, drop common club-type tokens, collapse
whitespace. Good enough to match most soft-league names; the misses are exactly what the
review_queue surfaces for manual aliasing (NON-NEGOTIABLE #6).
"""
from __future__ import annotations

import re
import unicodedata

# Club-type tokens that differ between feeds and carry no identity ("Bahia EC" == "Bahia").
_DROP = {"fc", "cf", "sc", "ac", "afc", "cd", "ec", "se", "ud", "sd", "club", "cska"}


def norm_team(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    tokens = [t for t in s.split() if t not in _DROP]
    return " ".join(tokens).strip()
