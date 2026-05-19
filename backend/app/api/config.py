from fastapi import APIRouter

router = APIRouter()

BOOKS = [
    {
        "key": "draftkings",
        "name": "DraftKings",
        "promo": "Bet $5, Get $200 in Bonus Bets",
        "url": "https://sportsbook.draftkings.com/r/sb/cvid2410/US-NY-SB/US-NY",
    },
    {
        "key": "fanduel",
        "name": "FanDuel",
        "promo": "Bet $5, Get $200 in Bonus Bets",
        "url": "https://fndl.co/jjdare5",
    },
    {
        "key": "betmgm",
        "name": "BetMGM",
        "promo": "First Bet Offer Up to $1,500",
        "url": "https://sports.betmgm.com",
    },
]


@router.get("/config")
async def get_config():
    return {"books": BOOKS}
