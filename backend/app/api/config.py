from fastapi import APIRouter
from app.config import settings

router = APIRouter()

BOOKS = [
    {
        "key": "draftkings",
        "name": "DraftKings",
        "promo": "Bet $5, Get $200 in Bonus Bets",
        "url": settings.draftkings_affiliate_url,
    },
    {
        "key": "fanduel",
        "name": "FanDuel",
        "promo": "Bet $5, Get $200 in Bonus Bets",
        "url": settings.fanduel_affiliate_url,
    },
    {
        "key": "betmgm",
        "name": "BetMGM",
        "promo": "First Bet Offer Up to $1,500",
        "url": settings.betmgm_affiliate_url,
    },
]


@router.get("/config")
async def get_config():
    return {"books": BOOKS}
