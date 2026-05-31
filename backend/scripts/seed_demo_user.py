"""Seed one demo subscriber and build their routing index, so the full
detect→fanout→deliver chain has someone to deliver to.

Run from backend/:  python -m scripts.seed_demo_user [tier]   (tier: free|bettor|sharp)
"""
import asyncio
import sys

from sqlalchemy import select

from app.config import settings
from app.models.core import League
from app.models.users import Subscription, User
from app.services.cache import get_redis
from app.shared.db import get_sessionmaker
from app.shared.routing import index_subscription

EMAIL = "demo@parlaypal.gg"


async def main(tier: str) -> None:
    Session = get_sessionmaker()
    r = get_redis()
    books = [b.strip() for b in settings.soft_books.split(",") if b.strip()]
    channels = ["log"]
    async with Session() as s:
        user = (await s.execute(select(User).where(User.email == EMAIL))).scalar_one_or_none()
        if user is None:
            user = User(email=EMAIL, tier=tier, bankroll=1000.0)
            s.add(user)
            await s.flush()
        else:
            user.tier = tier
        soft_league_ids = (
            await s.execute(select(League.id).where(League.is_soft.is_(True)))
        ).scalars().all()
        sub = (await s.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )).scalar_one_or_none()
        if sub is None:
            sub = Subscription(user_id=user.id)
            s.add(sub)
        sub.leagues = list(soft_league_ids)
        sub.books = books
        sub.min_edge = 0.0
        sub.channels = channels
        await s.commit()
        uid = user.id

    await index_subscription(r, uid, tier, list(soft_league_ids), books, 0.0, channels)
    print(f"demo user {uid} ({tier}) indexed for {len(soft_league_ids)} leagues, "
          f"books={books}, channels={channels}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "bettor"))
