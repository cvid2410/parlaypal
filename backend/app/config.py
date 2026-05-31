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

    # --- signals: delivery ---
    # Free tier sees signals on a delay (the teaser model). Paid tiers are live.
    free_delay_seconds: int = 12 * 60
    # Optional Discord webhook. When unset, the 'discord' channel is a no-op and only the
    # 'log' channel runs (lets us verify the full chain locally without external creds).
    discord_webhook_url: str = ""

    # --- auth ---
    jwt_secret: str = "dev-secret-change-me"  # override in prod via env
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    # Google OAuth is deferred; this placeholder marks where it plugs in (provider-ready).
    google_client_id: str = ""

    # --- billing ---
    # Dev-only tier toggle so the UI can demo free<->paid before Stripe lands.
    # MUST be False in production (Stripe webhooks become the only way to change tier).
    allow_dev_upgrade: bool = True
    # Stripe. When stripe_secret_key is unset, billing falls back to dev-upgrade.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_bettor: str = ""  # Stripe Price id for the $29 Bettor plan
    stripe_price_sharp: str = ""   # Stripe Price id for the $79 Sharp plan
    public_base_url: str = "http://localhost:5173"  # for checkout success/cancel redirects

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
