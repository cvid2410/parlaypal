"""status_of must bucket API-Football status codes correctly — in particular, matches that
won't be played (CANC/PST/ABD) must NOT fall through to 'scheduled', which would park a
cancelled game in the Scores 'Upcoming' column with a future-looking kickoff time."""
from app.services.af import OFF, status_of


def test_finished_codes():
    for s in ("FT", "AET", "PEN", "AWD", "WO"):
        assert status_of(s) == "finished"


def test_live_codes():
    for s in ("1H", "2H", "HT", "ET", "P", "SUSP", "INT"):
        assert status_of(s) == "live"


def test_off_codes_are_not_scheduled():
    for s in ("CANC", "PST", "ABD"):
        assert status_of(s) == "off", f"{s} must be 'off', not scheduled/upcoming"
        assert s in OFF and OFF[s]  # has a human label for the UI


def test_unknown_and_not_started_are_scheduled():
    for s in ("NS", "TBD", "???"):
        assert status_of(s) == "scheduled"
