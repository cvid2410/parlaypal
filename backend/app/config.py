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

    # --- adaptive (kickoff-aware) polling ---
    # The worker wakes every tick; each league is fetched only when its tier is due. This
    # keeps fast polling for live/imminent games and barely touches idle leagues — the
    # refresh rate is the real Odds API cost driver (CLAUDE.md / BUILD_PLAN 0.2).
    poll_tick_seconds: int = 20            # base loop cadence (= the fast cadence)
    poll_live_duration_min: int = 150      # treat a fixture as in-play this long after kickoff
    poll_near_window_min: int = 75         # "imminent": kickoff within this window → fast
    poll_upcoming_window_hours: int = 12   # has a game later today → medium
    poll_fast_seconds: int = 20            # live / imminent leagues
    poll_medium_seconds: int = 300         # upcoming-today leagues
    poll_slow_seconds: int = 1800          # idle leagues (still discover fixtures + far odds)

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
    # Middles: max combined inverse-odds (hold) worth surfacing. <=1.10 means a miss costs
    # at most ~9%; <1.0 is a guaranteed-profit middle (arb that also middles).
    middle_max_hold: float = 1.10

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
