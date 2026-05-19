from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_football_key: str = ""
    the_odds_api_key: str = ""
    redis_url: str = "redis://localhost:6379"
    draftkings_affiliate_url: str = "#"
    fanduel_affiliate_url: str = "#"
    betmgm_affiliate_url: str = "#"
    sentry_dsn: str = ""
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_claim_email: str = "admin@parlaypal.gg"

    class Config:
        env_file = ".env"


settings = Settings()
