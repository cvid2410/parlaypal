from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- external feeds ---
    api_football_key: str = ""
    the_odds_api_key: str = ""

    # --- infra ---
    redis_url: str = "redis://localhost:6379"
    database_url: str = "postgresql+asyncpg://parlaypal:parlaypal@localhost:5432/parlaypal"

    # --- affiliate / legacy ---
    draftkings_affiliate_url: str = "#"
    fanduel_affiliate_url: str = "#"
    betmgm_affiliate_url: str = "#"
    sentry_dsn: str = ""
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_claim_email: str = "admin@parlaypal.gg"

    # --- signals: ingestion ---
    # Soft US books we shop for +EV / arb against the sharp reference.
    soft_books: str = "draftkings,fanduel,betmgm,williamhill_us,betrivers"
    # Sharp reference book used to devig a "fair" probability.
    sharp_book: str = "pinnacle"
    # The Odds API regions. Pinnacle is served under eu/uk, soft US books under us.
    odds_regions: str = "us,eu,uk"
    # Seconds between ingest polls (tighten near kickoff once live windows land).
    ingest_poll_seconds: int = 30

    # --- signals: detection ---
    # Minimum +EV edge (percent) before a signal is emitted.
    min_edge_pct: float = 2.0
    # A selection's decimal odds must move at least this fraction to count as a
    # meaningful change (NON-NEGOTIABLE #3). 0.01 == 1%.
    move_threshold: float = 0.01
    # Fractional Kelly multiplier for stake sizing.
    kelly_fraction: float = 0.25
    # Default signal TTL (seconds); also the dedup key TTL.
    signal_ttl_seconds: int = 1800
    # Edge bucket width (percent) for dedup / re-alert-on-improvement.
    edge_bucket_pct: float = 1.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
