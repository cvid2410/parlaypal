"""Unit tests for the team-page shaping (pure functions - no DB/AF needed)."""

from app.api.teams import _shape, _team_header

# Two AF fixtures for team id 50: one home win, one away (in a different competition).
FIXTURES = [
    {
        "fixture": {"date": "2026-05-01T15:00:00+00:00", "status": {"short": "FT", "elapsed": 90}},
        "league": {"name": "Premier League"},
        "teams": {
            "home": {"id": 50, "name": "Man City", "logo": "city.png"},
            "away": {"id": 66, "name": "Aston Villa", "logo": "villa.png"},
        },
        "goals": {"home": 2, "away": 1},
    },
    {
        "fixture": {
            "date": "2026-05-08T18:00:00+00:00",
            "status": {"short": "NS", "elapsed": None},
        },
        "league": {"name": "Champions League"},
        "teams": {
            "home": {"id": 505, "name": "Inter", "logo": "inter.png"},
            "away": {"id": 50, "name": "Man City", "logo": "city.png"},
        },
        "goals": {"home": None, "away": None},
    },
]


def test_shape_home_and_away_perspective():
    rows = _shape(FIXTURES, 50)
    home, away = rows

    # Home fixture: opponent is the away side, score from our team's perspective.
    assert home["opponent"] == "Aston Villa"
    assert home["home_away"] == "H"
    assert home["team_score"] == 2 and home["opp_score"] == 1
    assert home["status"] == "finished"
    assert home["league"] == "Premier League"

    # Away fixture: we're the away side; opponent is the home side; all comps included.
    assert away["opponent"] == "Inter"
    assert away["home_away"] == "A"
    assert away["team_score"] is None and away["opp_score"] is None
    assert away["status"] == "scheduled"
    assert away["league"] == "Champions League"


def test_team_header_pulls_own_name_logo():
    assert _team_header(FIXTURES, 50) == {"name": "Man City", "logo": "city.png"}


def test_team_header_missing_team_is_blank():
    assert _team_header(FIXTURES, 999) == {"name": None, "logo": None}
