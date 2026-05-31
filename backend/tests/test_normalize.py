from app.shared.normalize import norm_team


def test_strips_accents_and_case():
    assert norm_team("Atlético") == "atletico"
    assert norm_team("São Paulo") == "sao paulo"


def test_drops_club_suffix_tokens():
    assert norm_team("Bahia EC") == "bahia"
    assert norm_team("EC Bahia") == "bahia"
    assert norm_team("Vasco da Gama FC") == "vasco da gama"


def test_collapses_punctuation_and_space():
    assert norm_team("Paris Saint-Germain") == "paris saint germain"
    assert norm_team("  Real   España  ") == "real espana"
