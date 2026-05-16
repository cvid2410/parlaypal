from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_football_key: str = ""
    the_odds_api_key: str = ""
    redis_url: str = "redis://localhost:6379"
    database_url: str = "postgresql+asyncpg://parlaypal:parlaypal@localhost:5432/parlaypal"
    draftkings_affiliate_url: str = "#"
    fanduel_affiliate_url: str = "#"
    betmgm_affiliate_url: str = "#"
    sentry_dsn: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
